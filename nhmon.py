# NHAssist - NetHack automated price identification and tedium removal tool.
# Copyright (C) 2019-2025  Vitaly Ostrosablin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
NetHack monitor - it keeps track of game state by looking at the screen output.
"""

import json
import logging
import os
import sys
import re
from abc import ABC, abstractmethod
from argparse import Namespace
from typing import List, Optional, Dict, TypedDict

import const
from priceid import (
    abbreviate_items,
    lookup_item,
    find_price_candidates,
)
from tmux import Tmux


# TODO: Gem ID, Wand ID, Ring ID


class PriceIdentifiedItem(TypedDict):
    """
    This represents a single entry of price-identified item.
    """
    short_name: str
    candidates: List[str]
    item_called: bool


class NHMonitor(ABC):
    """
    Base NetHack monitor class that does general tracking without windowport-specific
    details.
    """

    def __init__(self, args: Namespace):
        """
        Initialize a new NetHack monitor object.

        :param args: Command line arguments.
        """
        # Tmux object
        self.tmux = Tmux(args.targetpane)

        # Game state
        self.price_id: Dict[str, PriceIdentifiedItem] = {}
        self.known_items: Dict[str, str] = {}
        self.charisma = 0
        self.xplevel = 0
        self.sucker = False  # TODO: Autodetect worn shirt or dunce cap?
        self.tourist = False
        self.turn: int | None = None

        # Internal monitor state:
        self.state = "init"
        # This flag enables automatic Elbereth on dust finger-engraving.
        self.autoeword = args.auto_elbereth
        # This flag indicates that NHAssist is quitting and will stop main loop.
        self.stopping = False
        # This flag would cause NHMonitor to be recreated and will reset it's state.
        self.reset = False
        # Duration for messages, displayed via tmux display-message. Hardcoded for now.
        self.msg_duration = 2
        # Align turnlimits on multiples of turnlimit (e.g. 500, 1000, 1500).
        self.aligned_turnlimit = args.aligned_turnlimit
        # Turnlimit - how many turns to give player?
        self.turnlimit = args.turnlimit
        # Save and quit on hitting the turn.
        self.stop_on_turn = 0
        # Max description length for called items.
        self.max_abbrev_length = args.abbreviation_length
        # Persistence file path.
        self.persistence_file = args.persistence
        if self.persistence_file is not None:
            self.persistence_load()
        # Persistence is dirty (needs to be saved) flag.
        self.dirty = False

    def persistence_load(self) -> None:
        """
        Load persistent knowledge from previous play session(s).

        :return: None.
        """
        try:
            with open(self.persistence_file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return  # File doesn't exist or not yet saved, ignore
        self.price_id = data.get("price_id", self.price_id)
        self.known_items = data.get("known_items", self.known_items)
        self.charisma = data.get("charisma", self.charisma)
        self.xplevel = data.get("xplevel", self.xplevel)
        self.sucker = data.get("sucker", self.sucker)
        self.tourist = data.get("tourist", self.tourist)

    def persistence_save(self) -> None:
        """
        Save learned facts into persistence file.

        :return: None.
        """
        if not self.dirty or self.persistence_file is None:
            return
        data = {
            "price_id": self.price_id,
            "known_items": self.known_items,
            "charisma": self.charisma,
            "xplevel": self.xplevel,
            "sucker": self.sucker,
            "tourist": self.tourist,
        }
        try:
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, sort_keys=True)
        except OSError:
            self.persistence_file = None
            return  # Cannot write to file
        self.dirty = False

    def persistence_unlink(self) -> None:
        """
        Destroy persistence file.

        :return: None.
        """
        os.unlink(self.persistence_file)

    def set_turn(self, turn: int) -> None:
        """
        Set a new turn value. This will check turnlimits for automatic save-and-quit
        feature.

        :param turn: New turn counter value.
        :return: None.
        """
        # TODO: Autoreset if turn counter becomes less than remembered?
        newturn: Optional[int] = turn
        if self.turn is None:
            self.restore_sync()
            if self.turnlimit:
                if self.aligned_turnlimit:
                    self.stop_on_turn = self.turnlimit * (turn // self.turnlimit + 1)
                else:
                    self.stop_on_turn = turn + self.turnlimit
        if self.stop_on_turn and turn >= self.stop_on_turn and turn != self.turn:
            self.tmux.display_message(
                "Turn limit reached, saving game...", self.msg_duration
            )
            self.mark_state_dirty()
            if self.save_and_quit():
                newturn = None
        self.turn = newturn

    def set_charisma(self, charisma: int) -> None:
        """
        Set a new charisma value that's used in buy price computations.

        :param charisma: New charisma value.
        :return: None.
        """
        if self.charisma != charisma:
            logging.info("New charisma value learned: %s", charisma)
            self.charisma = charisma
            self.mark_state_dirty()

    def set_xplevel(self, xplevel: int) -> None:
        """
        Set a new experience level value.

        :param xplevel: New experience level value.
        :return: None.
        """
        if self.xplevel != xplevel:
            logging.info("New XP level value learned: %s", xplevel)
            self.xplevel = xplevel
            self.mark_state_dirty()

    def set_tourist(self, state: bool) -> None:
        """
        Set tourist state.

        :param state: Boolean, if True - you're identified as a Tourist.
        :return: None.
        """
        if state:
            logging.info("You have been identified as low-level tourist")
            self.tourist = True
            self.mark_state_dirty()
        else:
            self.tourist = False

    def set_sucker(self, state: bool) -> None:
        """
        Set sucker state (used in buy/sell price calculations).

        :param state: Boolean, if True - player is sucker.
        :return: None.
        """
        if not self.sucker and state:
            logging.info("You have been identified as sucker")
            self.tmux.display_message("You are now sucker", self.msg_duration)
            self.mark_state_dirty()
        if self.sucker and not state:
            logging.info("You are no longer identified as sucker")
            self.tmux.display_message("You are no longer sucker", self.msg_duration)
            self.mark_state_dirty()
        self.sucker = state

    def check_sucker(self) -> None:
        """
        Check conditions that automatically make you a sucker.

        Currently, this handles only most common case (tourist with XL < 15).
        For other cases at this moment (dunce cap, shirt), you need to enter

        # sucker

        in extended command prompt to force NHAssist to calculate prices as if
        you're a sucker.

        :return: None.
        """
        if self.tourist:
            self.set_sucker(self.xplevel < 15)

    def restore_sync(self) -> None:
        """
        Set synced state - when NHAssist is sure that it sees a NetHack window,
        it will enable extended parsing of screen and will interact with game.

        :return: None.
        """
        logging.info("Acquired sync with NetHack @ pane %s", self.tmux.pane)
        self.state = "sync"

    def lost_sync(self) -> None:
        """
        Tell NHAssist that we've lost sync with game. This will disable further
        tracking and interactions with terminal pane until sync is re-acquired.

        :return: None
        """
        self.state = "init"
        logging.info("Lost sync with NetHack @ pane %s", self.tmux.pane)

    def mark_state_dirty(self) -> None:
        """
        This method sets dirty flag and should be called whenever we have made some
        changes that we would like to persist between NHAssist launches (e.g.
        newly-learned list of possible identities of an item).

        :return: None.
        """
        self.dirty = True

    def handle_extcmd(self, cmd: str) -> bool:
        """
        Handle extended command prompt.

        :param cmd: Contents of extended command prompt.
        :return: Boolean (if True - command was accepted and executed).
        """
        if cmd == "sucker":
            self.set_sucker(True)
        elif cmd == "!sucker":
            self.set_sucker(False)
        elif cmd == "reset":
            self.reset = True
            self.persistence_unlink()
        else:
            return False
        self.dismiss_extcmd()
        return True

    def learn_price_id(self, candidates: List[str], item: str, appearance: str) -> None:
        """
        Record knowledge, inferred from price identification.

        :param candidates: List of possible identities of item (or real identity, if
        it's only one in list).
        :param item: Item name.
        :param appearance: Item's randomized appearance.
        :return: None.
        """
        if len(candidates) == 1:
            self.tmux.display_message(
                f"Item uniquely identified: {candidates[0]}! Now call it.",
                self.msg_duration,
            )
            logging.info("Item uniquely identified: %s", candidates[0])
            short_name = candidates[0]
            self.known_items[candidates[0]] = appearance
            self.mark_state_dirty()
        else:
            logging.info("List of possible items: %s", candidates)
            short_name = abbreviate_items(candidates, self.max_abbrev_length)
            self.tmux.display_message(
                f"Possible items: {short_name}. Now call it.", self.msg_duration
            )
        if item not in self.price_id:
            self.price_id[item] = {
                "short_name": short_name,
                "candidates": candidates,
                "item_called": False,
            }
            logging.info("Alias: %s", short_name)
            self.mark_state_dirty()
        else:
            if set(candidates) != set(self.price_id[item]["candidates"]):
                self.price_id[item] = {
                    "short_name": short_name,
                    "candidates": candidates,
                    "item_called": False,
                }
                logging.info("Alias (update): %s", short_name)
                self.mark_state_dirty()

    def identify_purchase(self, item: str, price: int, buying: bool = True) -> bool:
        """
        Identify an item that's being offered or sold.

        :param item: Item's name.
        :param price: Price, that was either requested, or offered for this item.
        :param buying: Is item being purchased (otherwise - calculate selling price).
        :return: Whether price ID was successful.
        """
        if buying:
            logging.info("I see %s being offered for %s zorkmids.", item, price)
        else:
            logging.info("I see %s zorkmids being offered for %s.", price, item)
        kind, appearance = lookup_item(item)
        if kind is not None and appearance is not None:
            logging.info("Type: %s; Appearance: %s", kind, appearance)
            candidates = find_price_candidates(
                price, kind, self.charisma, self.sucker, buying=buying
            )
            candidates = list(filter(lambda x: x not in self.known_items, candidates))
            if not candidates:
                logging.info("No items have been matched for price =(")
                return False
            self.learn_price_id(candidates, item, appearance)
            return True
        return False

    def process_frame(self) -> None:
        """
        Perform a single iteration of screen analysis. Should be called repeatedly from
        main loop.

        :return: None.
        """
        self.persistence_save()
        frame = self.tmux.get_frame()
        self.find_stats()
        if self.state == "sync":
            if self.is_dead(frame):
                self.lost_sync()
                self.persistence_unlink()
                sys.exit(0)
            if self.is_writing_eword(frame) and self.autoeword:
                logging.info("Finger-engraving detected: writing E-word automatically")
                self.write_eword()
                return
            if self.invoke_ewait(frame):
                self.ewait()
                return
            if (cmd := self.read_extcmd(frame)) is not None:
                if self.handle_extcmd(cmd):
                    return
            if self.item_for_sale():
                return
            if self.item_to_sell():
                return
            if item := self.check_call_prompt():
                if self.dispatch_price_id(item):
                    return

    @abstractmethod
    def find_stats(self) -> None:
        """
        Windowport-specific method of reading main attributes from bottom status lines.
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def is_writing_eword(self, frame: str) -> bool:
        """
        Windowport-specific method of checking, whether we do dust engraving to
        autotype Elbereth. Works only if autoeword is enabled.

        :param frame: String with representation of terminal screen (frame).
        :return: Boolean, indicating that player has begun finger dust engraving.
        """
        raise NotImplementedError

    @abstractmethod
    def write_eword(self) -> None:
        """
        Windowport-specific method of actually typing Elbereth into dust engravement
        prompt.

        :return: None.
        """
        raise NotImplementedError

    @abstractmethod
    def invoke_ewait(self, frame: str) -> bool:
        """
        Detect that player wants to sleep a single turn while standing on dust Elbereth.
        Windowport-specific.

        It's bound to Ctrl+E, exploiting the fact that in non-wizardmode games such
        combination would yield a message, telling that wizdetect command is not
        available. If it's present on the screen - w.

        :param frame: String with representation of terminal screen (frame).
        :return: Boolean, indicating player's intent to skip turn on dust Elbereth.
        """
        raise NotImplementedError

    @abstractmethod
    def ewait(self) -> None:
        """
        Windowport-specific method to do a single Elbereth wait turn.

        :return: None.
        """
        raise NotImplementedError

    @abstractmethod
    def is_dead(self, frame: str) -> bool:
        """
        Windowport-specific method of checking, if player is dead (DYWYPI).

        :param frame: String with representation of terminal screen (frame).
        :return: Boolean, indicating that player has died.
        """
        raise NotImplementedError

    @abstractmethod
    def item_for_sale(self) -> bool:
        """
        Windowport-specific method of detecting information about item being sold.

        :return: Boolean, indicating whether we have found an item for sale.
        """
        raise NotImplementedError

    @abstractmethod
    def item_to_sell(self) -> bool:
        """
        Windowport-specific method of detecting that we offer an item to shopkeeper.

        :return: Boolean, indicating whether we have found offered item.
        """
        raise NotImplementedError

    @abstractmethod
    def save_and_quit(self) -> bool:
        """
        Attempt to initiate save and quit. Windowport-specific.

        :return: Whether we have successfully quit the game.
        """
        raise NotImplementedError

    @abstractmethod
    def dispatch_price_id(self, item) -> bool:
        """
        Fill type name of price-identified item. Windowport-specific.

        :param item: Name of item that's being called.
        :return: Whether item was successfully called.
        """
        raise NotImplementedError

    @abstractmethod
    def dismiss_extcmd(self) -> None:
        """
        Close an extended command prompt. Windowport-specific.

        :return: None.
        """
        raise NotImplementedError

    @abstractmethod
    def read_extcmd(self, frame) -> Optional[str]:
        """
        Fetch an extended command that's being typed. Windowport-specific.

        :param frame: String with representation of terminal screen (frame).
        :return: Extended command prompt contents or None.
        """
        raise NotImplementedError

    @abstractmethod
    def check_call_prompt(self) -> Optional[str]:
        """
        Check if calling prompt is open and which item we try to call.
        Windowport-specific.

        :return: Name of item being called, or None if prompt is not found.
        """
        raise NotImplementedError


class TtyMonitor(NHMonitor):
    """
    Implementation of NetHack monitor for tty windowport.
    """

    def read_extcmd(self, frame: str) -> Optional[str]:
        """
        Detect extended command being entered. We scan top line for # prefix.

        :param frame: String with representation of terminal screen (frame).
        :return: Extended command text.
        """
        cmd = frame.splitlines()[0]
        if cmd.startswith("# "):
            return cmd[2:]
        return None

    def dismiss_extcmd(self) -> None:
        """
        Close extended command prompt by pressing Escape twice.

        :return: None.
        """
        self.tmux.send_keys(["Escape", "Escape"])

    def dispatch_price_id(self, item: str) -> bool:
        """
        Enter name of price-identified item in prompt.

        :param item: Item name in calling prompt.
        :return: Boolean, indicating whether item was given a name.
        """
        if item in self.price_id:
            if self.price_id[item]["item_called"]:
                return False
            self.tmux.send_keys([self.price_id[item]["short_name"], "C-m"])
            self.price_id[item]["item_called"] = True
            self.tmux.wait_chg()
            logging.info('Gave name %s to %s', self.price_id[item]["short_name"], item)
            self.mark_state_dirty()
            return True
        return False

    def check_call_prompt(self) -> Optional[str]:
        """
        Check screen for call prompt presence.

        :return: Either item being called in call prompt, or None, if no call prompt.
        """
        m = self.tmux.find_pattern(const.CALL_PROMPT_RE)
        if m is not None:
            return m.group("item")
        return None

    def item_to_sell(self) -> bool:
        """
        Price identify item that's about to be sold to shopkeeper.

        :return: Whether we found pattern and attempted to price ID item.
        """
        m = self.tmux.find_pattern(const.OFFER_RE)
        if m is not None:
            item = m.group("item")
            price = int(m.group("price"))
            self.identify_purchase(item, price, buying=False)
            self.tmux.wait_chg()
            return True
        return False

    def item_for_sale(self) -> bool:
        """
        Price identify item for sale in shop.

        :return: Whether we found pattern and attempted to price ID item.
        """
        matches: List[re.Match] = []
        matches.extend(self.tmux.find_pattern_iter(const.SALE_RE, collapse=True))
        matches.extend(self.tmux.find_pattern_iter(const.PICKUP_SALE_RE, collapse=True))
        for m in matches:
            item = (
                m.group("item")
                .replace("potions", "potion")
                .replace("scrolls", "scroll")
            )
            price = int(m.group("price"))
            quantity = int(m.groupdict().get("quantity", 1) or 1)
            price = price // quantity
            self.identify_purchase(item, price)
            self.tmux.wait_chg()
            return True
        return False

    def find_stats(self) -> None:
        """
        Find attributes and other game stats and update them in monitor state.

        :return: None.
        """
        m = self.tmux.find_pattern(const.STATUS_CONT_RE)
        if m:
            self.set_turn(int(m.group("turn")))
            if m.groupdict()["xplevel"] is not None:
                self.set_xplevel(int(m.group("xplevel")))
        m = self.tmux.find_pattern(const.STATUS_RE)
        if m:
            self.set_charisma(int(m.group("charisma")))
            if self.tourist is None:
                if m.group("rank") in const.TOURIST_LOW_LEVEL:
                    self.set_tourist(True)
            self.check_sucker()

    def save_and_quit(self) -> bool:
        """
        Attempt to invoke saving dialog and answer "y" to save and quit game.

        :return: Boolean, indicating whether we have quit game.
        """
        self.tmux.send_keys("S")
        frame = self.tmux.wait_chg()
        if "Really save? [yn]" in frame:
            self.tmux.send_keys("y")
            self.lost_sync()
            return True
        return False

    def is_writing_eword(self, frame: str) -> bool:
        """
        Detect a message, indicating that player is writing in dust with fingertip.
        It's used for auto-elbereth feature, which will automatically engrave Elbereth,
        when selecting dust-engraving.

        :param frame: String with representation of terminal screen (frame).
        :return: True, if there's a message, indicating that you've started to engrave
        in dust with fingertip.
        """
        return "You write in the dust with your fingertip.--More--" in frame

    def invoke_ewait(self, frame: str) -> bool:
        """
        Detect player's attempt to wait a turn on square with Elbereth engravement.
        It's bound to Ctrl+E and uses the fact that in non-wizmode games, this hotkey
        will result in message, telling that wizdetect command is not available.

        :param frame: String with representation of terminal screen (frame).
        :return: True, if player has pressed Ctrl+E (and we found expected message).
        """
        return "Unavailable command 'wizdetect'." in frame  # Bound to Ctrl+E

    def ewait(self) -> None:
        """
        Perform a single turn of dust Elbereth waiting. This would look at current
        square to check if Elbereth engraving is present and not corrupted. If engraving
        is OK - we just use . command to rest a single turn. If engraving on current
        square is corrupted or even not present at all - we would engrave a new one
        (wiping previous engraving, if needed).

        :return: None.
        """
        self.tmux.send_keys(":")
        while True:
            frame = self.tmux.wait_chg()
            if 'You read: "Elbereth".' in frame:  # Already engraved, rest
                self.skip_more(frame, skipall=True)
                self.tmux.send_keys(".")
                frame = self.tmux.wait_chg()
                if "Are you waiting to get hit?" in frame:
                    logging.info("Cannot safely rest - enemy is near.")
                    break
                logging.info("Elbereth is already engraved, resting")
                self.tmux.send_keys(":")
                frame = self.tmux.wait_chg()
                self.skip_more(frame)
                break
            # Engraving must be corrupted or missing, fix it
            if 'You read: "' in frame or "You see no objects here." in frame:
                logging.info("Elbereth is missing or corrupt, re-engraving.")
                # self.tmux.display_message("Elbereth re-engraved", self.msg_duration)
                self.tmux.send_keys("E")
                self.tmux.wait_chg()
                self.tmux.send_keys("-")
                frame = self.tmux.wait_chg()
                if "Do you want to add to the current engraving?" in frame:
                    self.tmux.send_keys("n")
                    frame = self.tmux.wait_chg()
                self.skip_more(frame, skipall=True)
                self.tmux.send_keys("Elbereth")
                self.tmux.wait_chg()
                self.tmux.send_keys(["C-m", ":"])
                break
            if "--More--" in frame:  # Other messages obscure view
                self.skip_more(frame)
                continue
            logging.info("Unknown messages, unable to perform Elbereth rest")
            break

    def skip_more(self, frame: str, skipall: bool = False) -> None:
        """
        Find --More-- prompt on screen and skip it.

        :param frame: String with representation of terminal screen (frame).
        :param skipall: If True - skip all sequential --More-- prompts.
        :return: None.
        """
        while "--More--" in frame:
            self.tmux.send_keys("C-m")
            if not skipall:
                break
            frame = self.tmux.wait_chg()

    def write_eword(self) -> None:
        """
        Type Elbereth when finger-engraving in dust. Only used for auto-Elbereth
        feature.

        :return: None.
        """
        self.tmux.send_keys_and_wait("C-m")
        self.tmux.send_keys_and_wait("Elbereth")
        self.tmux.send_keys_and_wait("C-m")
        self.tmux.send_keys(":")

    def is_dead(self, frame: str) -> bool:
        """
        Check if player is dead. We just look for DYWYPI here.

        :param frame: String with representation of terminal screen (frame).
        :return: Whether player has died.
        """
        return "Do you want your possessions identified?" in frame


class CursesMonitor(NHMonitor):
    """
    NetHack monitor for curses windowport, not implemented at this moment.
    """

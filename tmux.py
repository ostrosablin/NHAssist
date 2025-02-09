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
A set of primitives to work with tmux session.
"""

import re
import subprocess
from subprocess import run, PIPE, CalledProcessError
from time import sleep
from typing import List, Iterator, Optional


class TmuxError(Exception):
    """
    Class for tmux-related errors.
    """


class Tmux:
    """
    Implementation of various operations over a running tmux session.
    """

    WAIT_DELAY = 0.12

    def __init__(self, pane: str):
        """
        Create a new tmux connection.

        :param pane: Pane to interact with.
        """
        self.pane = pane
        self.session = pane.split(":")[0]
        try:
            self.prev_frame = self.get_frame()
        except TmuxError as e:
            raise TmuxError(
                f"Unable to connect to tmux server! Is pane {pane} correct?"
            ) from e

    def _tmux_cmd(
        self, cmd: str, *args: str | int, sessionwide: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Build and execute a tmux command.

        :param cmd: tmux command to execute.
        :param args: Arguments for tmux command.
        :param sessionwide: If true - pass session name instead of pane to target arg.
        :return: subprocess.CompletedProcess instance for executed command.
        """
        cmdline = [
            "tmux",
            cmd,
            "-t",
            self.session if sessionwide else self.pane,
            *map(str, args),
        ]
        return run(cmdline, check=True, stdout=PIPE, encoding="utf-8")

    def get_frame(self, advance: bool = True) -> str:
        """
        Get a frame from tmux session.

        :param advance: If true, current frame will replace saved frame.
        :return: String with representation of terminal screen (frame).
        """
        try:
            frame = self._tmux_cmd("capture-pane", "-p").stdout
        except CalledProcessError as e:
            raise TmuxError("Unable to read from tmux server!") from e
        if advance:
            self.prev_frame = frame
        return frame

    def wait_chg(self) -> str:
        """
        Wait until tmux screen changes.

        :return: String with updated terminal screen (frame).
        """
        while True:
            frame = self.get_frame(advance=False)
            if frame != self.prev_frame:
                self.prev_frame = frame
                return frame
            sleep(Tmux.WAIT_DELAY)

    def wait_pattern(self, pattern: str) -> re.Match[str]:
        """
        Wait for pattern to appear on screen.

        :param pattern: Regex to search.
        :return: Match object for found pattern.
        """
        while True:
            res = self.find_pattern(pattern)
            if res is not None:
                return res
            sleep(Tmux.WAIT_DELAY)

    @staticmethod
    def _collapse_frame(frame: str) -> str:
        """
        Collapse a frame lines into a single string with excessive spacing removed.

        :param frame: String with text representation of screen.
        :return: String with newlines and excessive trailing spaces removed.
        """
        return " ".join(map(lambda x: x.strip(), frame.splitlines()))

    def find_pattern_iter(
        self, pattern: str, collapse: bool = False, advance: bool = False
    ) -> Iterator[re.Match[str]]:
        """
        Find all regex pattern matches on the screen.

        :param pattern: Regex to search.
        :param collapse: Whether to remove newlines and trailing spaces.
        :param advance: Replace saved frame with new frame.
        :return: Iterator over regex matches.
        """
        if advance:
            self.get_frame()
        frame = self.prev_frame
        if collapse:
            frame = self._collapse_frame(frame)
        return re.finditer(pattern, frame)

    def find_pattern(
        self, pattern: str, collapse: bool = False, advance: bool = False
    ) -> Optional[re.Match[str]]:
        """
        Find regex match on the screen.

        :param pattern: Regex to search.
        :param collapse: Whether to remove newlines and trailing spaces.
        :param advance: Replace saved frame with new frame.
        :return: Regex match if found, else None.
        """
        if advance:
            self.get_frame()
        frame = self.prev_frame
        if collapse:
            frame = self._collapse_frame(frame)
        return re.search(pattern, frame)

    def send_keys(self, keys: str | List[str]) -> None:
        """
        Send keypresses into tmux pane.

        :param keys: String with keys or list of strings to press.
        :return: None.
        """
        if isinstance(keys, str):
            keys = [keys]
        if not keys:
            raise ValueError("Attempt to send empty keys into tmux pane")
        try:
            self._tmux_cmd("send-keys", *keys)
        except CalledProcessError as e:
            raise TmuxError("Unable to send keys to tmux server!") from e

    def send_keys_and_wait(self, keys: str | List[str]) -> str:
        """
        Send keypresses into tmux pane and wait for screen to change.

        :param keys: String with keys or list of strings to press.
        :return: String with representation of terminal screen (frame).
        """
        self.send_keys(keys)
        return self.wait_chg()

    @staticmethod
    def extract_rectangle_area(
            frame: str, x: int, y: int, width: int, height: int
    ) -> str:
        """
        Cut out a rectangle area from frame string and return it. May be useful to e.g.
        extract curses windows.

        :param frame: String with representation of terminal screen (frame).
        :param x: X coordinate of top right corner of extracted rectangle.
        :param y: Y coordinate of top right corner of extracted rectangle.
        :param width: Width of extracted rectangle.
        :param height: Height of extracted rectangle.
        :return: String with cut out rectangle section of screen frame.
        """
        lines = frame.split("\n")

        selected_lines = lines[y : y + height]

        result = []
        for line in selected_lines:
            if len(line) < x + width:
                line += " " * (x + width - len(line))
            result.append(line[x : x + width])
        return "\n".join(result)

    def display_message(
        self, text: str, duration: int = 0, modal: bool = False
    ) -> None:
        """
        Display a message in tmux's status bar.

        :param text: Text to display.
        :param duration: Duration for which message would be displayed.
        :param modal: If True - you cannot interact with pane until message times out.
        :return: None.
        """
        if not duration:
            return
        extra_args = []
        if modal:
            extra_args.append("-N")
        duration = round(duration * 1000)
        try:
            self._tmux_cmd(
                "display-message", "-d", duration, *extra_args, text, sessionwide=True
            )
        except CalledProcessError as e:
            raise TmuxError("Unable to display message in tmux server!") from e

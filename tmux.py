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
from __future__ import annotations

import re
import subprocess
from collections import UserString
from subprocess import run, PIPE, CalledProcessError
from time import sleep
from typing import List, Iterator, Optional


class TmuxError(Exception):
    """
    Class for tmux-related errors.
    """

class TmuxFrame(UserString):
    """
    Class for captured frames (and subframes). For versatility, it's subclassed from
    UserString, ergo it can be used as a regular string with some neat helper methods.

    Each string is RegEx-searchable, allows easy parsing of sub-panes and generally
    friendly for dynamic terminal application parsing.
    """

    def __init__(self, frame: str | TmuxFrame):
        """
        Create a new Frame object.
        """
        super().__init__(str(frame))

    def parse_curses_panes(self) -> list[TmuxFrame]:
        """
        Find Curses panes in output and cut out their content.

        Panes are scanned left-to-right top-down, beginning with upper left corner.

        Usually, for NetHack, first pane would be message box, second is perm_invent (if
        enabled), third is map and fourth - status panel.

        :param frame: String with text representation of screen.
        :return: A list of pane contents (minus the borders).
        """
        lines = self.data.split('\n')
        if not lines or not lines[0]:
            return []

        height = len(lines)
        width = max(len(line) for line in lines) if lines else 0

        # Pad all lines to the same width
        padded_lines = [line.ljust(width) for line in lines]

        # Identify all potential box boundaries
        corners = {}  # (r, c) -> '┌'/'┐'/'└'/'┘'
        # horizontal_chars = {'─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴'}

        for r in range(height):
            for c in range(width):
                char = padded_lines[r][c]
                if char in ['┌', '┐', '└', '┘']:
                    corners[(r, c)] = char

        # Find all possible boxes by matching corners
        boxes = []
        corner_positions = list(corners.keys())

        for i, (r1, c1) in enumerate(corner_positions):
            if corners[(r1, c1)] != '┌':
                continue

            # Look for matching corners to form a box
            for r2 in range(r1 + 1, height):
                if padded_lines[r2][c1] == '│':
                    continue
                elif padded_lines[r2][c1] == '└':
                    # Found bottom-left corner
                    for c2 in range(c1 + 1, width):
                        if padded_lines[r1][c2] == '─':
                            continue
                        elif padded_lines[r1][c2] == '┐':
                            # Check if there's a matching bottom-right corner
                            if (r2, c2) in corners and corners[(r2, c2)] == '┘':
                                # Verify this is a valid box by checking borders
                                is_valid_box = True

                                # Check top border
                                for c in range(c1 + 1, c2):
                                    if padded_lines[r1][c] not in ['─', '┬']:
                                        is_valid_box = False
                                        break
                                if not is_valid_box:
                                    continue

                                # Check bottom border
                                for c in range(c1 + 1, c2):
                                    if padded_lines[r2][c] not in ['─', '┴']:
                                        is_valid_box = False
                                        break
                                if not is_valid_box:
                                    continue

                                # Check left border
                                for r in range(r1 + 1, r2):
                                    if padded_lines[r][c1] not in ['│', '├']:
                                        is_valid_box = False
                                        break
                                if not is_valid_box:
                                    continue

                                # Check right border
                                for r in range(r1 + 1, r2):
                                    if padded_lines[r][c2] not in ['│', '┤']:
                                        is_valid_box = False
                                        break
                                if not is_valid_box:
                                    continue

                                boxes.append((r1, c1, r2, c2))
                            break
                    break

        # Remove nested boxes (boxes completely inside other boxes)
        def is_nested(outer_box, inner_box):
            r1_o, c1_o, r2_o, c2_o = outer_box
            r1_i, c1_i, r2_i, c2_i = inner_box
            return (r1_o < r1_i and r2_o > r2_i and
                    c1_o < c1_i and c2_o > c2_i)

        filtered_boxes = []
        for i, box in enumerate(boxes):
            is_nested_in_any = False
            for j, other_box in enumerate(boxes):
                if i != j and is_nested(other_box, box):
                    is_nested_in_any = True
                    break
            if not is_nested_in_any:
                filtered_boxes.append(box)

        # Extract content from each box
        results = []
        for r1, c1, r2, c2 in filtered_boxes:
            content_lines = []
            for r in range(r1 + 1, r2):
                content_line = padded_lines[r][c1 + 1:c2]
                # Remove trailing spaces but preserve internal spaces
                content_lines.append(content_line.rstrip())

            # Join content lines and add to results if not empty
            if content_lines:
                # Remove empty lines at the end
                while content_lines and content_lines[-1] == '':
                    content_lines.pop()
                content = '\n'.join(content_lines)
                if content.strip():  # Only add if content is not just whitespace
                    results.append(TmuxFrame(content))

        return results

    def extract_rectangle_area(
            self, x: int, y: int, width: int, height: int, padding: bool = False
    ) -> TmuxFrame:
        """
        Cut out a rectangle area from frame string and return a new frame.

        :param x: X coordinate of top right corner of extracted rectangle.
        :param y: Y coordinate of top right corner of extracted rectangle.
        :param width: Width of extracted rectangle (negative for full length).
        :param height: Height of extracted rectangle (negative for full height).
        :param padding: Whether to pad strings with spaces to make a true rectangle.
        :return: TmuxFrame with cut out rectangular section of parent frame.
        """
        lines = self.data.split("\n")

        selected_lines = lines[y : y + (len(lines) if height < 0 else height)]

        result = []
        for line in selected_lines:
            cutwidth = len(line) if width < 0 else width
            if padding is True and len(line) < x + cutwidth:
                line += " " * (x + cutwidth - len(line))
            result.append(line[x : x + cutwidth])
        return TmuxFrame("\n".join(result))

    def extract_lines(self, first: int, nlines: int) -> TmuxFrame:
        """
        Extract a vertical block of (full width) lines into a separate frame.

        :param first: Y coordinate of first extracted line.
        :param nlines: Number of extracted lines.
        :return: TmuxFrame with cut out lines from frame.
        """
        return self.extract_rectangle_area(0, first, -1, nlines)

    def collapse_frame(self) -> TmuxFrame:
        """
        Vertically collapse a frame into single line with excessive spacing removed.

        :return: String with newlines and excessive trailing spaces removed.
        """
        return TmuxFrame(" ".join(map(lambda x: x.strip(), str(self).splitlines())))

    def find_pattern(self, pattern: str) -> Optional[re.Match[str]]:
        """
        Find regex match on the frame.

        :param pattern: Regex to search.
        :return: Regex match if found, else None.
        """
        return re.search(pattern, self.data)

    def find_pattern_iter(self, pattern: str) -> Iterator[re.Match[str]]:
        """
        Find all regex pattern matches on the screen.

        :param pattern: Regex to search.
        :return: Iterator over regex matches.
        """
        return re.finditer(pattern, self.data)

    def find_lines_with_pattern(self, pattern: str) -> list[int]:
        """
        Find line numbers with matches of pattern.

        :param pattern: Regex to search in lines.
        :return: List with indices of lines matching the regex.
        """
        matches = []
        for n, line in enumerate(self.splitlines()):
            if re.search(pattern, line):
                matches.append(n)
        return matches


class Tmux:
    """
    Implementation of various operations over a running tmux session.
    """

    WAIT_DELAY: float = 0.12

    def __init__(self, pane: str, busy_wait: bool = False):
        """
        Create a new tmux connection.

        :param pane: Pane to interact with.
        """
        self.pane: str = pane
        self.session: str = pane.split(":")[0]
        self.wait_update: bool = not busy_wait
        if self.wait_update:
            self._initialize_updater()
        try:
            self.prev_frame: TmuxFrame = self.get_frame()
        except TmuxError as e:
            raise TmuxError(
                f"Unable to connect to tmux server! Is pane {pane} correct?"
            ) from e

    def _tmux_cmd(
        self, cmd: str, *args: str | int, sessionwide: bool | None = False
    ) -> subprocess.CompletedProcess:
        """
        Build and execute a tmux command.

        :param cmd: tmux command to execute.
        :param args: Arguments for tmux command.
        :param sessionwide: If True - pass session name instead of pane to target arg.
        If None - don't pass target at all.
        :return: subprocess.CompletedProcess instance for executed command.
        """
        cmdline = [
            "tmux",
            cmd
        ]
        if sessionwide is not None:
            cmdline.extend(("-t", self.session if sessionwide else self.pane))
        cmdline.extend(map(str, args))
        return run(cmdline, check=True, stdout=PIPE, encoding="utf-8")

    def _initialize_updater(self) -> None:
        """
        Set up event-driven tmux
        """
        self._tmux_cmd("set-window-option", "monitor-activity", "on")
        self._tmux_cmd("set-option", "activity-action", "any", sessionwide=None)
        self._tmux_cmd(
            "set-hook", "-w", "alert-activity", "wait-for -S nhassist"
        )

    def get_frame(self, advance: bool = True, keep_spaces: bool = False) -> TmuxFrame:
        """
        Get a frame from tmux session.

        :param advance: If true, current frame will replace saved frame.
        Otherwise, a previously cached frame would be returned.
        :param keep_spaces: If true, trailing spaces within lines are preserved.
        :return: TmuxFrame with text representation of terminal screen.
        """
        args = ["-p"]
        if keep_spaces:
            args.append("-N")
        try:
            frame = TmuxFrame(self._tmux_cmd("capture-pane", *args).stdout)
        except CalledProcessError as e:
            raise TmuxError("Unable to read from tmux server!") from e
        if advance:
            self.prev_frame = frame
        return frame

    def wait_chg(self) -> TmuxFrame:
        """
        Wait until tmux screen changes.

        :return: TmuxFrame with updated terminal screen.
        """
        while True:
            if self.wait_update:
                self._tmux_cmd("wait-for", "nhassist", sessionwide=None)
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
            frame = frame.collapse_frame()
        return frame.find_pattern_iter(pattern)

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
            frame = frame.collapse_frame()
        return frame.find_pattern(pattern)

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

    def send_keys_and_wait(self, keys: str | List[str]) -> TmuxFrame:
        """
        Send keypresses into tmux pane and wait for screen to change.

        :param keys: String with keys or list of strings to press.
        :return: String with representation of terminal screen (frame).
        """
        self.send_keys(keys)
        return self.wait_chg()

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

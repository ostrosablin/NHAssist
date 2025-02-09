#!/usr/bin/env python3

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
NHAssist entry point with initialization, arg parsing, logging setup and main loop.
"""

import argparse
import logging
import sys
import time

from nhmon import TtyMonitor, CursesMonitor

# Argument parsing
parser = argparse.ArgumentParser(description='NetHack assistant')
parser.add_argument('targetpane', default=None, help="tmux pane to attach to")
parser.add_argument('-c', '--curses', action="store_true",
                    help="Whether curses windowport is used (not yet implemented)")
parser.add_argument('-a', '--abbreviation-length', default=60, type=int,
                    help="Max length for price-identified object names")
parser.add_argument('-t', '--turnlimit', default=0, type=int,
                    help="How many turns to play before being autosaved")
parser.add_argument('-A', '--aligned-turnlimit', action="store_true",
                    help="Whether to round turnlimit to nearest multiple")
parser.add_argument('-p', '--persistence', default=None,
                    help="Path to file, where known facts would be stored")
parser.add_argument('-l', '--logfile', default=None,
                    help="Path to save log file into (default - don't write logs)")
parser.add_argument('-e', '--auto-elbereth', action="store_true",
                    help="When engraving in dust with finger, always write Elbereth")

try:
    args = parser.parse_args()
except (argparse.ArgumentError, argparse.ArgumentTypeError):
    parser.print_help()
    sys.exit(0)

# Arg checking
if args.abbreviation_length < 1:
    raise ValueError("Abbreviation length must be a positive number!")
if args.turnlimit:
    if args.turnlimit < 1:
        raise ValueError("Turnlimit must be a non-negative number!")
else:
    if args.aligned_turnlimit:
        raise ValueError("Aligned turnlimit option is only valid when turnlimit is enabled!")

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logformat = logging.Formatter(
    "[%(levelname)s] %(asctime)s - %(funcName)s: %(message)s"
)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logformat)
logger.addHandler(handler)
if args.logfile is not None:
    filehandler = logging.FileHandler(args.logfile, encoding="utf-8")
    filehandler.setLevel(logging.DEBUG)
    filehandler.setFormatter(logformat)
    logger.addHandler(filehandler)

# Main loop
MonitorClass = CursesMonitor if args.curses else TtyMonitor

monitor = MonitorClass(args)

while not monitor.stopping:
    if monitor.reset:
        monitor = MonitorClass(args)
    monitor.process_frame()
    time.sleep(0.12)

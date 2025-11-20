# NHAssist: Automated price identification and tedium removal tool
Did you ever wanted to automate price identification in **NetHack** and focus on
more interesting aspects of game?

You've come to right place: **NHAssist** is your companion tool for **NetHack** that
will do the boring stuff that adds no value to game for you.

## How does this work?
It's as simple as this:

![NHAssist demo](https://github.com/ostrosablin/nhassist/blob/master/img/nhassistdemo.gif?raw=true "NHAssist demo")

## Main features
- **NHAssist** was primarily designed as an automated item identification tool.
- It's designed to work both with locally running NetHack and **public servers**.
Because of this it relies exclusively on parsing terminal output.
- It has support for some other useful features, such that automated check for
Elbereth corruption under you.
- There's an automatic save-and-quit feature that exits the game after specified
number of turns. It's essentially an out-of-game implementation of
[my idea](https://github.com/NetHack/NetHack/issues/208) that was not implemented
in game natively. This can be used to play round-robin games by giving control
to another person after N turns or just for limiting your play sessions.

## What is NHAssist not:
**NHAssist** is **not**:
- An in-game spoiler encyclopedia. Use [NetHack Wiki](https://nethackwiki.com) for
that. Only a small subset of spoilers (mostly involving simple table lookups) are
in scope of **NHAssist**.
- A cheating tool. It won't do anything that involves techniques that are considered
cheating by community, including dumplog bones identification, bug expoitation, etc.
- A bot. It won't play the game for you, fight for you, make any strategic and
tactical decisions. It's designed to automate simple and tedious actions (such as
looking up an item in price table and giving it a name, or checking engraved Elbereth
under you and reengraving it before resting a turn if needed). Most actions must be
explicitly initiated by player.

## Dependencies:
- **NetHack 3.7.0** WIP. It's not released yet, but you could either compile it from
sources and play locally, or over SSH on **Hardfought** public server.
- **Python 3.10+**. It uses only standard library, no third-party libraries needed.
- **tmux**. For all interactions with NetHack, **NHAssist** relies on **tmux**, so
it's assumed that you have it installed.

It's tested only on Linux platform, although it's possible that it will work e.g. in
Cygwin on Windows.

## Installation:
**NHAssist** doesn't need installation - you can just clone the repository (or grab
it from releases) and run nhassist.py from terminal.

## Running:
Generally, you just need to run nhassist.py and also specify a tmux session and pane
where NetHack would be run. You also probably want to enable persistence, so that
NHAssist will remember facts across restarts.

Here's an example command-line:

    python ./nhassist.py 0:10 -p ~/hardfought.json -l ~/hardfought.log

To enable automatically engraving Elbereth when dust engraving with fingertip, add
`--auto-elbereth` option.

If you want to limit game session with specific number of turns, add `-t` option,
followed with number of turns you want to play. For example, if you're on turn
**1263**, passing `-t 1000` will try to save game on turn **2263**. There's also
an option `--aligned-turnlimit` that will round turnlimit to next nearest multiple
of turnlimit, so in above example, it would try to save on turn **2000**.

## Usage:
Automatic price ID works in background and does a price ID table lookup whenever
it sees message about seeing an item for sale in shop or when shopkeeper offers
you money for a dropped item. If item is successfully price-identified, you will
be notified through **tmux**'s status bar and then just need to open call prompt
for this item and **NHAssist** would automatically give it a name.

If you want to rest a single turn on an Elbereth-protected square - press `Ctrl+E`.
This would automatically engrave Elbereth on current square if it's absent or
will re-engrave if it's become corrupted. Rest command will be used only when
**NHAssist** is sure that Elbereth is present and effective and there's no monsters
next to you. **Note** that this won't work in wizard mode, because `Ctrl+E` is
already bound to `wizdetect` command.

If you have started **NHAssist** with `--auto-elbereth` option, choosing `-` from
engraving menu to do a dust engraving with fingertip will automatically type
`Elbereth` in prompt and press `Enter`.

Also, **NHAssist** supports fake extended commands. You can open the extended
command prompt in game and type `# sucker` to mark character as sucker and do
appropriate price calculations (this may be needed if you wear a shirt or dunce
cap). When you are no longer sucker, type `# !sucker` in prompt. Note that this
shouldn't be needed for a low-level Tourist, as **NHAssist** tracks this
automatically. Finally, if you want reset **NHAssist** and wipe all knowledge
learned so far, you can type `# reset` in extended command prompt.

## Future plans:
- Currently, **NHAssist** only supports tty windowport. However, it would be great
to support working with curses windowport, too. Some stubs are already present, and
windowport-specific functionality is separated from common logic, but there's no
implementation for curses.
- Other forms of automated identification: wand ID, ring ID, gem ID.
- Improve sucker status autodetection and learn more information from game messages,
parse discoveries list, etc.
- Support updating item names based on new information.
- Improve feedback during gameplay.
- Possibly, some other useful macros and automated real-time analysis.

## Known issues:
- **NHAssist** generally relies on regex pattern matching and substring search.
There are many ways you can intentionally break it by entering certain strings
into unexpected places and prompts. It's a helper tool, and if you try to break 
it - you probably don't need help anyway. There are no plans to fix such cases,
unless there are false detects/misdetects during normal use.

## Contributing:
Any contributions are welcome. Feel free to open a pull request or report an issue.
When reporting an issue, please, try to collect as much information as possible
(preferably a ttyrec, **NHAssist** log and persistence file), as this will make it
much easier to reproduce and fix it.

## License:
![GPLv3](https://github.com/ostrosablin/nhassist/blob/master/img/gplv3.png?raw=true "GPLv3")

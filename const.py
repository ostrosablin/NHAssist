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
Constants that are used across NHAssist.
"""

# Parsing regexes:
# Price ID regexes
SALE_RE = (
        r"(?:You see here |Things that are here: )?(a|an|(?P<quantity>\d+)) "
        r"(?P<item>[\w -]+) \(for sale, (?P<price>\d+) zorkmids\)"
)
PICKUP_SALE_RE = (
    r"\"For you, [\w ]+; only (?P<price>\d+) zorkmids for this (?P<item>.+)\.\""
)
OFFER_RE = (
        r"[\w -'=]+ offers (?P<price>\d+) gold pieces "
        r"for your (?P<item>[\w -]+).(?:  Sell it\?)?"
)

# Status regexes
STATUS_RE = (
    r"\[(?P<name>[\w _-]+?)\s+the\s+(?P<rank>[\w _-]+?)\s+\]\s+"
    r"St:(?P<strength>\d+(\/\d+)?)\s+Dx:(?P<dexterity>\d+)\s+"
    r"Co:(?P<constitution>\d+)\s+In:(?P<intelligence>\d+)\s+"
    r"Wi:(?P<wisdom>\d+)\s+Ch:(?P<charisma>\d+)\s+(?P<alignment>\w+)"
)
STATUS_CONT_RE = (
    r"(?:Dlvl:)?((?P<dlvl>\d+)|(?P<plane>[\w ]+))\s+\$:(?P<money>\d+)\s+"
    r"HP:(?P<hp>\d+)\((?P<maxhp>\d+)\)\s+Pw:(?P<pw>\d+)\((?P<maxpw>\d+)\)\s+"
    r"AC:(?P<ac>-?\d+)\s+(?:Xp:|HD:)((?P<xplevel>\d+)\/(?P<xp>\d+)|(?P<hd>\d+))\s+"
    r"T:(?P<turn>\d+)"
)

# Empty call prompt is open
CALL_PROMPT_RE = r"^Call (a|an) (?P<item>[\w -]+)\:\s\s+"

# Worn item regex
WORN_RE = r"[A-Za-z]\s-\s(a|an)\s((\+|-)\d+)?\s(?P<item>\w+)\s\(being worn\)"

# Discoveries list regex
DISCOVERY_RE = (
    r"(\*| ) (?P<item>[\w ]+?)( called (?P<called>.+))? \((?P<appearance>[\w ]+)\)"
)

# Tourist sucker detection.
TOURIST_LOW_LEVEL = (
    "Rambler",
    "Sightseer",
    "Excursionist",
    "Peregrinator",
    "Peregrinatrix",
    "Traveler",
)

# Price ID tables
COST_TABLES = {
    "boots": {
        8: ["elven boots", "kicking boots"],
        30: ["fumble boots", "levitation boots"],
        50: ["jumping boots", "speed boots", "water walking boots"],
    },
    "cloak": {
        40: ["leather cloak", "orcish cloak"],
        50: ["cloak of displacement", "cloak of protection"],
        60: ["cloak of invisibility", "cloak of magic resistance"],
    },
    "helm": {
        10: ["helmet"],
        50: [
            "helm of brilliance",
            "helm of opposite alignment",
            "helm of telepathy",
            "helm of caution",
        ],
    },
    "gloves": {
        8: ["leather gloves"],
        50: ["gauntlets of dexterity", "gauntlets of fumbling", "gauntlets of power"],
    },
    "scroll": {
        20: ["scroll of identify"],
        50: ["scroll of light"],
        60: ["scroll of enchant weapon"],
        80: ["scroll of enchant armor", "scroll of remove curse"],
        100: [
            "scroll of confuse monster",
            "scroll of destroy armor",
            "scroll of fire",
            "scroll of food detection",
            "scroll of gold detection",
            "scroll of magic mapping",
            "scroll of scare monster",
            "scroll of teleportation",
        ],
        200: [
            "scroll of amnesia",
            "scroll of create monster",
            "scroll of earth",
            "scroll of taming",
        ],
        300: [
            "scroll of charging",
            "scroll of genocide",
            "scroll of punishment",
            "scroll of stinking cloud",
        ],
    },
    "potion": {
        20: ["potion of healing"],
        50: [
            "potion of booze",
            "potion of fruit juice",
            "potion of see invisible",
            "potion of sickness",
        ],
        100: [
            "potion of confusion",
            "potion of extra healing",
            "potion of hallucination",
            "potion of restore ability",
            "potion of sleeping",
        ],
        150: [
            "potion of blindness",
            "potion of gain energy",
            "potion of invisibility",
            "potion of monster detection",
            "potion of object detection",
        ],
        200: [
            "potion of enlightenment",
            "potion of full healing",
            "potion of levitation",
            "potion of polymorph",
            "potion of speed",
        ],
        250: ["potion of acid", "potion of oil"],
        300: ["potion of gain ability", "potion of gain level", "potion of paralysis"],
    },
    "ring": {
        100: [
            "ring of adornment",
            "ring of hunger",
            "ring of protection",
            "ring of protection from shape changers",
            "ring of stealth",
            "ring of sustain ability",
            "ring of warning",
        ],
        150: [
            "ring of aggravate monster",
            "ring of cold resistance",
            "ring of gain constitution",
            "ring of gain strength",
            "ring of increase accuracy",
            "ring of increase damage",
            "ring of invisibility",
            "ring of poison resistance",
            "ring of see invisible",
            "ring of shock resistance",
        ],
        200: [
            "ring of fire resistance",
            "ring of free action",
            "ring of levitation",
            "ring of regeneration",
            "ring of searching",
            "ring of slow digestion",
            "ring of teleportation",
        ],
        300: [
            "ring of conflict",
            "ring of polymorph",
            "ring of polymorph control",
            "ring of teleport control",
        ],
    },
    "wand": {
        100: ["wand of light", "wand of nothing"],
        150: [
            "wand of digging",
            "wand of enlightenment",
            "wand of locking",
            "wand of magic missile",
            "wand of make invisible",
            "wand of opening",
            "wand of probing",
            "wand of secret door detection",
            "wand of slow monster",
            "wand of speed monster",
            "wand of striking",
            "wand of undead turning",
        ],
        175: ["wand of cold", "wand of fire", "wand of lightning", "wand of sleep"],
        200: [
            "wand of cancellation",
            "wand of create monster",
            "wand of polymorph",
            "wand of teleportation",
        ],
        500: ["wand of death", "wand of wishing"],
    },
    "spellbook": {
        100: [
            "spellbook of force bolt",
            "spellbook of protection",
            "spellbook of detect monsters",
            "spellbook of light",
            "spellbook of sleep",
            "spellbook of jumping",
            "spellbook of healing",
            "spellbook of knock",
        ],
        200: [
            "spellbook of magic missile",
            "spellbook of drain life",
            "spellbook of create monster",
            "spellbook of detect food",
            "spellbook of confuse monster",
            "spellbook of slow monster",
            "spellbook of cure blindness",
            "spellbook of wizard lock",
            "spellbook of chain lightning",
        ],
        300: [
            "spellbook of remove curse",
            "spellbook of clairvoyance",
            "spellbook of detect unseen",
            "spellbook of identify",
            "spellbook of cause fear",
            "spellbook of charm monster",
            "spellbook of haste self",
            "spellbook of cure sickness",
            "spellbook of extra healing",
            "spellbook of stone to flesh",
        ],
        400: [
            "spellbook of cone of cold",
            "spellbook of fireball",
            "spellbook of detect treasure",
            "spellbook of invisibility",
            "spellbook of levitation",
            "spellbook of restore ability",
        ],
        500: ["spellbook of magic mapping", "spellbook of dig"],
        600: [
            "spellbook of create familiar",
            "spellbook of turn undead",
            "spellbook of teleport away",
            "spellbook of polymorph",
        ],
        700: ["spellbook of finger of death", "spellbook of cancellation"],
    },
}

# Table of random appearances
RANDOM_APPEARANCES = {
    "scroll": [
        "ZELGO MER",
        "JUYED AWK YACC",
        "NR 9",
        "XIXAXA XOXAXA XUXAXA",
        "PRATYAVAYAH",
        "DAIYEN FOOELS",
        "LEP GEX VEN ZEA",
        "PRIRUTSENIE",
        "ELBIB YLOH",
        "VERR YED HORRE",
        "VENZAR BORGAVVE",
        "THARR",
        "YUM YUM",
        "KERNOD WEL",
        "ELAM EBOW",
        "DUAM XNAHT",
        "ANDOVA BEGARIN",
        "KIRJE",
        "VE FORBRYDERNE",
        "HACKEM MUCHE",
        "VELOX NEB",
        "FOOBIE BLETCH",
        "TEMOV",
        "GARVEN DEH",
        "READ ME",
        "ETAOIN SHRDLU",
        "LOREM IPSUM",
        "FNORD",
        "KO BATE",
        "ABRA KA DABRA",
        "ASHPD SODALG",
        "MAPIRO MAHAMA DIROMAT",
        "GNIK SISI VLE",
        "HAPAX LEGOMENON",
        "EIRIS SAZUN IDISI",
        "PHOL ENDE WODAN",
        "GHOTI",
        "ZLORFIK",
        "VAS CORP BET MANI",
        "STRC PRST SKRZ KRK",
        "XOR OTA",
    ],
    "potion": [
        "ruby",
        "pink",
        "orange",
        "yellow",
        "emerald",
        "dark green",
        "cyan",
        "sky blue",
        "brilliant blue",
        "magenta",
        "purple-red",
        "puce",
        "milky",
        "swirly",
        "bubbly",
        "smoky",
        "cloudy",
        "effervescent",
        "black",
        "golden",
        "brown",
        "fizzy",
        "dark",
        "white",
        "murky",
    ],
    "spellbook": [
        "parchment",
        "vellum",
        "ragged",
        "dog eared",
        "mottled",
        "stained",
        "cloth",
        "leather",
        "white",
        "pink",
        "red",
        "orange",
        "yellow",
        "velvet",
        "light green",
        "dark green",
        "turquoise",
        "cyan",
        "light blue",
        "dark blue",
        "indigo",
        "magenta",
        "purple",
        "violet",
        "tan",
        "plaid",
        "light brown",
        "dark brown",
        "gray",
        "wrinkled",
        "dusty",
        "bronze",
        "copper",
        "silver",
        "gold",
        "glittering",
        "shining",
        "dull",
        "thin",
        "thick",
        "checkered",
    ],
    "ring": [
        "pearl",
        "iron",
        "twisted",
        "steel",
        "wire",
        "engagement",
        "shiny",
        "bronze",
        "brass",
        "copper",
        "silver",
        "gold",
        "wooden",
        "granite",
        "opal",
        "clay",
        "coral",
        "black onyx",
        "moonstone",
        "tiger eye",
        "jade",
        "agate",
        "topaz",
        "sapphire",
        "ruby",
        "diamond",
        "ivory",
        "emerald",
    ],
    "amulet": [
        "circular",
        "spherical",
        "oval",
        "triangular",
        "pyramidal",
        "square",
        "concave",
        "hexagonal",
        "octagonal",
    ],
    "wand": [
        "aluminum",
        "balsa",
        "brass",
        "copper",
        "crystal",
        "curved",
        "ebony",
        "forked",
        "glass",
        "hexagonal",
        "iridium",
        "iron",
        "jeweled",
        "long",
        "maple",
        "marble",
        "oak",
        "pine",
        "platinum",
        "runed",
        "short",
        "silver",
        "spiked",
        "steel",
        "tin",
        "uranium",
        "zinc",
    ],
    "helmet": ["plumed", "etched", "crested", "visored"],
    "cloak": ["tattered cape", "ornamental cope", "opera cloak", "piece of cloth"],
    "gloves": ["old", "padded", "riding", "fencing"],
    "boots": ["mud", "snow", "riding", "buckled", "hiking", "combat", "jungle"],
}

# Items that have fixed appearance
FIXED_APPEARANCE = {
    "coarse mantelet": "orcish cloak",
    "apron": "alchemy smock",
    "hooded cloak": "dwarvish cloak",
    "slippery cloak": "oilskin cloak",
    "faded pall": "elven cloak",
    "unlabeled scroll": "blank paper",
    "clear potion": "water",
}

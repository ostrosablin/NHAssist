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
Price ID module - all price computation and guesses go here.
"""

from math import ceil
from typing import List, Optional, Tuple

import const


def get_charisma_multiplier(charisma: int) -> float:
    """
    Calculate buy price multiplier for given charisma.

    :param charisma: Character's charisma value.
    :return: Float price multiplier.
    """
    mul = 1.0
    if charisma <= 5:
        mul = 2.0
    elif charisma <= 7:
        mul = 1.5
    elif charisma <= 10:
        mul = 4 / 3
    elif charisma <= 15:
        mul = 1.0
    elif charisma <= 17:
        mul = 0.75
    elif charisma <= 18:
        mul = 2 / 3
    elif charisma >= 19:
        mul = 0.5
    return mul

def guess_base_cost_buying(
    price: int, charisma: int, sucker: Optional[bool] = None
) -> List[int]:
    """
    Return possible base prices for specified buy price.

    :param price: Price, requested by shopkeeper for item.
    :param charisma: Player's charisma.
    :param sucker: Whether player is sucker (being charged with extra 1/3 markup).
    :return: List of possible base prices for item.
    """
    uncharismated = price / (get_charisma_multiplier(charisma))
    candidates = [
        round(uncharismated),
        round(uncharismated / (4 / 3)),
        round(uncharismated / (16 / 9)),
    ]
    if sucker is None:
        # If it's unknown, whether player is sucker - we return all possible prices.
        return candidates
    return candidates[1:3] if sucker else candidates[0:2]


def guess_base_cost_selling(price: int, sucker: bool = False) -> List[int]:
    """
    Return possible base prices for specified sell price.

    :param price: Price, offered by shopkeeper for item.
    :param sucker: Whether player is sucker (being offered just 1/3 of price).
    :return: List of possible base prices for item.
    """
    if price == 1:
        return [2, 2]
    multiplier = 3 if sucker else 2
    nearest = 5 if price >= 5 else 2
    # This formula expoits the fact that most base prices in NetHack can be represented
    # as multiples of 5, so we can round to nearest 0 or 5 to cancel out rounding error
    # and get the right price.
    # While this works for vanilla NetHack 3.7.0, it's based on brittle assumptions and
    # not guaranteed to work at all for variants that have different base prices.
    return [
        nearest * round(price * multiplier / nearest),
        nearest * round(price * multiplier * 4 / 3 / nearest),
    ]


def erase_types(item_list: List[str]) -> List[str]:
    """
    Strip item type from item name.

    :param item_list: List of item names.
    :return: List of item names without type.
    """
    types = (
        " boots",
        " cloak",
        "cloak of ",
        "helm of ",
        " gloves",
        "gauntlets of ",
        "scroll of ",
        "potion of ",
        "ring of ",
        "wand of ",
        "spellbook of ",
    )
    new_list = []
    for item in item_list:
        for substr in types:
            item = item.replace(substr, "")
        new_list.append(item)
    return new_list


def abbreviate_items(item_list: List[str], target_length: int) -> str:
    """
    Abbreviate a list of possible items and make them fit into name string for object.

    We always strip type names from candidates, because it has no value, since type
    is present in object description anyway. Then we try to fit names into
    slash-delimited string as is. If it cannot fit into target length, we remove spaces
    between words, capitalize each word and try to fit it, gradually removing more
    letters in each item name until it fits into target length.

    The point is to make alias with candidate items to be as readable as possible
    trying to avoid the need to lookup very short abbreviations.

    :param item_list: List of candidate items to abbreviate.
    :param target_length: Max description string length.
    :return: String that contains slash-separated abbreviated item names.
    """
    item_list = erase_types(item_list)
    # Trivial case - items fit as is:
    result = "/".join(item_list)
    if len(result) <= target_length:
        return result
    # Dictionary resize
    # 5-step dictionary resize
    items = []
    no_short = True
    for i in range(5):
        min_step = i
        items = []
        no_short = i != 0
        for item in item_list:
            if i == 0:
                items.append("".join(map(lambda x: x.capitalize(), item.split())))
            else:
                short_forms = const.ABBREV_DICT.get(item)
                if short_forms is not None:
                    no_short = False
                    items.append(short_forms[i - 1])
                else:
                    items.append(item)
        if no_short:
            break  # No use, list doesn't have an abbrev dict
        result = "/".join(items)
        if len(result) <= target_length:
            if min_step == 0:
                return result
            else:
                break  # Try to refine result
    else:
        min_step = -1  # Cannot fit with dict algorithm, skip next step.
    # Fine tuning - try to squeeze out most of our remaining char budget
    if not no_short and min_step > 0:
        final_list = []
        budget = target_length - len(result)
        zip_obj = zip(item_list, items)
        # Heurestics - we expand most heavily shortened item name
        for item, short in sorted(zip_obj, key=lambda x: len(x[0]) / len(x[1])):
            if min_step == 1:
                alternative = "".join(map(lambda x: x.capitalize(), item.split()))
            else:
                alternative = item
                if (short_forms := const.ABBREV_DICT.get(item)) is not None:
                    alternative = short_forms[min_step - 2]
            if short == alternative:
                final_list.append(short)  # No change
                continue
            budget_diff = len(alternative) - len(short)
            if budget_diff > budget:
                final_list.append(short)
                continue  # Out of budget, ignore
            else:
                final_list.append(alternative)
                budget -= budget_diff
        return "/".join(sorted(final_list))
    # Fallback to old algorithm: begin generic dynamic resize
    items = []
    max_wordlen = 0
    for item in item_list:
        words = list(map(lambda x: x.capitalize(), item.split()))
        for word in words:
            max_wordlen = max(max_wordlen, len(word))
        items.append(words)
    for wordsize in range(max_wordlen, 0, -1):
        shortitems = []
        for itemwords in items:
            shortwords = []
            for word in itemwords:
                shortwords.append(word[: ceil(wordsize / len(itemwords))])
            shortitems.append("".join(shortwords))
        result = "/".join(shortitems)
        if len(result) <= target_length or wordsize == 1:
            return result
    return result


def full_random_item_name(kind: str, appearance: str) -> str:
    """
    Construct a full item name. For most items it's just appearance followed by type,
    however, cloaks and scrolls have special treatment.

    :param kind: Item type.
    :param appearance: Item appearance.
    :return: Full randomized item name.
    """
    if kind == "scroll":
        return f"scroll labeled {appearance}"
    if kind == "cloak":
        return appearance
    return f"{appearance} {kind}"


def lookup_item(item: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Lookup item in list of possible appearances.

    :param item: Item name.
    :return: Tuple of kind and appearance. If no item was matched - both will be None.
    """
    for kind, appearances in const.RANDOM_APPEARANCES.items():
        for appearance in appearances:
            if full_random_item_name(kind, appearance) == item:
                return kind, appearance
    return None, None


def find_price_candidates(
    price: int,
    kind: str,
    charisma: int,
    sucker: Optional[bool] = None,
    buying: bool = True,
) -> List[str]:
    """
    Find a list of possible items for current player.

    :param price: Price offered/requested for item.
    :param kind: Item type.
    :param charisma: Player's charisma (only has effect on buying).
    :param sucker: Whether player is sucker.
    :param buying: Look up items for purchase, rather than for sale.
    :return: List of matched candidate items, inferred from price.
    """
    candidates = []
    if buying:
        possible_prices = guess_base_cost_buying(price, charisma, sucker)
    else:
        possible_prices = guess_base_cost_selling(
            price, sucker if sucker is not None else False
        )
    for opt in possible_prices:
        if opt in const.COST_TABLES[kind]:
            candidates.extend(const.COST_TABLES[kind][opt])
    return candidates


def is_shk_greedy(
    price: int, kind: str, sucker: Optional[bool] = None
) -> Optional[bool]:
    """
    Determine, whether shopkeeper is greedy.

    :param price: Price, offered by shopkeeper for item.
    :param kind: Item type.
    :param sucker: Whether you're a sucker.
    :return:
    """
    possible_prices = guess_base_cost_selling(
        price, sucker if sucker is not None else False
    )
    if possible_prices[1] in const.COST_TABLES[kind]:
        if possible_prices[0] not in const.COST_TABLES:
            # Only greedy price is valid, shk must be greedy.
            return True
        # Not sure.
        return None
    if possible_prices[0] not in const.COST_TABLES:
        # Neither price has matched, greediness cannot be inferred.
        return None
    # Only main price is possible, shk is not greedy.
    return False

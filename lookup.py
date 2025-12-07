import priceid

ITEM_TYPES = {
    "[": ("boots", "cloak", "helm", "gloves"),
    "?": "scroll",
    "!": "potion",
    "=": "ring",
    "/": "wand",
    "+": "spellbook",
}

while True:
    while True:
        try:
            charisma = int(input("Charisma (type 0 if selling item): "))
            if charisma != 0 and not (3 <= charisma <= 18):
                raise ValueError("Invalid Charisma")
            break
        except ValueError:
            print("Invalid charisma value. Must be in range 3 <= Charisma <= 18 or 0")
    while True:
        item = input("Enter item type symbol: ")
        if len(item) > 0 and item[0] in ITEM_TYPES:
            item = ITEM_TYPES[item[0]]
            if isinstance(item, str):
                item = (item,)
            break
        print(
            f"Invalid item symbol, choose one of: {" ".join(list(ITEM_TYPES.keys()))}"
        )
    while True:
        try:
            price = int(input(f"{'Buying' if charisma else 'Selling'} price: "))
            if price < 1:
                raise ValueError("Invalid price")
            break
        except ValueError:
            print("Invalid price value. Enter a positive integer.")
    sucker = input("Are you tourist or wearing dunce cap [y/N]?: ").lower()
    sucker = True if sucker.startswith("y") else False
    print()
    no_match = True
    for kind in item:
        items = priceid.find_price_candidates(
            price, kind, charisma, sucker, bool(charisma)
        )
        if items:
            if no_match:
                print("List of items mathing your query:\n")
            no_match = False
            if len(item) > 1:
                print(f"{kind}:")
            for obj in items:
                print(obj)
            print()
            print("Call prompt name: " + priceid.abbreviate_items(items, 60) + "\n")
    if no_match:
        print("No items have matched your query\n")
    input("Press Enter to run another query, or Ctrl+C to quit.\n")

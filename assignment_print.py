# read assignments from file and print them

import json

with open('files/assignments.json', 'r') as f:
    assignments = json.load(f)

print(len(assignments))

for assignment in assignments:
    print("* " + assignment + ":\n  * ", end='')
    cards = assignments[assignment]
    card = cards[0]
    other_card = cards[1] if len(cards) > 1 else None
    if other_card is not None:
        print('{} // {}'.format(card, other_card))
    else:
        print(card)
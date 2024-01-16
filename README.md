# Battle of the Cents

## Description
This repository is a python program to generate and assign players their commanders for the budget challenge "Battle of the Cents".

## Files
* `battle_of_the_cents.py`: The main python program. Generates "botc_challenge.json" containing all legal commanders through EDHREC and Scryfall API calls.
* `lottery.py`: Lottery GUI to assign players their commanders. You need to have a `players.txt` file in the files folder with the names of the players, one per line.
* `assignment_print.py`: Pretty print the assigned commanders.
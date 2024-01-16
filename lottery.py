import json
import os
import random

import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
import requests
import time

from steps.scryfall_cleanup_and_price_filter import ScryfallCleanupStep

with open('files/botc_challenge.json', 'r') as f:
    data = json.load(f)


def draw_idx_from_main_pool(tried_indexes: list):
    pool = range(len(data['card_pool']))
    # remove tried indexes
    pool = [x for x in pool if x not in tried_indexes]
    if len(pool) == 0:
        raise PoolExhaustedException('main_pool')
    return random.choice(pool)


class PoolExhaustedException(Exception):
    def __init__(self, pool):
        super().__init__("Pool {} exhausted".format(pool))
        self.pool = pool


def draw_idx_from_multi_pool(index_pool, tried_indexes: list):
    pool = data['additional_data'][index_pool]
    # remove tried indexes
    pool = [x for x in pool if x not in tried_indexes]
    if len(pool) == 0:
        raise PoolExhaustedException(index_pool)
    return random.choice(pool)


def draw_multi_pool(index):
    # we read from json, so keys are strings
    index = str(index)
    pools = data['additional_data']['multi_commander_card_indexes_reverse'][index]
    # random pool
    pool = random.choice(pools)
    return pool


def get_corresponding_pool(pool):
    switcher = {
        'partner_card_indexes': 'partner_card_indexes',
        'partner_with_card_indexes': 'partner_with_card_other_indexes',
        'background_card_indexes': 'choose_a_background_card_indexes',
        'choose_a_background_card_indexes': 'background_card_indexes',
        'doctor_card_indexes': 'doctor_companion_card_indexes',
        'doctor_companion_card_indexes': 'doctor_card_indexes',
        'friends_forever_card_indexes': 'friends_forever_card_indexes'
    }
    return switcher.get(pool, 'Invalid pool')


def get_illegal_pool(pool):
    switcher = {
        'partner_card_indexes': 'partner_illegal_pool',
        'partner_with_card_indexes': None,
        'background_card_indexes': 'background_illegal_pool',
        'choose_a_background_card_indexes': 'background_illegal_pool',
        'doctor_card_indexes': 'doctor_illegal_pool',
        'doctor_companion_card_indexes': 'doctor_illegal_pool',
        'friends_forever_card_indexes': 'friends_forever_illegal_pool'
    }
    return switcher.get(pool, 'Invalid pool')


def draw_for_multi_index(index, tried_indexes: list):
    pool = draw_multi_pool(index)
    # get corresponding pool
    corresponding_pool = get_corresponding_pool(pool)
    # if corresponding pool is 'partner_with_card_other_indexes', we need to find the exact partner
    if corresponding_pool == 'partner_with_card_other_indexes':
        other_idx = data['additional_data'][corresponding_pool][str(index)]
        if other_idx in tried_indexes:
            raise PoolExhaustedException(pool)
        return other_idx, pool
    if index not in tried_indexes:
        tried_indexes.append(index)
    drawn_idx = draw_idx_from_multi_pool(corresponding_pool, tried_indexes)
    return drawn_idx, pool


def check_legal_pairing(card, other_card, pool):
    illegal_pool = get_illegal_pool(pool)
    if illegal_pool is None or card['name'] not in data['additional_data'][illegal_pool]:
        return True
    if other_card['name'] in data['additional_data'][illegal_pool][card['name']]:
        return False
    return True


# load pulled from file
if os.path.exists('files/pulled.json'):
    with open('files/pulled.json', 'r') as f:
        pulled = json.load(f)
else:
    pulled = []

# load players from file (just names one per line txt)
if os.path.exists('files/players.txt'):
    with open('files/players.txt', 'r') as f:
        players = f.readlines()
        players = [x.strip() for x in players]
else:
    print('No players file found')
    exit(1)

# load assignments from file (json)
if os.path.exists('files/assignments.json'):
    with open('files/assignments.json', 'r') as f:
        assignments = json.load(f)
else:
    assignments = {}

next_player = None
# get the next player in list not in assignments
for player in players:
    if player not in assignments:
        next_player = player
        break

if next_player is None:
    print('All players assigned')
    exit(0)

exhausted_pools = []


def draw(veto_filter=lambda x: True):
    tried_indexes = []
    # add all indexes of exhausted pools to tried_indexes
    for pool in exhausted_pools:
        tried_indexes += data['additional_data'][pool]

    # pick a random index from the data['additional_data']['multi_commander_card_indexes']
    index = draw_idx_from_main_pool(tried_indexes)
    tried_indexes.append(index)

    card = data['card_pool'][index]

    while not veto_filter(card) or card['name'] in pulled:
        index = draw_idx_from_main_pool(tried_indexes)
        card = data['card_pool'][index]
        tried_indexes.append(index)

    other_card = None

    try:
        # check if index is in multicommander pool
        if index in data['additional_data']['multi_commander_card_indexes']:
            other_idx, pool = draw_for_multi_index(index, tried_indexes)
            tried_indexes.append(other_idx)
            # check if legal pairing
            other_card = data['card_pool'][other_idx]
            while not check_legal_pairing(card, other_card, pool) or other_card['name'] in pulled:
                other_idx, pool = draw_for_multi_index(index, tried_indexes)
                other_card = data['card_pool'][other_idx]
                tried_indexes.append(other_idx)
    except PoolExhaustedException as e:
        exhausted_pools.append(e.pool)
        # also add corresponding pool
        exhausted_pools.append(get_corresponding_pool(e.pool))
        print('Pool {} exhausted'.format(e.pool))
        return draw(veto_filter)
    return card, other_card


def get_img(card):
    if os.path.exists('imgs/{}.jpg'.format(card['name'])):
        return card['name']

    card_name = card['name']

    if '// ' in card_name:
        # double faced card
        card_name = card_name.split('//')[0].strip()

    if '"' in card_name:
        # sanitize card name
        card_name = card_name.replace('"', '')

    if 'image_uris' not in card:
        # prob double faced card
        card = card['card_faces'][0]

    image_url = card['image_uris']['normal']
    r = requests.get(image_url)
    with open('imgs/{}.jpg'.format(card_name), 'wb') as f:
        f.write(r.content)
    return card_name


# make a tkinter window
window = tk.Tk()
window.title('Battle of the Cents Lottery - {}'.format(next_player))
panel1 = tk.Label(window, image=None)
panel1.pack_forget()
panel2 = tk.Label(window, image=None)
panel2.pack_forget()


def tk_new_card(img1_name, img2_name=None):
    # get card image
    if img2_name is not None:
        # show both cards side by side, and auto resize tkinter window to fit both images
        img1 = Image.open('imgs/{}.jpg'.format(img1_name))
        img2 = Image.open('imgs/{}.jpg'.format(img2_name))
        # resize tkinter window to fit both images
        width = img1.width + img2.width
        height = max(img1.height, img2.height)
        window.geometry('{}x{}'.format(width, height))
        # show both images
        img1 = ImageTk.PhotoImage(img1)
        img2 = ImageTk.PhotoImage(img2)
        panel1.configure(image=img1)
        panel1.image = img1
        panel1.pack(side='left', fill='both', expand='yes')
        panel2.configure(image=img2)
        panel2.image = img2
        panel2.pack(side='right', fill='both', expand='yes')
    else:
        # show only one card and auto resize window to fit image
        img = Image.open('imgs/{}.jpg'.format(img1_name))
        width = img.width
        height = img.height
        window.geometry('{}x{}'.format(width, height))
        # show image
        img = ImageTk.PhotoImage(img)
        panel1.configure(image=img)
        panel1.image = img
        panel1.pack(side='left', fill='both', expand='yes')
        panel2.pack_forget()


def calculate_step_times(T, X, lambda_factor):
    """
    Calculate the time for each step in an animation with exponential slowdown.

    Parameters:
    T (float): Total duration of the animation in seconds.
    X (int): Total number of steps in the animation.
    lambda_factor (float): Factor that determines the rate of exponential growth.

    Returns:
    list: A list of time durations for each step.
    """
    step_times = [np.exp(lambda_factor * i) for i in range(1, X + 1)]
    total = sum(step_times)
    normalized_times = [T * (time / total) for time in step_times]

    return normalized_times


def tk_new_card_animation(cards=20, card_anim_time=4, jump_height=60, jump_time=0.1, veto_filter=lambda x: True):
    sequence = []
    sleep_times = calculate_step_times(card_anim_time, cards, 0.3)
    for i in range(cards):
        card, other_card = draw(veto_filter)
        # get images in advance
        img1 = get_img(card)
        img2 = None
        if other_card is not None:
            img2 = get_img(other_card)
        sequence.append((img1, img2))

    # show cards in sequence
    for indx, (img1_name, img2_name) in enumerate(sequence):
        tk_new_card(img1_name, img2_name)
        window.update()
        time.sleep(sleep_times[indx])
    # make window do a little jump
    x = window.winfo_x()
    y = window.winfo_y()
    for i in range(int(jump_time / 0.01)):
        window.geometry('+{}+{}'.format(x, int(y - jump_height * (i / (jump_time / 0.01)))))
        window.update()
        time.sleep(0.01)
    for i in range(int(jump_time / 0.01)):
        window.geometry('+{}+{}'.format(x, int(y - jump_height * (1 - i / (jump_time / 0.01)))))
        window.update()
        time.sleep(0.01)
    # set back to original position
    window.geometry('+{}+{}'.format(x, y))

    if other_card is None:
        card_name = card['name']
        if '//' in card_name:
            card_name = card_name.split('//')[0].strip()
        print('Drawn: {}'.format(card['name']))
        print('Decks: {}'.format(data['additional_data']['edhrec_dict'][card_name][0]['num_decks']))
        price = ScryfallCleanupStep().get_price(card)
        price = round(price, 2)
        print('Price: {}€'.format(price))
        pulled.append(card['name'])
    else:
        print('Drawn: {} and {}'.format(card['name'], other_card['name']))
        # try to find combi in edhrec_dict
        # try first with card name
        found = False
        for combi in data['additional_data']['edhrec_dict'][card['name']]:
            if 'cards' not in combi:
                continue
            if other_card['name'] in [x['name'] for x in combi['cards']]:
                print('Decks: {}'.format(combi['num_decks']))
                found = True
                break
        # try with other card name
        for combi in data['additional_data']['edhrec_dict'][other_card['name']]:
            if 'cards' not in combi:
                continue
            if card['name'] in [x['name'] for x in combi['cards']]:
                print('Decks: {}'.format(combi['num_decks']))
                found = True
                break
        if not found:
            print('Decks: 0')

        price1 = ScryfallCleanupStep().get_price(card)
        price2 = ScryfallCleanupStep().get_price(other_card)
        price1 = round(price1, 2)
        price2 = round(price2, 2)
        print('Price: {}€ and {}€'.format(price1, price2))
        pulled.append(card['name'])
        pulled.append(other_card['name'])
    print('-' * 70)
    # save pulled to file
    with open('files/pulled.json', 'w') as f:
        json.dump(pulled, f)
    return card, other_card


def ub_veto(card):
    sets = ['who', 'ltr', 'ltc', 'pip', '40k', 'bot']
    if card['set'].lower() in sets:
        return False
    return True


def combi_veto(*vetos):
    def combi(card):
        for veto in vetos:
            if not veto(card):
                return False
        return True

    return combi


current_card = None
current_other_card = None

def process(veto_filter, accept):
    global current_card
    global current_other_card

    if current_card is None:
        current_card, current_other_card = tk_new_card_animation(veto_filter=veto_filter)
        return

    if accept:
        global next_player
        # save current player to assignments
        if current_other_card is None:
            assignments[next_player] = (current_card['name'],)
        else:
            assignments[next_player] = (current_card['name'], current_other_card['name'])
        # save assignments to file
        with open('files/assignments.json', 'w') as f:
            json.dump(assignments, f)
        # next player
        next_player = None
        for player in players:
            if player not in assignments:
                next_player = player
                break
        if next_player is None:
            print('All players assigned')
            exit(0)
        # set title
        window.title('Battle of the Cents Lottery - {}'.format(next_player))
        # clear images
        panel1.image = None
        panel1.pack(side='left', fill='both', expand='yes')
        panel2.pack_forget()
        current_card = None
        current_other_card = None
        return

    # veto
    current_card, current_other_card = tk_new_card_animation(veto_filter=veto_filter)


# veto = combi_veto(ub_veto)
veto = lambda x: True

# accept, on space
window.bind('<space>', lambda event: process(veto, True))
# veto, on v
window.bind('v', lambda event: process(veto, False))
window.mainloop()

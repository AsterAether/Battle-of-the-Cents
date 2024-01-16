import json
import os
import time

import requests

from battle_of_the_cents import ProcessingStep, BotCChallenge


class ScryfallCleanupStep(ProcessingStep):

    def __init__(self, prices_to_check=None,
                 cutoff_money: float = 1,
                 usd_exchange_rate: float = 0.91):
        super().__init__()
        if prices_to_check is None:
            prices_to_check = ['eur', 'usd', 'eur_foil', 'usd_foil', 'usd_etched', 'eur_etched']
        self.prices_to_check = prices_to_check
        self.cutoff_money = cutoff_money
        self.usd_exchange_rate = usd_exchange_rate
        self.cleaned_baseline_file = 'files/cleaned_baseline.json'
        self.scryfall_baseline_file = 'files/scryfall.json'

    def get_price(self, card):
        lowest_price = float('inf')
        for price in self.prices_to_check:
            if price in card['prices'] and card['prices'][price] is not None:
                c_price = float(card['prices'][price])
                if 'usd' in price:
                    c_price *= self.usd_exchange_rate
                if c_price < lowest_price:
                    lowest_price = c_price
        if lowest_price == float('inf'):
            return None
        return lowest_price

    def load_baseline(self):
        if os.path.exists(self.scryfall_baseline_file):
            with open(self.scryfall_baseline_file, 'r') as f:
                cards = json.load(f)
                return cards

        usd_str = self.cutoff_money / self.usd_exchange_rate
        # format with 2 decimals
        search_string = 'is:commander (eur<={} or usd<={}) legal:commander unique:prints'.format(
            round(self.cutoff_money, 2), round(usd_str, 2))
        print(search_string)

        cards = []

        # get from scryfall
        r = requests.get('https://api.scryfall.com/cards/search', params={'q': search_string})

        # parse json
        data = json.loads(r.text)

        # get all cards
        cards += data['data']
        todo = data['total_cards'] // 175
        print('Need to do {} more requests'.format(todo))
        i = 0
        while data['has_more']:
            i += 1
            print('Request {} of {}'.format(i, todo))
            # wait for 500ms
            time.sleep(0.5)
            r = requests.get(data['next_page'])
            data = json.loads(r.text)
            cards += data['data']

        # save cards to json
        with open(self.scryfall_baseline_file, 'w') as f:
            json.dump(cards, f)
        return cards

    def process(self, botc: BotCChallenge):
        # load scryfall baseline
        baseline = self.load_baseline()

        print('STARTING PRUNING------------------------------------------------------------------------------')
        current_card = baseline[0]['name']
        card_added_or_skipped = False
        for card in baseline:
            if card['name'] != current_card:
                current_card = card['name']
                card_added_or_skipped = False

            if card_added_or_skipped:
                continue

            # if promo types is "thick" skip
            if 'promo_types' in card and 'thick' in card['promo_types']:
                print('Thick: {}'.format(card['name']))
                card_added_or_skipped = True
                continue

            # check if card price is under 1 euro
            price = self.get_price(card)
            if price is None or price > self.cutoff_money:
                print('Not cheap: {}'.format(card['name']))
                card_added_or_skipped = True
                continue

            # add card to list
            botc.card_pool.append(card)
            card_added_or_skipped = True

        print('FINISHED PRUNING------------------------------------------------------------------------------')

        print('Found {}'.format(len(botc.card_pool)))

        # save cleaned baseline
        with open(self.cleaned_baseline_file, 'w') as f:
            json.dump(botc.card_pool, f, indent=4)

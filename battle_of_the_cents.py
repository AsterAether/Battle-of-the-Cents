import json
import os
import time
from abc import abstractmethod

import requests


class BotCChallenge:

    def __init__(self):
        self.additional_data = {}
        self.card_pool = []
        self.edhrec_baseline_file = 'files/edhrec.json'
        self.all_printings_file = 'files/all_printings.json'
        self.botc_challenge_file = 'files/botc_challenge.json'

    def apply_step(self, step: 'ProcessingStep'):
        print('Applying step: {}'.format(step.__class__.__name__))
        step.process(self)
        print('Done applying step: {}'.format(step.__class__.__name__))

    def load_all_baseline(self):
        if os.path.exists(self.all_printings_file):
            with open(self.all_printings_file, 'r') as f:
                cards = json.load(f)
                return cards

        search_string = 'is:commander legal:commander unique:prints sort:name'

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
        with open(self.all_printings_file, 'w') as f:
            json.dump(cards, f)
        return cards

    def load_edhrec_baseline(self):
        if os.path.exists(self.edhrec_baseline_file):
            with open(self.edhrec_baseline_file, 'r') as f:
                data = json.load(f)
                return data
        endpoint = 'https://json.edhrec.com/pages/commanders/year.json'
        r = requests.get(endpoint)
        cards = json.loads(r.text)['cardlist']

        # write to file
        with open(self.edhrec_baseline_file, 'w') as f:
            json.dump(cards, f)
        return cards

    def save_data(self):
        copy_additional_data = self.additional_data.copy()
        # remove some keys

        all_data = {
            'card_pool': self.card_pool,
            'additional_data': copy_additional_data
        }
        # pretty print
        with open(self.botc_challenge_file, 'w') as f:
            json.dump(all_data, f, indent=4)


# Represents a single step in the processing pipeline
class ProcessingStep:
    @abstractmethod
    def process(self, botc: BotCChallenge):
        pass


if __name__ == '__main__':
    from steps.commander_year_extractor import YearExtractorStep
    from steps.multi_commander_filtering import MultiCommanderStep
    from steps.scryfall_cleanup_and_price_filter import ScryfallCleanupStep
    from steps.edhrec_filter import EDHRECStep
    from steps.manual_filter import ManualFilter

    mc_step = MultiCommanderStep()

    botc = BotCChallenge()
    botc.apply_step(ScryfallCleanupStep(cutoff_money=0.49))
    # Remove faceless one and prismatic piper
    to_remove = [
        'Faceless One',
        'The Prismatic Piper'
    ]
    botc.apply_step(ManualFilter(lambda card: card['name'] in to_remove))
    # Remove vanilla legends that do not have a good mana to power ratio
    botc.apply_step(
        ManualFilter(lambda card: 'oracle_text' in card and card['oracle_text'] == "" and float(card['power']) <= card['cmc']))
    botc.apply_step(YearExtractorStep())
    botc.apply_step(mc_step)
    botc.apply_step(EDHRECStep(cutoff_decks=1500))
    mc_step.cleanup = False
    # have to rerun this step because of cleanup
    botc.apply_step(mc_step)
    botc.save_data()

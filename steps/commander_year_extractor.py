import json
import os
from datetime import datetime

from battle_of_the_cents import ProcessingStep, BotCChallenge


class YearExtractorStep(ProcessingStep):

    def __init__(self):
        super().__init__()
        self.years_file = 'files/years.json'

    def process(self, botc: BotCChallenge):

        # if file exists, load it
        if os.path.exists(self.years_file):
            with open(self.years_file, 'r') as f:
                years = json.load(f)
                botc.additional_data['years'] = years
                return

        all_prints = botc.load_all_baseline()
        years = {}
        current_card = all_prints[0]['name']
        # format is YYYY-MM-DD, convert to date object
        lowest_date = datetime.strptime(all_prints[0]['released_at'], '%Y-%m-%d')
        for card in all_prints:
            if current_card != card['name']:
                # new card, add to years (tostring)
                years[current_card] = lowest_date.strftime('%Y-%m-%d')
                lowest_date = datetime.strptime(card['released_at'], '%Y-%m-%d')
                current_card = card['name']

            # check if card is older than lowest_date
            card_date = datetime.strptime(card['released_at'], '%Y-%m-%d')
            if card_date < lowest_date:
                lowest_date = card_date

        # last card
        years[current_card] = lowest_date.strftime('%Y-%m-%d')

        with open(self.years_file, 'w') as f:
            json.dump(years, f)

        botc.additional_data['years'] = years

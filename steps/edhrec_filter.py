import collections
import json
import os
import time

from battle_of_the_cents import ProcessingStep, BotCChallenge


class EDHRECStep(ProcessingStep):

    def __init__(self, cutoff_decks: int = 2000,
                 year_diff: int = 5,
                 year_multiplier: float = 0.1):
        super().__init__()
        self.cutoff_decks = cutoff_decks
        self.year_diff = year_diff
        self.year_multiplier = year_multiplier
        self.edhrec_dict_file = 'files/edhrec_dict.json'

    def edhrec_preprocess(self, botc: BotCChallenge):
        if os.path.exists(self.edhrec_dict_file):
            with open(self.edhrec_dict_file, 'r') as f:
                edhrec_dict = json.load(f)
                botc.additional_data['edhrec_dict'] = edhrec_dict
                return

        edhrec = botc.load_edhrec_baseline()
        edhrec_dict = {}

        # go through card pool
        for card in botc.card_pool:
            name = card['name']
            # if // in name, remove everything after it
            if '//' in name:
                name = name.split('//')[0].strip()
            # go through edhrec and find each card (there can be multiple because of multiple commanders)
            edhrec_dict[name] = []
            for edh_card in edhrec:
                if edh_card['name'] == name:
                    edhrec_dict[name].append(edh_card)

        botc.additional_data['edhrec_dict'] = edhrec_dict

        with open(self.edhrec_dict_file, 'w') as f:
            json.dump(edhrec_dict, f)

    def check_threshold(self, botc, card, edh_card):
        multiplier_cut = False
        multiplier = 1
        # released_at extract, everything over 5 years old is fine, everything before gets a multiplier
        # get current year, and subtract release year
        # format is YYYY-MM-DD
        if 'released_at' in card:
            release_year = int(botc.additional_data['years'][card['name']].split('-')[0])
            current_year = int(time.strftime('%Y'))
            years_old = current_year - release_year
            if years_old < self.year_diff:
                multiplier = (self.year_diff - years_old) * self.year_multiplier + 1

        if edh_card['num_decks'] * multiplier > self.cutoff_decks:
            if multiplier != 1:
                # check if multiplier would change outcome
                if edh_card['num_decks'] > self.cutoff_decks:
                    print('Too many decks: {}'.format(card['name']))
                else:
                    print(
                        'Too many decks: {}, multiplier: {}, original: {}'.format(card['name'], multiplier,
                                                                                  edh_card['num_decks']))
                    multiplier_cut = True
            else:
                print('Too many decks: {}'.format(card['name']))
            return True, multiplier_cut, multiplier
        return False, multiplier_cut, multiplier

    def process(self, botc: BotCChallenge):
        self.edhrec_preprocess(botc)
        to_remove = []
        multiplier_cuts = []

        botc.additional_data['partner_illegal_pool'] = collections.defaultdict(list)
        botc.additional_data['friends_forever_illegal_pool'] = collections.defaultdict(list)
        botc.additional_data['background_illegal_pool'] = collections.defaultdict(list)
        botc.additional_data['doctor_illegal_pool'] = collections.defaultdict(list)

        print('EDHREC----------------------------------------------------------------------------------------')
        for index, card in enumerate(botc.card_pool):
            name = card['name']
            # if // in name, remove everything after it
            if '//' in name:
                name = name.split('//')[0].strip()
            if name not in botc.additional_data['edhrec_dict']:
                print('Not found in EDHREC, not removing: {}'.format(name))
                continue

            # if index is in multi-commander card indexes, skip
            if index in botc.additional_data['multi_commander_card_indexes']:
                # if you are already cut, skip
                if index in to_remove:
                    continue

                # print how many pairs it has
                print('Multi commander: {}, pairs: {}'.format(card['name'],
                                                              len(botc.additional_data['edhrec_dict'][name])))
                # if no pairs, skip
                if len(botc.additional_data['edhrec_dict'][name]) == 0:
                    continue

                # find entry with no 'cards'
                found = False
                own_entry = None
                for edh_card in botc.additional_data['edhrec_dict'][name]:
                    if 'cards' not in edh_card:
                        found = True
                        own_entry = edh_card
                        break

                if found:
                    # this is the entry with only this card without partners, check
                    cut, m_cut, multiplier = self.check_threshold(botc, card, own_entry)
                    if cut:
                        # not really cutting it, just for info
                        print('Cutting single: {}'.format(card['name']))

                categories = botc.additional_data['multi_commander_card_indexes_reverse'][index]
                # partner with check
                if 'partner_with_card_indexes' in categories:
                    # get pairing with 'cards' (there only is one)
                    for edh_card in botc.additional_data['edhrec_dict'][name]:
                        if 'cards' in edh_card:
                            cut, m_cut, multiplier = self.check_threshold(botc, card, edh_card)
                            if cut:
                                print('Cutting partner with: {}'.format(card['name']))
                                to_remove.append(index)
                                # also remove partner
                                # get partner name
                                card_names = edh_card['cards']
                                partner_name = None
                                for e_card in card_names:
                                    if e_card['name'] != name:
                                        partner_name = e_card['name']
                                        break
                                # get partner index
                                partner_index = None
                                for i in botc.additional_data['partner_with_card_indexes']:
                                    o_card = botc.card_pool[i]
                                    if o_card['name'] == partner_name:
                                        partner_index = i
                                        break
                                # remove partner
                                if partner_index is not None:
                                    to_remove.append(partner_index)
                                else:
                                    raise Exception('Partner index not found')
                                print('Cutting partner of partner with: {}'.format(partner_name))
                                break

                # partner check
                def n_n_check(index_list_name, pool_name):
                    if index_list_name in categories:
                        # get pairing with 'cards'
                        for edh_card in botc.additional_data['edhrec_dict'][name]:
                            if 'cards' in edh_card:
                                card_names = [e_card['name'] for e_card in edh_card['cards']]
                                # remove own name
                                card_names.remove(name)
                                other_partner = card_names[0]

                                # if pair is already cut, skip, only need to check other partner
                                if card['name'] in botc.additional_data[pool_name + '_illegal_pool'][other_partner]:
                                    print('Skipping already cut pair: {}, {}'.format(card['name'], other_partner))
                                    continue

                                # check if other partner is in card pool
                                partner_in_pool = False
                                for index in botc.additional_data[index_list_name]:
                                    p_card = botc.card_pool[index]
                                    if p_card['name'] == other_partner:
                                        partner_in_pool = True
                                        break
                                if not partner_in_pool:
                                    # skip this pairing
                                    continue

                                cut, m_cut, multiplier = self.check_threshold(botc, card, edh_card)
                                if cut:
                                    botc.additional_data[pool_name + '_illegal_pool'][card['name']].append(other_partner)
                                    # also add to partner pool
                                    botc.additional_data[pool_name + '_illegal_pool'][other_partner].append(card['name'])
                                    print('Cutting {} combi: {}, {}'.format(pool_name, card['name'], other_partner))

                n_n_check('partner_card_indexes', 'partner')
                # friends forever check
                n_n_check('friends_forever_card_indexes', 'friends_forever')

                # same as above, but main_index can only be paired with sub_index, not itself and not the other way around
                def m_n_check(main_index_name, sub_index_name, pool_name):
                    if main_index_name in categories:
                        # get pairing with 'cards'
                        for edh_card in botc.additional_data['edhrec_dict'][name]:
                            if 'cards' in edh_card:
                                card_names = [e_card['name'] for e_card in edh_card['cards']]
                                # remove own name
                                card_names.remove(name)
                                other_partner = card_names[0]

                                # check if other partner is in card pool
                                partner_in_pool = False
                                for index in botc.additional_data[sub_index_name]:
                                    p_card = botc.card_pool[index]
                                    if p_card['name'] == other_partner:
                                        partner_in_pool = True
                                        break
                                if not partner_in_pool:
                                    # skip this pairing
                                    continue

                                cut, m_cut, multiplier = self.check_threshold(botc, card, edh_card)
                                if cut:
                                    botc.additional_data[pool_name + '_illegal_pool'][card['name']].append(other_partner)
                                    # also add to partner pool
                                    botc.additional_data[pool_name + '_illegal_pool'][other_partner].append(card['name'])
                                    print('Cutting {} combi: {}, {}'.format(pool_name, card['name'], other_partner))

                m_n_check('choose_a_background_card_indexes', 'background_card_indexes', 'background')
                m_n_check('doctor_card_indexes', 'doctor_companion_card_indexes', 'doctor')

                # continue to not run normal check
                continue

            for edh_card in botc.additional_data['edhrec_dict'][name]:
                cut, m_cut, multiplier = self.check_threshold(botc, card, edh_card)
                if m_cut:
                    multiplier_cuts.append((card['name'], multiplier, edh_card['num_decks']))
                if cut:
                    to_remove.append(index)
                    break
        print('MULTIPLIER CUT---------------------------------------------------------------------------------')
        for name, multiplier, original in multiplier_cuts:
            print('{}: {}, {}'.format(name, multiplier, original))

        print('Found {} cards to remove'.format(len(to_remove)))
        # remove cards from card pool
        botc.card_pool = [card for index, card in enumerate(botc.card_pool) if index not in to_remove]
        print('Found {} cards left'.format(len(botc.card_pool)))
        print('------------------------------------------------------------------------------------------------')

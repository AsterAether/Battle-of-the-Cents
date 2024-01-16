from battle_of_the_cents import ProcessingStep, BotCChallenge


class MultiCommanderStep(ProcessingStep):

    def __init__(self, cleanup: bool = True):
        super().__init__()
        self.cleanup = cleanup

    def __process(self, botc: BotCChallenge, output=print):
        # special cases: partner, partner with, doctor and doctor's companion, friends forever, backgrounds
        # partner
        partner_card_indexes = []
        # partner with cards
        partner_with_card_indexes = []
        # background cards
        background_card_indexes = []
        choose_a_background_card_indexes = []
        # doctor and doctor's companion
        doctor_card_indexes = []
        doctor_companion_card_indexes = []
        # friends forever
        friends_forever_card_indexes = []

        to_remove = []

        for i, card in enumerate(botc.card_pool):
            # if no oracle text, probably double sided, skip
            if 'oracle_text' not in card:
                continue
            if 'partner' in card['oracle_text'].lower() and not ('partner with' in card['oracle_text'].lower()):
                partner_card_indexes.append(i)
            if 'partner with' in card['oracle_text'].lower():
                partner_with_card_indexes.append(i)
            if 'background' in card['type_line'].lower():
                background_card_indexes.append(i)
            if 'choose a background' in card['oracle_text'].lower():
                choose_a_background_card_indexes.append(i)
            # doctor is in typeline
            if 'doctor' in card['type_line'].lower():
                doctor_card_indexes.append(i)
            # doctor's companion is in oracle text
            if 'doctor\'s companion' in card['oracle_text'].lower():
                doctor_companion_card_indexes.append(i)
            # friends forever in oracle text
            if 'friends forever' in card['oracle_text'].lower():
                friends_forever_card_indexes.append(i)

        output('PARTNER----------------------------------------------------------------------------------------')
        output('Found {} partner cards'.format(len(partner_card_indexes)))
        # possible combinations (every cards can be a partner with every other card but itself)
        # n * (n - 1)
        output('Possible combinations: {}'.format(len(partner_card_indexes) * (len(partner_card_indexes) - 1)))

        # partner with processing
        output('PARTNER WITH-----------------------------------------------------------------------------------')
        output('Found {} partner with cards'.format(len(partner_with_card_indexes)))
        output('Now outputing partner with cards that do not have a partner with card')
        botc.additional_data['partner_with_card_other_indexes'] = {}
        for i in partner_with_card_indexes:
            card = botc.card_pool[i]
            # get partner with name
            partner_with_name = card['oracle_text'].lower().split('partner with ')[1]
            # parse until you hit either a newline or ' ('
            partner_with_name = partner_with_name.split('\n')[0]
            partner_with_name = partner_with_name.split(' (')[0]

            found = False
            for other_idx, other_card in enumerate(botc.card_pool):
                if other_card['name'].lower() == partner_with_name:
                    found = True
                    botc.additional_data['partner_with_card_other_indexes'][i] = other_idx
                    break
            if not found:
                output('{}'.format(card['name']))
                to_remove.append(i)

        output('BACKGROUND-------------------------------------------------------------------------------------')
        output('Found {} background cards'.format(len(background_card_indexes)))
        output('Found {} choose a background cards'.format(len(choose_a_background_card_indexes)))
        # possible combinations (every choose a background card can be a partner with background cards)
        # n * m
        output('Possible combinations: {}'.format(len(choose_a_background_card_indexes) * len(background_card_indexes)))

        output('DOCTOR-----------------------------------------------------------------------------------------')
        output('Found {} doctor cards'.format(len(doctor_card_indexes)))
        output('Found {} doctor\'s companion cards'.format(len(doctor_companion_card_indexes)))
        # possible combinations (every doctor card can be a partner with doctor's companion cards)
        # n * m
        output('Possible combinations: {}'.format(len(doctor_card_indexes) * len(doctor_companion_card_indexes)))

        output('FRIENDS FOREVER--------------------------------------------------------------------------------')
        output('Found {} friends forever cards'.format(len(friends_forever_card_indexes)))
        # possible combinations (every cards can be a partner with every other card but itself)
        # n * (n - 1)
        output('Possible combinations: {}'.format(len(friends_forever_card_indexes) * (
                len(friends_forever_card_indexes) - 1)))
        # print all names
        for i in friends_forever_card_indexes:
            output('{}'.format(botc.card_pool[i]['name']))

        # add to additional data
        botc.additional_data['partner_card_indexes'] = partner_card_indexes
        botc.additional_data['partner_with_card_indexes'] = partner_with_card_indexes
        botc.additional_data['background_card_indexes'] = background_card_indexes
        botc.additional_data['choose_a_background_card_indexes'] = choose_a_background_card_indexes
        botc.additional_data['doctor_card_indexes'] = doctor_card_indexes
        botc.additional_data['doctor_companion_card_indexes'] = doctor_companion_card_indexes
        botc.additional_data['friends_forever_card_indexes'] = friends_forever_card_indexes
        botc.additional_data[
            'multi_commander_card_indexes'] = partner_card_indexes + partner_with_card_indexes + background_card_indexes + choose_a_background_card_indexes + doctor_card_indexes + doctor_companion_card_indexes + friends_forever_card_indexes
        botc.additional_data['multi_commander_card_data_categories'] = ['partner_card_indexes',
                                                                       'partner_with_card_indexes',
                                                                       'background_card_indexes',
                                                                       'choose_a_background_card_indexes',
                                                                       'doctor_card_indexes',
                                                                       'doctor_companion_card_indexes',
                                                                       'friends_forever_card_indexes']
        # also add reverse index search, index can be in multiple categories
        botc.additional_data['multi_commander_card_indexes_reverse'] = {}
        for i, index_list_name in enumerate(botc.additional_data['multi_commander_card_data_categories']):
            for index in botc.additional_data[index_list_name]:
                if index not in botc.additional_data['multi_commander_card_indexes_reverse']:
                    botc.additional_data['multi_commander_card_indexes_reverse'][index] = []
                botc.additional_data['multi_commander_card_indexes_reverse'][index].append(index_list_name)
        return to_remove

    def process(self, botc: BotCChallenge):
        to_remove = self.__process(botc, output=print if self.cleanup else lambda x: None)
        if self.cleanup:
            # remove cards from card pool
            for i in sorted(to_remove, reverse=True):
                del botc.card_pool[i]
            print('Removed {} cards'.format(len(to_remove)))
            print('New card pool size: {}'.format(len(botc.card_pool)))
            # have to reprocess because of indexes
            print('Reprocessing')
            self.__process(botc, output=lambda x: None)

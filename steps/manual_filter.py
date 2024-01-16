from battle_of_the_cents import ProcessingStep


class ManualFilter(ProcessingStep):

    def __init__(self, lambda_filter: callable):
        super().__init__()
        # list of card names to remove
        self.lambda_filter = lambda_filter

    def process(self, botc):
        to_remove = []
        for i, card in enumerate(botc.card_pool):
            # fuzzy name matching
            if self.lambda_filter(card):
                to_remove.append(i)

        for index in to_remove[::-1]:
            del botc.card_pool[index]
        print('Removed {} cards'.format(len(to_remove)))
        print('Left with {} cards'.format(len(botc.card_pool)))

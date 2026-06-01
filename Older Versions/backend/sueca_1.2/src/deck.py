from src.constants import *
import random
from src.card_mapper import CardMapper


class Deck:
    """This class represents a deck, which holds 40 cards from 4 different suits, each card is a number between 0-39. """
    def __init__(self):
        self.NUM_SUITS = 4
        self.SUITSIZE = 10
        self.cards = list(range(self.DECKSIZE))

    @property
    def DECKSIZE(self):
        return self.NUM_SUITS * self.SUITSIZE

    def __str__(self):
        deck_str = ""
        for i in range(0, len(self.cards), 10):
            line_of_cards = []
            for card_id in self.cards[i : i + 10]:
                rank = CardMapper.get_card_rank(card_id)
                suit = CardMapper.get_card_suit(card_id)
                card_representation = f"{rank}{suit}"
                line_of_cards.append(card_representation)
            deck_str += "     ".join(line_of_cards) + "\n"
        return deck_str.strip()

    def shuffle_deck(self, intensity="Normal"):
        """Shuffles deck given an intensity which can be small,normal or high. """
        random_variable = random.randint(0, 2)
        if intensity == "Small":
            times_shuffle = 1 + random_variable
        elif intensity == "Normal":
            times_shuffle = 4 + random_variable
        elif intensity == "High":
            times_shuffle = 7 + random_variable
        while times_shuffle != 0:
            random.shuffle(self.cards)
            times_shuffle -= 1

    def cut_deck(self, index):
        """Cuts the deck at a given index, prone to small intentional deviations. """
        if 35 > index > 5:
            random_variable = random.randint(-5, 5)
        elif 40 >= index >= 35:
            random_variable = random.randint(-5, 40 - index)
        elif 0 < index <= 5:
            random_variable = random.randint(1 - index, 5)
        index += random_variable
        if 0 < index <= 40:
            top = self.cards[:index]
            bottom = self.cards[index:]
            self.cards = bottom + top

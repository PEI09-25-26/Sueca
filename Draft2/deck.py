from card import *
from constants import *
import random

class Deck:
    def __init__(self):
        self.pile = [Card(rank,suit) for suit in suits for rank in ranks_map]

    def __str__(self):
        deck_str = ''
        for i in range(0, len(self.pile), 10):
            if i == 9:
                deck_str += '     '.join(str(card) for card in self.pile[i:i+10])
            else:
                deck_str += '     '.join(str(card) for card in self.pile[i:i+10]) + '\n'
        return deck_str
    

    def shuffle_deck(self):
        random.shuffle(self.pile)
        


    def cut_deck(self,index):
        if 0 < index <= 40:
            top = self.pile[:index]
            bottom = self.pile[index:]
            self.pile = bottom + top        
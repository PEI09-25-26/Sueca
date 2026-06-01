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
    

    def shuffle_deck(self, intensity="Normal"):
        random_variable = random.randint(0, 2)
        if intensity == "Small":
            times_shuffle = 1 + random_variable
        elif intensity == "Normal":
            times_shuffle = 4 + random_variable
        elif intensity == "High":
            times_shuffle = 7 + random_variable
        while times_shuffle != 0:
            random.shuffle(self.pile)
            times_shuffle -= 1
        


    def cut_deck(self,index):
        if 35 > index > 5:
            random_variable = random.randint(-5, 5)
        elif 40 >= index >= 35 :
            random_variable = random.randint(-5, 40-index)
        elif 0 < index <= 5:
            random_variable = random.randint(1-index, 5)
        index += random_variable
        if 0 < index <= 40:
            top = self.pile[:index]
            bottom = self.pile[index:]
            self.pile = bottom + top        
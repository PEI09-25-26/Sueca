from card import *
from constants import *
import random

class Deck:
    def __init__(self):
        self.pile = [Card(rank,suit) for suit in suits for rank in ranks_map]

    def __str__(self):
        deck_str = ''
        for i in range(0, len(self.pile), 10):
            deck_str += '  '.join(str(card) for card in self.pile[i:i+10]) + '\n'
        
        return deck_str
    

    def shuffle_deck(self):
        print(f"Shuffling deck...")
        random.shuffle(self.pile)
        print(f"Deck has been shuffled.")


    def cut_deck(self):
        print("Deck before the cut:")
        print(str(self))

        while True:
            try:
                index = int(input("Cut from what index:").strip())
                if 0 < index <= 40:
                    top = self.pile[:index]
                    bottom = self.pile[index:]
                    break
                print(f"Invalid cut index, pick in a range of (1,40)")
            except ValueError:
                raise ValueError("Input Text is not permitted.")
        self.pile = bottom + top
        print("Deck after the cut:")
        print(str(self))
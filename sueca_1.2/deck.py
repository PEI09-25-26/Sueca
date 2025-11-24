from constants import *
import random

class Deck:
    def __init__(self):
        self.points = [0,0,0,0,0,2,3,4,10,11,
                0,0,0,0,0,2,3,4,10,11,
                0,0,0,0,0,2,3,4,10,11,
                0,0,0,0,0,2,3,4,10,11]
        
        self.pile = [
            "♣|2", "♣|3", "♣|4", "♣|5", "♣|6", "♣|Q", "♣|J", "♣|K", "♣|7", "♣|A",
            "♦|2", "♦|3", "♦|4", "♦|5", "♦|6", "♦|Q", "♦|J", "♦|K", "♦|7", "♦|A",
            "♥|2", "♥|3", "♥|4", "♥|5", "♥|6", "♥|Q", "♥|J", "♥|K", "♥|7", "♥|A",
            "♠|2", "♠|3", "♠|4", "♠|5", "♠|6", "♠|Q", "♠|J", "♠|K", "♠|7", "♠|A"
        ]

    def __repr__(self):
        combined_str = ''
        card_width = 4
        for i in range(0, len(self.pile), 10):
            cards_row = self.pile[i:i+10]
            points_row = self.points[i:i+10]

            points_line = ' '.join(f"{p:>{card_width}}" for p in points_row)
            cards_line = ' '.join(f"{c:>{card_width}}" for c in cards_row)

            combined_str += points_line + "\n" + cards_line + "\n"
        return combined_str

    
    def __str__(self):
        deck_str = ''
        for i in range(0, len(self.pile), 10):
            row = '  '.join(f"{card:>2}" for card in self.pile[i:i+10])
            deck_str += row + ("\n" if i + 10 < len(self.pile) else "")
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

        card_point_pairs = list(zip(self.pile,self.points))
        
        while times_shuffle!=0:
            random.shuffle(card_point_pairs) 
            times_shuffle -= 1
        self.pile,self.points = zip(*card_point_pairs)
        self.pile = list(self.pile)
        self.points = list(self.points)
        
    def cut_deck(self,index):
        if 35 > index > 5:
            random_variable = random.randint(-5, 5)
        elif 40 >= index >= 35 :
            random_variable = random.randint(-5, 40-index)
        elif 0 < index <= 5:
            random_variable = random.randint(1-index, 5)
        index += random_variable
        if 0 < index <= 40:
            top_pile = self.pile[:index]
            bottom_pile = self.pile[index:]
            top_points = self.points[:index]
            bottom_points = self.points[index:]
            self.pile = bottom_pile + top_pile
            self.points = bottom_points + top_points 
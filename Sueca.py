import random

ranks_map = {
        "A":11,
        "7":10,
        "K":4,
        "J":3,
        "Q":2,
        "2":0,
        "3":0,
        "4":0,
        "5":0,
        "6":0
    }

suits = ["H","D","C","S"]

MAX_CARDS = 40

class Card:
    def __init__(self,rank,suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}|{self.suit}"
    

class Deck:
    def __init__(self):
        self.pile = [Card(rank,suit) for suit in suits for rank in ranks_map]


    def _shuffle_deck(self):
        """Shuffles the deck do later by beep bop man but for now be skellington of shufflings"""
        random.shuffle(self.pile)


    def __str__(self):
        return "\n".join(str(card) for card in self.pile)
    
    def _cut_deck(self):
        """Cuts deck also made by beep bop man"""
    
class Game:

    def __init__(self,player_names):
        self.deck = Deck()
        self.players = [Player(name, i + 1) for i, name in enumerate(player_names)]
                
    def __str__(self):
        deck_str = ''
        for i in range(0, len(self.deck.pile), 10):
            deck_str += '  '.join(str(card) for card in self.deck.pile[i:i+10]) + '\n'
        
        players_str = ''
        for i in range(0,len(self.players),2):
            players_str += ' '.join(str(player) for player in self.players[i:i+2]) + "\n"
        return (
            f"Deck =>\n{deck_str}\n"
            f"Players =>\n{players_str}\n"
        )
    
    def _distribute_cards(self):
        for i in range(10):
            pass

class Player:
    def __init__(self,name,player_count):
        self.name = name
        self.hand = []
        self.player_count = player_count

    def receive_cards(self,set_of_cards):
        self.hand = set_of_cards

    def play_card(self,card):
        """Plays card when on their turn"""
        self.hand.pop(card)
        print(self.hand)

    def cut(self):
        """Can cut plays made by other players"""

    def __repr__(self):
        return f"Player {self.player_count} == {self.name}"
    
def main():
    game = Game(["Pedro","Tiago","Lucas","Gonçalo"])
    game.deck._shuffle_deck()
    print(game) 

main()
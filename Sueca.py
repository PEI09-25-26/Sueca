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

# suits = ["H","D","C","S"] - save for later if needed
"""suits = {
    "Spades": "♠️",
    "Hearts": "♥️",        - Can also use this save for later
    "Diamonds": "♦️",
    "Clubs": "♣️"
}"""

suits = ["♥️","♦️","♣️","♠️"]

MAX_CARDS = 40      # Probably not needed

class Card:
    def __init__(self,rank,suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}|{self.suit}"
    

class Deck:
    def __init__(self):
        self.pile = [Card(rank,suit) for suit in suits for rank in ranks_map]

    def __str__(self):
        deck_str = ''
        for i in range(0, len(self.pile), 10):
            deck_str += '  '.join(str(card) for card in self.pile[i:i+10]) + '\n'
        
        return deck_str
    
  
class Game:

    def __init__(self,player_names):
        self.deck = Deck()
        self.players = [Player(name, i + 1) for i, name in enumerate(player_names)]
                
    # def __str__(self):
    #     players_str = ''
    #     for i in range(0,len(self.players),2):
    #         players_str += ' '.join(str(player) for player in self.players[i:i+2]) + "\n" - Might not need
    #     return (
    #         f"Deck =>\n{self.deck}\n"
    #         f"Players =>\n{players_str}\n"
    #     )
    
    def _shuffle_deck(self):
        """Shuffles the deck do later by beep bop man but for now there be random skeleton """
        random.shuffle(self.deck.pile)

    def _cut_deck(self):
        """Cuts deck also made by beep bop man"""
    
    def _distribute_cards(self):     # Can only be done after shuffling
        for player in self.players:
            set_cards=[]
            for i in range(10):
                card = self.deck.pile.pop()  
                set_cards.append(card)
            player.receive_cards(set_cards)
    
    def _round(self):
        round_vector = []
        for player in self.players:
            print(f"It's Player {player.player_id}'s turn:")

    def _show_deck(self):
        return str(self.deck)

    def _show_players(self):
        return str(self.players)

class Player:
    def __init__(self,name,player_id):
        self.name = name
        self.hand = []
        self.player_id = player_id

    def receive_cards(self,set_of_cards):
        self.hand = set_of_cards

    def play_card(self,card):
        """Plays card when on their turn. Can be either a cut or a normal play fix later"""
        self._view_hand()
        choice = input("Choice?") # Still WIP

        self.hand.pop(card)

    def cut(self):
        """Can cut plays made by other players might not be necessary, look above fix later"""

    def __repr__(self):
        return f"Player {self.player_id} == {self.name}"
    
    def _view_hand(self):
        print(f"Hand of Player {self.player_id} =>")
        hand_str = ' '.join(str(card) for card in self.hand)  
        print(hand_str)

def main():
    game = Game(["Pedro","Tiago","Lucas","Gonçalo"])
    print(game._show_deck())
    print(game._show_players())
    game._shuffle_deck()              # People can spectate the game, having access to all of the hands and plays record list, like each round's vector
    game._distribute_cards()
    for player in game.players:
        player._view_hand()           # Each player plays on their own terminal maybe? I don't know how to do that ):. And they can do stuff like view_cards, peek aside and cheat :)(with a very low chance of working) whenever they wish to

main()
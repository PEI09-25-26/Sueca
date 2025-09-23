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

# # suits = ["H","D","C","S"] - save for later if needed
# """suits = {
#     "Spades": "♠️",
#     "Hearts": "♥️",        - Can also use this save for later
#     "Diamonds": "♦️",
#     "Clubs": "♣️"
# }"""

suits = ["♥️","♦️","♣️","♠️"]

MAX_CARDS = 40      # Probably not needed

class Card:
    def __init__(self,rank,suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}|{self.suit}"
    
class NullCard(Card):
    def __init__(self, rank, suit):
        super().__init__(rank, suit)
    def __str__(self):
        return f"Null|Card"
    
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
        self._cut_deck()
        self._shuffle_deck()
        self.trump_card = self._get_trump_card()
        self.trump_suit = self.trump_card.suit
        self.players = [Player(name, i + 1) for i, name in enumerate(player_names)]
        self._distribute_cards()
        self.round_vector_history = []
        self.players_and_scores ={self.players[0]:0,
                                self.players[2]:0,
                                self.players[1]:0,
                                self.players[3]:0}
        self.round_counter = 1
        self.teams = [[self.players[0],self.players[2]],[self.players[1],self.players[3]]]
    # def __str__(self):
    #     players_str = ''
    #     for i in range(0,len(self.players),2):
    #         players_str += ' '.join(str(player) for player in self.players[i:i+2]) + "\n" - Might not need
    #     return (
    #         f"Deck =>\n{self.deck}\n"
    #         f"Players =>\n{players_str}\n"
    #     )
    def _get_trump_card(self):
        answer = input("Take trump_card from top or bottom?: ").strip().lower()
        if answer=="top":
            trump_card = self.deck.pile[0]
        else:
            trump_card = self.deck.pile[-1]
        self.trump_card = trump_card
        return trump_card

    def _shuffle_deck(self):
        """Shuffles the deck do later by beep bop man but for now there be random skeleton """
        random.shuffle(self.deck.pile)

    def _cut_deck(self):
        print("Deck before the cut:")
        print(self._show_deck())

        index = int(input("Cut from what index:").strip())
        top = self.deck.pile[:index]
        bottom = self.deck.pile[index:]
        self.deck.pile = bottom + top

        print("Deck after the cut:")
        print(self._show_deck())

    def _distribute_cards(self):     # Can only be done after shuffling needs to be 10 to right etc
        for player in self.players:
            set_cards=[]    
            for i in range(10):
                card = self.deck.pile.pop(0)  
                set_cards.append(card)
            player.receive_cards(set_cards)
    
    def _round(self):
        print(f"========================================")
        print(f"Round {self.round_counter}")
        round_vector = []
        for player in self.players:
            print(f"It's Player {player.player_id}'s turn:")
            print(player._view_hand())
            round_vector.append(player.play_card())
        print("\nCards played this round:")
        for i, card in enumerate(round_vector, start=1):
            print(f"Player {self.players[i-1].player_id} played: {card}")

        self.round_vector_history.append(round_vector)

        def _determine_round_winner():
            trump_was_played = any(card.suit == self.trump_suit for card in round_vector)

            
            if trump_was_played:
                trump_cards = [card for card in round_vector if card.suit == self.trump_suit]
                winner = max(trump_cards,key=lambda card: ranks_map[card.rank])
                winner_index = round_vector.index(winner)
                return winner,winner_index
            
            winner = max(round_vector,key=lambda card: ranks_map[card.rank])
            winner_index = round_vector.index(winner)
            return winner,winner_index

        round_winner, winner_index = _determine_round_winner()
        winner_player = self.players[winner_index]  # map index to player

        def _get_round_sum():
            round_sum = 0
            for card in round_vector:
                round_sum+=ranks_map[card.rank]
            return round_sum

        print(f"Round winner was {round_winner},  Player {winner_player.player_id} ({winner_player.name}) wins {_get_round_sum()} points.")

        # Update score
        self.players_and_scores[winner_player] += _get_round_sum()

        self.round_counter+=1

    def _show_deck(self):
        return str(self.deck)

    def _show_players(self):
        return str(self.players)
    
    def _show_trump_card(self):
        return str(self.trump_card)

    def _show_trump_suit(self):
        return str(self.trump_suit)
    
    def _show_players_and_scores(self):
        return str(self.players_and_scores)
    
    def _show_history(self):
        return str(self.round_vector_history)
    
    def _show_teams(self):
        return str(self.teams)
    
    def _show_final_scores_and_print_winner(self):
        team1_score = sum(self.players_and_scores[player] for player in self.teams[0])
        team2_score = sum(self.players_and_scores[player] for player in self.teams[1])

        print(f"Team 1 (Players {self.teams[0][0].name} & {self.teams[0][1].name}) scored: {team1_score}")
        print(f"Team 2 (Players {self.teams[1][0].name} & {self.teams[1][1].name}) scored: {team2_score}")

        if team1_score > team2_score:
            print("Team 1 is victorious 🏆!")
        elif team2_score > team1_score:
            print("Team 2 is victorious 🏆!")

class Player:
    def __init__(self,name,player_id):
        self.name = name
        self.hand = []
        self.player_id = player_id

    def receive_cards(self,set_of_cards):
        self.hand = set_of_cards

    def play_card(self):
        while True:
            try:
                print("Select a card by its number (1 to {}):".format(len(self.hand)))
                choice = int(input("Choice? ").strip()) - 1  
                if 0 <= choice < len(self.hand):
                    return self.hand.pop(choice)
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Please enter a valid number.")


    def _play_cut(self):
        """Can cut plays made by other players might not be necessary, look above fix later"""

    def __repr__(self):
        return f"Player {self.player_id} == {self.name}"
    
    def _view_hand(self):
        print(f"Hand of Player {self.player_id} =>")
        hand_str = ' '.join(str(card) for card in self.hand)  
        return hand_str

def main():
    game = Game(["Pedro","Tiago","Lucas","Gonçalo"])
    i = 0
    print(game._show_trump_card())
    while i<10:
        game._round()
        i+=1      
    game._show_final_scores_and_print_winner()
       
main() 
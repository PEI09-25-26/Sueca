import random
from card import *
from deck import *
from constants import *
from player import *


class Game:

    def __init__(self,player_names):
        self.deck = Deck()
        self.deck.shuffle_deck()
        self.deck.cut_deck()
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
        self.last_round_winner = self.players[0]
        self.round_suit = ''
        self.current_player = self.last_round_winner


    def _get_trump_card(self):
        while True:
            answer = input("Take trump_card from top or bottom?: ").strip().lower()
            if answer=="top":
                trump_card = self.deck.pile[0]
                break
            elif answer == "bottom":
                trump_card = self.deck.pile[-1]
                break
            else:
                print(f"Invalid answer, try again. ")
        self.trump_card = trump_card
        return trump_card


   

    def _distribute_cards(self):   
        for player in self.players:
            set_cards=[self.deck.pile.pop(0) for i in range(10)]    
            player.receive_cards(set_cards)

    def assure_it_can_be_played(self, card, player):
        has_round_suit = any(c.suit == self.round_suit for c in player.hand)
        if card.suit == self.round_suit:
            return True
        if card.suit == self.trump_card.suit:
            return True
        if has_round_suit:
            return False
       
        return True

    
    def _round(self):
        print(f"========================================")
        print(f"Round {self.round_counter}")
        round_vector = []
        current_player = self.last_round_winner
        start_index = self.players.index(self.last_round_winner)
        turn_order = self.players[start_index:] + self.players[:start_index]
        for player in turn_order:
            print(f"It's Player {player.player_id}'s turn: ({player.name})")
            print(player._view_hand())
            if player == self.last_round_winner:
                print(f"Player {player.player_id} takes the lead this round, as they played the strongest last round, or distributed the deck.")
                round_vector.append(player.play_card())
                self.round_suit = round_vector[0].suit
                print(f"This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {self.trump_card.suit}  alternatively.")
            else:
                while True:
                    possible_card = player.play_card()
                    if self.assure_it_can_be_played(possible_card, player):
                        round_vector.append(possible_card)
                        break
                    else:
                        print(f"You must follow suit ({self.round_suit})!")
                        player.hand.append(possible_card)

        print("\nCards played this round:")
        for i, card in enumerate(round_vector, start=1):
            print(f"Player {self.players[i-1].player_id} played: {card}")

        self.round_vector_history.append({
            "round_suit": self.round_suit,
            "cards": round_vector[:]
        })

        def _determine_round_winner():
            trump_was_played = any(card.suit == self.trump_suit for card in round_vector)

            
            if trump_was_played:
                trump_cards = [card for card in round_vector if card.suit == self.trump_suit]
                winner = max(trump_cards,key=lambda card:ranks_map[card.rank])
                winner_index = round_vector.index(winner)
                return winner,winner_index
            
            winner = max(round_vector,key=lambda card:ranks_map[card.rank])
            winner_index = round_vector.index(winner)
            return winner,winner_index

        round_winner, winner_index = _determine_round_winner()
        winner_player = self.players[winner_index]
        self.last_round_winner = winner_player

        def _get_round_sum():
            round_sum = 0
            for card in round_vector:
                round_sum+=ranks_map[card.rank]
            return round_sum

        print(f"Round winner was {round_winner},  Player {winner_player.player_id} ({winner_player.name}) wins {_get_round_sum()} points.")

        # Update score
        self.players_and_scores[winner_player] += _get_round_sum()

        while True:
            answer = input("View game history so far?").strip().lower()
            if answer=="yes":
                print("Game history vector:")
                print(self.get_history())
                break
            break
        self.round_counter+=1

    def get_deck(self):
        return str(self.deck)

    def get_players (self):
        return str(self.players)
    
    def get_trump_card(self):
        return str(self.trump_card)

    def get_trump_suit(self):
        return str(self.trump_suit)
    
    def get_players_and_scores(self):
        return str(self.players_and_scores)
    
    def get_history(self):
        history_str = ""
        for round_num, round_data in enumerate(self.round_vector_history, start=1):
            cards = round_data["cards"]
            suit = round_data["round_suit"]

            history_str += f"Round {round_num} (suit: {suit}):\n"
            if not cards:
                history_str += "  (no cards recorded)\n"
            else:
                for i, card in enumerate(cards):
                    player = self.players[i]  # careful: assumes fixed order
                    history_str += f"  Player {player.player_id} ({player.name}) played {card}\n"
            history_str += "\n"

        return history_str
    
    def get_teams(self):
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

def main():
    game = Game(["Pedro","Tiago","Lucas","Gonçalo"])
    i = 0
    while i<10:
        print(f"This game's trump is {game.get_trump_card()}")
        game._round()
        i+=1      
    game._show_final_scores_and_print_winner()
       
main() 
from .card_mapper import CardMapper
from collections import deque


SUITS = ["♣", "♦", "♥", "♠"]

class Referee:
    def __init__(self, game_id="default"):
        self.card_queue = deque()
        self.players = {"player0":[True,True,True,True],
                        "player1":[True,True,True,True],
                        "player2":[True,True,True,True],
                        "player3":[True,True,True,True]
                        }
        self.game_id = game_id
        self.trump_set = False
        self.current_player = 0 
        self.dealer = -1 # -1 means not chosen yet
        self.trump=None
        self.trump_suit=None
        self.trump_owner_player = None
        self.trump_was_played = False
        self.round_vector = []
        self.rounds_played = 0
        self.current_round = 1
        self.phase = "waiting"
        self.team1_points = 0
        self.team2_points = 0
        self.team1_victories = 0
        self.team2_victories = 0
        self.first_player=0

    
    def state(self):
        # Determine who should be highlighted in the UI
        # During waiting, it's the dealer or current action taker
        # During playing, it's the current_player
        highlight = self.current_player
        if self.phase == "waiting" and not self.trump_set:
             highlight = self.dealer

        return {
            "game_id": self.game_id,
            "phase": self.phase,
            "trump_set": self.trump_set,
            "trump": CardMapper.get_card(self.trump) if self.trump else None,
            "trump_suit": self.trump_suit,
            "trump_owner_player": self.trump_owner_player,
            "trump_owner_label": f"player{self.trump_owner_player}" if self.trump_owner_player is not None else None,
            "queue_size": len(self.card_queue),
            "rounds_played": self.rounds_played,
            "current_round": self.current_round,
            "current_player": highlight,
            "current_player_label": f"player{highlight}",
            "team1_points": self.team1_points,
            "team2_points": self.team2_points,
            "team1_victories": self.team1_victories,
            "team2_victories": self.team2_victories,
            "new_game": self.rounds_played == 0
        }

    def receive_card(self):
        if not self.card_queue:
            raise RuntimeError("No card available")
        return self.card_queue.popleft()

    def inject_card(self, card_id: int):
        self.card_queue.append(card_id)

    def replace_last_card(self, card_id: int):
        if not self.card_queue:
            return False
        self.card_queue.pop()
        self.card_queue.append(card_id)
        return True

    def set_trump(self):
        self.trump = self.receive_card()
        self.trump_suit = CardMapper.get_card_suit(self.trump)
        self.trump_set = True
        self.trump_owner_player = self.dealer
        self.phase = "playing"
        # The starter is the person to the RIGHT of the dealer (counter-clockwise)
        # In our 0,1,2,3 order, the person to the right of N(1) is E(0)
        self.current_player = (self.dealer + 3) % 4
        print(f"Trump set to {CardMapper.get_card(self.trump)} for dealer {self.dealer}. Starter (Right of dealer): {self.current_player}")

    def play_round(self):
        self.rounds_played += 1
        self.current_round = self.rounds_played
        # Identify who started this trick
        starter_of_trick = self.current_player
        
        for i in range(4):
            card_number = self.receive_card()
            self.round_vector.append(card_number)

            if card_number == self.trump:
                self.trump_was_played = True
                print("[DEBUG] Trump was played this round!")

            card_suit = CardMapper.get_card_suit(card_number)
            card_suit_index = SUITS.index(card_suit)
            
            # Use trick starter to identify whose card this is
            this_player = (starter_of_trick + i) % 4
            player = f"player{this_player}"

            if i == 0:
                round_suit = card_suit
                round_suit_index = SUITS.index(round_suit)
            else:
                if not self.players[player][card_suit_index]:
                    print(f"[RENUNCIA] Player {this_player} made an illegal play!")
                    if this_player % 2 != 0:
                        self.team2_victories += 4 # Partner of 1,3 is 0,2
                    else:
                        self.team1_victories += 4
                    self.reset_players()
                    return False
                if card_suit != round_suit:
                    self.players[player][round_suit_index] = False
                    
                    # Last player check for trumps
                    last = (starter_of_trick + 3) % 4

                    if not self.trump_was_played and card_suit == self.trump_suit and this_player == last:
                        print(f"[RENUNCIA] Player {this_player} (LAST) failed to play trump!")
                        if this_player % 2 != 0:
                            self.team2_victories += 4
                        else:
                            self.team1_victories += 4
                        self.reset_players()
                        return False

        winner_rel_index = self.determine_round_winner(round_suit)
        winner_abs_id = (starter_of_trick + winner_rel_index) % 4
        
        self.get_round_sum(winner_abs_id)

        # Winner starts next trick
        self.current_player = winner_abs_id

        self.reset_round()
        return True

    def reset_players(self):
        self.players = {"player0":[True,True,True,True],
                        "player1":[True,True,True,True],
                        "player2":[True,True,True,True],
                        "player3":[True,True,True,True]
                        }
        self.round_vector = []
        self.trump_was_played = False
        self.trump=None
        self.trump_suit=None
        self.trump_set=False
        self.rounds_played = 0
        self.card_queue.clear()
        self.current_round = 1
        self.phase = "waiting"
        self.trump_owner_player = None
        
        # Dealer advances counter-clockwise
        self.dealer = (self.dealer + 1) % 4
        self.current_player = self.dealer # During waiting, current is dealer
        print(f"[DEBUG] PLAYERS RESET. New dealer: {self.dealer}")

    def reset_round(self):
        self.round_vector = []
        self.trump_was_played = False
        if self.rounds_played == 10:
            self.get_game_winner()
        
    def get_trump(self):
        self.trump = self.receive_card()
        self.trump_suit = CardMapper.get_card_suit(self.trump)

    def determine_round_winner(self, suit):
        # Calculate which of the 4 cards in round_vector wins
        # Use a manual loop to avoid issues with enumerate if not available in this environment
        round_trumps = []
        for i in range(len(self.round_vector)):
            c = self.round_vector[i]
            if CardMapper.get_card_suit(c) == self.trump_suit:
                round_trumps.append((i, c))

        if round_trumps:
            # Highest trump wins
            winner_rel_index = max(round_trumps, key=lambda x: x[1])[0]
            return winner_rel_index

        # Highest of the lead suit wins
        suit_cards = []
        for i in range(len(self.round_vector)):
            c = self.round_vector[i]
            if CardMapper.get_card_suit(c) == suit:
                suit_cards.append((i, c))

        winner_rel_index = max(suit_cards, key=lambda x: x[1])[0]
        return winner_rel_index

    def get_round_sum(self, winner_abs_id):
        """Returns the sum of the cards that were played this round. """
        round_sum = sum((CardMapper.get_card_points(card_number)) for card_number in self.round_vector)
        # Teams: Team 1 (1,3), Team 2 (0,2) -- logic from reset_players renuncia
        # Wait, if North is 1 and South is 3. Team 1 = 1 & 3.
        # If winner is 1 or 3 -> Team 1 points.
        if winner_abs_id in [1, 3]:
            self.team1_points += round_sum
        else:
            self.team2_points += round_sum
        print(f"Round winner: Player {winner_abs_id} | Round points: {round_sum}\n")

    def get_game_winner(self):
        if self.team1_points > self.team2_points:
            if self.team2_points >= 30:
                self.team1_victories += 1
                print("Team 1 wins the game!")
            elif self.team2_points > 0:
                self.team1_victories += 2
                print("Team 1 wins the game and team 2 didn't make 30 points (Team 1 +2 victories)!")
            else:
                self.team1_victories += 4
                print("Team 1 wins the game and team 2 made no points (Team 1 +4 victories)!")
        elif self.team2_points > self.team1_points:
            if self.team1_points >= 30:
                self.team2_victories += 1
                print("Team 2 wins the game!")
            elif self.team1_points > 0:
                self.team2_victories += 2
                print("Team 2 wins the game and team 1 didn't make 30 points (Team 2 +2 victories)!")
            else:
                self.team2_victories += 4
                print("Team 2 wins the game and team 1 made no points (Team 2 +4 victories)!")
        self.reset_players()

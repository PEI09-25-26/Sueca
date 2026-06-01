try:
    from .card_mapper import CardMapper
except ImportError:
    # Fallback for direct script execution outside package context.
    from card_mapper import CardMapper
from collections import deque


SUITS = ["♣", "♦", "♥", "♠"]


class Referee:
    def __init__(self, game_id="default"):
        self.card_queue = deque()
        self.players = {
            "player0": [True, True, True, True],
            "player1": [True, True, True, True],
            "player2": [True, True, True, True],
            "player3": [True, True, True, True],
        }
        self.game_id = game_id
        self.trump_set = False
        self.current_player = 0
        self.dealer = -1  # -1 means not chosen yet.
        self.trump = None
        self.trump_suit = None
        self.trump_owner_player = None
        self.trump_was_played = False
        self.round_vector = []
        self.rounds_played = 0
        self.current_round = 1
        self.current_match = 1
        self.phase = "waiting"
        self.team1_points = 0
        self.team2_points = 0
        self.team1_victories = 0
        self.team2_victories = 0
        self.trick_starter = None

    def state(self):
        highlight = self.current_player
        if self.phase == "waiting" and not self.trump_set:
            highlight = self.dealer

        positions = ["East", "North", "West", "South"]
        players_list = []
        for idx in range(4):
            cards_left = 10 - self.rounds_played
            players_list.append({
                "id": f"player{idx}",
                "player_id": f"player{idx}",
                "name": f"Player {idx} ({positions[idx]})",
                "player_name": f"Player {idx} ({positions[idx]})",
                "position": positions[idx],
                "cards_left": cards_left,
            })

        # Dynamically map round plays from card queue
        round_plays = []
        if self.trump_set:
            for i, card_id in enumerate(self.card_queue):
                if self.trick_starter is not None:
                    p_idx = (self.trick_starter + i) % 4
                else:
                    # Fallback helper if trick starter is not set
                    p_idx = (self.current_player - len(self.card_queue) + i) % 4
                
                round_plays.append({
                    "player_id": f"player{p_idx}",
                    "player_name": f"Player {p_idx} ({positions[p_idx]})",
                    "card": str(card_id),
                    "position": positions[p_idx],
                })

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
            "current_round": self.rounds_played if self.rounds_played > 0 else 1,
            "current_player": highlight,
            "current_player_id": f"player{highlight}",
            "current_player_name": f"Player {highlight} ({positions[highlight]})",
            "current_player_label": f"player{highlight}",
            "team1_points": self.team1_points,
            "team2_points": self.team2_points,
            "team1_victories": self.team1_victories,
            "team2_victories": self.team2_victories,
            "new_game": self.rounds_played == 0,
            "players": players_list,
            "player_count": 4,
            "game_started": self.trump_set,
            "teams": {
                "team1": ["Player 1 (North)", "Player 3 (South)"],
                "team2": ["Player 0 (East)", "Player 2 (West)"],
            },
            "scores": {
                "player0": 0,
                "player1": 0,
                "player2": 0,
                "player3": 0,
            },
            "team_scores": {
                "team1": self.team1_points,
                "team2": self.team2_points,
            },
            "match_points": {
                "team1": self.team1_victories,
                "team2": self.team2_victories,
            },
            "matches_played": self.current_match - 1,
            "current_match_number": self.current_match,
            "round_plays": round_plays,
            "dealer": self.dealer,
            "trick_starter": self.trick_starter,
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
        # Starter is the player to the left of the dealer.
        self.current_player = (self.dealer + 1) % 4
        print(
            f"Trump set to {CardMapper.get_card(self.trump)} for dealer {self.dealer}. "
            f"Starter: {self.current_player}"
        )

    def play_round(self):
        self.rounds_played += 1
        self.current_round = self.rounds_played
        starter_of_trick = self.trick_starter
        if starter_of_trick is None:
            starter_of_trick = self.current_player

        for i in range(4):
            card_number = self.receive_card()
            self.round_vector.append(card_number)

            if card_number == self.trump:
                self.trump_was_played = True
                print("[DEBUG] Trump was played this round!")

            card_suit = CardMapper.get_card_suit(card_number)
            card_suit_index = SUITS.index(card_suit)
            this_player = (starter_of_trick + i) % 4
            player = f"player{this_player}"

            if i == 0:
                round_suit = card_suit
                round_suit_index = SUITS.index(round_suit)
            else:
                if not self.players[player][card_suit_index]:
                    print(f"[RENUNCIA] Player {this_player} made an illegal play!")
                    if this_player % 2 != 0:
                        self.team2_victories += 4
                    else:
                        self.team1_victories += 4
                    self.reset_players()
                    return False
                if card_suit != round_suit:
                    self.players[player][round_suit_index] = False

        winner_rel_index = self.determine_round_winner(round_suit)
        winner_abs_id = (starter_of_trick + winner_rel_index) % 4

        self.get_round_sum(winner_abs_id)
        self.current_player = winner_abs_id
        self.trick_starter = None

        self.reset_round()
        return True

    def reset_players(self):
        self.players = {
            "player0": [True, True, True, True],
            "player1": [True, True, True, True],
            "player2": [True, True, True, True],
            "player3": [True, True, True, True],
        }
        self.round_vector = []
        self.trump_was_played = False
        self.trump = None
        self.trump_suit = None
        self.trump_set = False
        self.rounds_played = 0
        self.card_queue.clear()
        self.current_round = 1
        self.phase = "waiting"
        self.trump_owner_player = None
        self.trick_starter = None
        self.team1_points = 0
        self.team2_points = 0

        # Note: Dealer increment is handled by game_core.py or explicitly set
        self.current_player = (self.dealer + 1) % 4
        print(f"[DEBUG] PLAYERS RESET. Dealer remains: {self.dealer}. Starter: {self.current_player}")

    def reset_round(self):
        self.round_vector = []
        self.trump_was_played = False
        self.trick_starter = None

    def get_trump(self):
        self.trump = self.receive_card()
        self.trump_suit = CardMapper.get_card_suit(self.trump)

    def determine_round_winner(self, suit):
        round_trumps = []
        for i in range(len(self.round_vector)):
            card_number = self.round_vector[i]
            if CardMapper.get_card_suit(card_number) == self.trump_suit:
                round_trumps.append((i, card_number))

        if round_trumps:
            return max(round_trumps, key=lambda x: x[1])[0]

        suit_cards = []
        for i in range(len(self.round_vector)):
            card_number = self.round_vector[i]
            if CardMapper.get_card_suit(card_number) == suit:
                suit_cards.append((i, card_number))

        return max(suit_cards, key=lambda x: x[1])[0]

    def get_round_sum(self, winner_abs_id):
        round_sum = sum(CardMapper.get_card_points(card_number) for card_number in self.round_vector)
        # NORTH (1) and SOUTH (3) are on Team 1
        # EAST (0) and WEST (2) are on Team 2
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


"""
GameStateTracker - Maintains complete game state for AI decision making
"""
from collections import defaultdict
from .card_mapper import CardMapper
from .positions import Positions
from .card_analyzer import CardAnalyzer


class GameStateTracker:
    """Tracks all relevant game state for intelligent card play"""
    
    def __init__(self):
        # Player identity
        self.player_name = None
        self.position = None  # Positions enum
        self.team_id = None  # 0 or 1 (Team 1 = N/S, Team 2 = E/W)
        self.partner_id = None  # partner's name
        self.partner_position = None
        self.opponents = []  # list of opponent names
        
        # Trump
        self.trump_suit = None
        self.trump_card = None
        
        # Cards tracking
        self.my_hand = []  # current hand (list of card_ids)
        self.cards_played = []  # (player, card_id, round_num) tuples
        self.cards_played_by_player = defaultdict(list)  # player -> [cards]
        self.trick_history = []  # completed tricks
        self.current_trick = []  # (player, card_id) tuples for current trick
        
        # Round state
        self.current_round = 1
        self.lead_suit = None  # suit of first card in current trick
        
        # Inference (advanced card tracking)
        self.remaining_cards = set(range(40))  # cards not yet played
        self.remaining_trumps = set()  # trump cards not yet played
        self.void_suits_by_player = defaultdict(set)  # player -> {void suits}
        self.possible_cards_by_player = defaultdict(set)  # player -> {cards}
        
        # Scores
        self.team_points = 0
        self.opponent_points = 0
    
    def reset(self):
        """
        Reset all state to initial values.
        """
        self.__init__()
    
    def update_from_state(self, state, player_name):
        """
        Update tracker from server's game state dictionary.
        """
        self.player_name = player_name        
        for player in state["players"]:
            if player["name"] == player_name:
                self.position = Positions[player["position"]]

        self._determine_team_info(state)
        if state["trump_suit"]:
            self.trump_suit = state["trump_suit"]
            # Initialize remaining trumps if trump is known
            self.remaining_trumps = {
                i for i in range(40) 
                if CardMapper.get_card_suit(i) == self.trump_suit
            }
        self.current_round = state["current_round"]
        
        # Update team scores based on our team_id
        if self.team_id == 0:  # Team 1 (N/S)
            self.team_points = state["team_scores"]["team1"]
            self.opponent_points = state["team_scores"]["team2"]
        else:  # Team 2 (E/W)
            self.team_points = state["team_scores"]["team2"]
            self.opponent_points = state["team_scores"]["team1"]
        
        # Convert round_plays to list of (player, card_id) tuples
        self.current_trick = []
        self.lead_suit = state["round_suit"]
        for play in state["round_plays"]:
            card_id = int(play["card"])
            player_name_in_play = play["player"]
            self.current_trick.append((player_name_in_play, card_id))
            self._update_card_knowledge(player_name_in_play, card_id)
    
    def update_my_hand(self, hand):
        """
        Update agent's current hand.
        """
        self.my_hand = [int(card_str) for card_str in hand]

        for player in self.possible_cards_by_player:
            self.possible_cards_by_player[player] -= set(self.my_hand)


    def _determine_team_info(self, state):
        """
        Figure out team, partner, and opponents from state.
        """
        teams = state["teams"]
        
        # Check which team we're on
        if self.player_name in teams["team1"]:
            self.team_id = 0
            # Get partner (other player on our team)
            self.partner_id = [partner for partner in teams["team1"] if partner != self.player_name][0]
            self.opponents = teams["team2"]
        else:
            self.team_id = 1
            self.partner_id = [partner for partner in teams["team2"] if partner != self.player_name][0]
            self.opponents = teams["team1"]
        
        # Find partner's position
        for player in state["players"]:
            if player["name"] == self.partner_id:
                self.partner_position = Positions[player["position"]]
                break

    
    def _update_card_knowledge(self, player, card_id):
        """
        Update knowledge about remaining cards and detect void suits.
        """
        self.remaining_cards.discard(card_id)
        card_suit = CardMapper.get_card_suit(card_id)
        if self.trump_suit == card_suit:
            self.remaining_trumps.discard(card_id)

        if self.lead_suit and card_suit != self.lead_suit:
            self.void_suits_by_player[player].add(self.lead_suit)
        
    
    def get_remaining_cards_of_suit(self, suit):
        """
        Get all unplayed cards of a specific suit.
        """
        return {card for card in self.remaining_cards if CardMapper.get_card_suit(card) == suit}

    def get_my_cards_of_suit(self, suit):
        """
        Get my hand cards of a specific suit.
        """
        return [card for card in self.my_hand if CardMapper.get_card_suit(card) == suit]
    
    def is_partner_winning(self):
        """
        Check if partner is currently winning the trick.
        """
        if not self.current_trick:
            return False
        winner = self.get_current_trick_winner()
        return winner == self.partner_id
    
    def get_current_trick_winner(self):
        """
        Determine who's currently winning the trick.
        """
        if not self.current_trick:
            return None
        
        trump_cards=[]
        for player, card in self.current_trick:
            suit = CardMapper.get_card_suit(card)
            if suit == self.trump_suit:
                trump_cards.append((player, card))

        if trump_cards:
            candidate_cards = trump_cards
        else:
            lead_suit = CardMapper.get_card_suit(self.current_trick[0][1])
            candidate_cards = [(player, card) for player, card in self.current_trick
                            if CardMapper.get_card_suit(card) == lead_suit]

        winner_player, winner_card = max(candidate_cards, key=lambda x: CardAnalyzer.get_card_strength(x[1], self.trump_suit, self.lead_suit))

        return winner_player

    def get_trick_points(self, trick=None):
        """
        Calculate total points in a trick.
        """
        if trick is None:
            trick = self.current_trick
        
        total = 0
        for _, card_id in trick:
            total += CardMapper.get_card_points(card_id)
            
        return total

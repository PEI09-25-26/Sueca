"""
GameStateTracker - Maintains complete game state for AI decision making
DO THIS CLASS SECOND (after CardAnalyzer)
"""
from collections import defaultdict
from card_mapper import CardMapper
from positions import Positions
from card_analyzer import CardAnalyzer


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
        
        TODO:
        1. Set all simple attributes to None or 0
        2. Reset lists to []
        3. Reset defaultdicts to new defaultdict instances
        4. Reset remaining_cards to set(range(40))
        """
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
    
    def update_from_state(self, state, player_name):
        """
        Update tracker from server's game state dictionary.
        
        Args:
            state: dict from server's /api/status endpoint
            player_name: our agent's name
        
        TODO:
        1. Store player_name
        2. Find our position from state['players'] list
        3. Call _determine_team_info(state) to figure out teams
        4. Update trump_suit from state if present
        5. Initialize remaining_trumps if trump is known
        6. Update current_round from state
        7. Update team scores (be careful: you're either team1 or team2)
        8. Update current_trick from state['round_plays']
        9. Update lead_suit from state['round_suit']
        10. For each card in current trick, call _update_card_knowledge
        
        Hint: state structure is in server.py's get_state() method
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
        for play in state["round_plays"]:
            card_id = int(play["card"])
            player_name_in_play = play["player"]
            self.current_trick.append((player_name_in_play, card_id))
            self._update_card_knowledge(player_name_in_play, card_id)
        
        self.lead_suit = state["round_suit"]

    
    def update_my_hand(self, hand):
        """
        Update agent's current hand.
        
        Args:
            hand: list of card strings (e.g., ['0', '5', '12'])
        
        TODO:
        1. Convert hand strings to ints
        2. Store in self.my_hand
        3. (Optional) Remove my cards from possible_cards_by_player for others
        """
        cards_to_int = [int(card_str) for card_str in hand]
        self.my_hand = cards_to_int
        for card in self.my_hand:
            self.possible_cards_by_player.pop(card,None)


    def _determine_team_info(self, state):
        """
        Figure out team, partner, and opponents from state.
        
        Args:
            state: dict from server
        
        TODO:
        1. Get teams from state['teams'] (team1 and team2)
        2. Check if player_name is in team1 or team2
        3. Set self.team_id (0 for team1, 1 for team2)
        4. Set self.partner_name (other player on your team)
        5. Set self.opponents (list of 2 players on other team)
        6. Find partner's position from state['players']
        
        Teams: Team 1 = NORTH + SOUTH, Team 2 = EAST + WEST
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
        
        Args:
            player: name of player who played card
            card_id: card that was played
        
        TODO:
        1. Remove card_id from self.remaining_cards
        2. Get card's suit
        3. If card is trump, remove from self.remaining_trumps
        4. VOID DETECTION:
           - If self.lead_suit exists AND card_suit != lead_suit:
             - Player didn't follow suit → they're void in lead_suit!
             - Add lead_suit to self.void_suits_by_player[player]
        
        This is how you track what suits opponents don't have!
        """
        self.remaining_cards.remove(card_id)
        card_suit = CardMapper.get_card_suit(card_id)
        if self.trump_suit == card_suit:
            self.remaining_trumps.remove(card_id)

        if self.lead_suit and card_suit!= self.lead_suit:
            self.void_suits_by_player[player].add(self.lead_suit)
        
    
    def get_remaining_cards_of_suit(self, suit):
        """
        Get all unplayed cards of a specific suit.
        
        Returns: set of card_ids
        
        TODO:
        1. Filter self.remaining_cards for cards where suit matches
        2. Return as set
        
        Hint: Use set comprehension with CardMapper.get_card_suit()
        """
        return set(filter(lambda card: CardMapper.get_card_suit(card) == suit, self.remaining_cards))
    
    def get_my_cards_of_suit(self, suit):
        """
        Get my hand cards of a specific suit.
        
        Returns: list of card_ids
        
        TODO:
        1. Filter self.my_hand for cards where suit matches
        2. Return as list
        """
        return list(filter(lambda card: CardMapper.get_card_suit(card) == suit, self.my_hand))
    
    def is_partner_winning(self):
        """
        Check if partner is currently winning the trick.
        
        Returns: bool
        
        TODO:
        1. If current_trick is empty, return False
        2. Call _get_current_trick_winner() to find winner
        3. Return True if winner == self.partner_name
        """
        if not self.current_trick:
            return False
        winner = self._get_current_trick_winner()
        return winner == self.partner_name
    
    def _get_current_trick_winner(self):
        """
        Determine who's currently winning the trick.
        
        Returns: player_name or None
        
        TODO:
        1. If no cards in current_trick, return None
        2. Separate trick into trump cards and non-trump cards
        3. If any trumps were played:
           - Winner is player with highest trump card
        4. Else:
           - Winner is player with highest card in lead_suit
        5. Return winner's player name
        
        Hint: Use max() with card_id as key (higher id = higher rank in suit)
        """
        if not self.current_trick:
            return None
        trump_cards=[]
        non_trump_cards=[]
        for card in self.current_trick:
            suit = CardMapper.get_card_suit(card)
            if suit==self.trump_suit:
                trump_cards.append(card)
            else:
                non_trump_cards.append(card)

        if trump_cards:
            candidate_cards = trump_cards
        else:
            lead_suit = CardMapper.get_card_suit(self.current_trick[0][1])
            candidate_cards = [(player, card) for player, card in self.current_trick
                            if CardMapper.get_card_suit(card) == lead_suit]

        winner_player, winner_card = max(candidate_cards, key=lambda x: CardAnalyzer.get_card_strength(x[1]))

        return winner_player

    def get_trick_points(self, trick=None):
        """
        Calculate total points in a trick.
        
        Args:
            trick: list of (player, card_id) tuples (uses current_trick if None)
        
        Returns: int - total points
        
        TODO:
        1. If trick is None, use self.current_trick
        2. Sum up points for each card using CardMapper.get_card_points()
        3. Return total
        """
        total = 0

        if trick is None:
            lst = self.current_trick
        else:
            lst = trick
            for (player,card_id) in trick:
                total+=CardMapper.get_card_points(card_id)
        return total

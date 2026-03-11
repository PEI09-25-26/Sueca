"""
DecisionMaker - Makes card play decisions using heuristics
DO THIS CLASS THIRD (needs CardAnalyzer and GameStateTracker)
"""
from card_analyzer import CardAnalyzer
from card_mapper import CardMapper
import random


class DecisionMaker:
    """
    Implements heuristic-based decision making for weak AI.
    
    Core Strategy:
    - If partner is winning: play low card (don't waste good cards)
    - If trick has high points: try to win with lowest winning card
    - If can't win or low points: play lowest card
    """
    
    def __init__(self, game_state_tracker):
        """
        Args:
            game_state_tracker: reference to GameStateTracker instance
        """
        self.state = game_state_tracker
    
    def choose_card(self, hand):
        """
        Main decision function - choose best card to play.
        
        Args:
            hand: list of card_ids in our hand
        
        Returns: card_id to play
        
        TODO:
        1. If hand is empty, return None
        2. Get legal plays using CardAnalyzer.get_legal_plays()
        3. If only one legal play, return it
        4. Decide based on position in trick:
           - If no cards played yet: call _choose_lead_card()
           - If 3 cards played (we're last): call _choose_last_card()
           - Otherwise (2nd or 3rd): call _choose_middle_card()
        5. Return chosen card
        """
    
    def _choose_lead_card(self, legal_plays):
        """
        Choose card when leading the trick (first to play).
        
        Strategy:
        - Avoid leading with trump early in game
        - Play medium-strength cards
        - Late game: be more aggressive
        
        TODO:
        1. Check if late game (round >= 8):
           - If yes, prefer high-value cards (A or 7)
           - Use CardAnalyzer.get_highest_card()
        2. Separate legal_plays into trump and non-trump cards
        3. If we have non-trump cards:
           - Sort them by strength
           - Pick a middle-strength card (not highest, not lowest)
        4. If all trumps:
           - Play lowest trump (save good ones)
        5. Return chosen card
        
        Hint: Sort and pick cards[len(cards)//2] for middle
        """
        pass
    
    def _choose_last_card(self, legal_plays):
        """
        Choose card when playing last (4th position in trick).
        
        Strategy:
        - If partner winning: play lowest card
        - If high-value trick: try to win cheaply
        - Otherwise: play lowest card
        
        TODO:
        1. Check if partner is winning using self.state.is_partner_winning()
        2. If partner winning:
           - Return lowest card (CardAnalyzer.get_lowest_card)
        3. Get trick points using self.state.get_trick_points()
        4. If trick_points >= 10 (high value):
           - Try to get lowest winning card
           - If we can win, return that card
        5. If can't win or low-value trick:
           - Return lowest card
        """
        pass
    
    def _choose_middle_card(self, legal_plays):
        """
        Choose card when playing 2nd or 3rd in trick.
        
        Strategy:
        - If partner winning: play low
        - If high-value trick: try to win
        - Otherwise: play low
        
        TODO:
        1. Check if partner is winning
        2. If yes, return lowest card
        3. Get trick points
        4. If high value (>= 10 points):
           - Try to win with lowest winning card
           - If can win, return it
           - If can't win, return lowest card
        5. Otherwise (low value):
           - Return lowest card
        """
        pass
    
    def choose_trump_selection(self):
        """
        Decide whether to choose 'top' or 'bottom' card for trump.
        (Used if agent is WEST player)
        
        For weak agent: random choice.
        For stronger agent: could analyze both cards and pick better suit.
        
        Returns: 'top' or 'bottom'
        
        TODO:
        1. Return random choice between 'top' and 'bottom'
        
        Note: A smarter version would check which card/suit is better!
        """
        pass
    
    def choose_deck_cut(self):
        """
        Choose deck cutting position (1-40).
        (Used if agent is NORTH player)
        
        For weak agent: random cut in middle range.
        
        Returns: int between 1-40
        
        TODO:
        1. Return random number between 15-25
        
        Note: Superstitious players have preferences, but it's mostly luck!
        """
        pass

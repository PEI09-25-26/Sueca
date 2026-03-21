"""
DecisionMaker - Makes card play decisions using heuristics
"""
from ..card_analyzer import CardAnalyzer
from ..card_mapper import CardMapper
import random


class DecisionMaker:
    """
    Implements heuristic-based decision making for weak AI.
    
    Core Strategy:
    - RANDOM
    """
    
    def __init__(self, game_state_tracker):
        self.state = game_state_tracker
    
    def choose_card(self, hand):
        """
        Main decision function - choose best card to play.
        """
        if not hand:
            return None

        legal_plays = CardAnalyzer.get_legal_plays(hand, self.state.lead_suit, self.state.trump_suit)

        return random.randint(0, len(legal_plays)-1)
        
    def choose_trump_selection(self):
        """
        Decide whether to choose 'top' or 'bottom' card for trump.
        (Used if agent is WEST player)
        """
        return random.choice(['top', 'bottom'])
    
    def choose_deck_cut(self):
        """
        Choose deck cutting position (1-40).
        (Used if agent is NORTH player)
        """
        return random.randint(1, 40)

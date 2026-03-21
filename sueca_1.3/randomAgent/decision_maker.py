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
    - If partner is winning: play low card (don't waste good cards)
    - If trick has high points: try to win with lowest winning card
    - If can't win or low points: play lowest card
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

        if len(legal_plays) == 1:
            return legal_plays[0]
        
        num_played = len(self.state.current_trick)
        if num_played == 0:
            return self.choose_lead_card(legal_plays)
        elif num_played == 3:
            return self.choose_last_card(legal_plays)
        else:
            return self.choose_middle_card(legal_plays)
    
    def choose_lead_card(self, legal_plays):
        """
        Choose card when leading the trick (first to play).
        
        Strategy:
        - Avoid leading with trump early in game
        - Play medium-strength cards
        - Late game: be more aggressive
        """
        # Late game only -> aggressive play
        if self.state.current_round >= 8:
            return CardAnalyzer.get_highest_card(legal_plays, self.state.trump_suit, self.state.lead_suit)
        
        trumps = []
        non_trumps = []
        for card in legal_plays:
            if CardMapper.get_card_suit(card) == self.state.trump_suit:
                trumps.append(card)
            else:
                non_trumps.append(card)

        if non_trumps != []:
            # Play a medium-strength non-trump card
            sorted_cards = sorted(non_trumps, key=lambda x: CardAnalyzer.get_card_strength(x, self.state.trump_suit, self.state.lead_suit))
            return sorted_cards[len(sorted_cards) // 2]
        else:
            # Only has trumps, play the lowest card
            return CardAnalyzer.get_lowest_card(trumps)
    
    def choose_middle_card(self, legal_plays):
        """
        Choose card when playing 2nd or 3rd in trick.
        
        Strategy:
        - If partner winning: play low
        - If high-value trick: try to win
        - Otherwise: play low
        """
        if self.state.is_partner_winning():
            return CardAnalyzer.get_lowest_card(legal_plays)
        
        trick_points = self.state.get_trick_points()
        if trick_points >= 10:
            # There is a high enough ammount of points in the trick, go for it
            winning_card = CardAnalyzer.get_lowest_winning_card(legal_plays, self.state.current_trick, self.state.trump_suit, self.state.lead_suit)
            if winning_card is not None:
                return winning_card
            else:
                return CardAnalyzer.get_lowest_card(legal_plays)
        else:
            # Not that many points in the trick, play safe
            return CardAnalyzer.get_lowest_card(legal_plays)
        
    
    def choose_last_card(self, legal_plays):
        """
        Choose card when playing last (4th position in trick).
        
        Strategy:
        - If partner winning: play lowest card
        - If high-value trick: try to win cheaply
        - Otherwise: play lowest card
        """
        if self.state.is_partner_winning():
            return CardAnalyzer.get_lowest_card(legal_plays)

        trick_points = self.state.get_trick_points()
        if trick_points >= 10:
            # The trick has a high point count, try to win cheaply
            winning_card = CardAnalyzer.get_lowest_winning_card(
                legal_plays, self.state.current_trick, self.state.trump_suit, self.state.lead_suit
            )
            if winning_card is not None:
                return winning_card

        # Unwinnable trick/trick not worth it
        return CardAnalyzer.get_lowest_card(legal_plays)
        
    
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
        return random.randint(15, 25)

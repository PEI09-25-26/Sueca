"""
CardAnalyzer - Pure utility functions for analyzing cards
"""
from card_mapper import CardMapper


class CardAnalyzer:
    """Analyzes cards for strength, playability, and strategic value"""
    
    # Card strength order within a suit: A > 7 > K > J > Q > 6 > 5 > 4 > 3 > 2
    RANK_ORDER = {
        "A": 9,   # Strongest
        "7": 8,
        "K": 7,
        "J": 6,
        "Q": 5,
        "6": 4,
        "5": 3,
        "4": 2,
        "3": 1,
        "2": 0   # Weakest
    }
    
    @staticmethod
    def get_card_strength(card_id, trump_suit=None, lead_suit=None):
        """
        Calculate how strong a card is in the current context.
        """
        card_suit = CardMapper.get_card_suit(card_id)
        card_rank = CardMapper.get_card_rank(card_id)
        rank_strength = CardAnalyzer.RANK_ORDER[card_rank]

        if card_suit == trump_suit:
            category = 2
        elif card_suit==lead_suit:
            category = 1
        else:
            category = 0
        return (category,rank_strength)
    
    @staticmethod
    def get_legal_plays(hand, lead_suit):
        """
        Get cards that can be legally played (must follow suit if possible).
        """
        if lead_suit is None:
            return hand
        else:
            valid = []
            for card in hand:
                card_suit = CardMapper.get_card_suit(card)
                if card_suit==lead_suit:
                    valid.append(card)
        if not valid:
            return hand
        else:
            return valid        

    
    @staticmethod
    def can_win_trick(card_id, current_trick, trump_suit, lead_suit):
        """
        Check if a card can win the current trick.
        """
        if not current_trick:
            return True
        
        my_strength = CardAnalyzer.get_card_strength(card_id, trump_suit, lead_suit)
        max_strength = (-1, -1)

        for _, card in current_trick:
            strength = CardAnalyzer.get_card_strength(card, trump_suit, lead_suit)
            if strength > max_strength:
                max_strength = strength

        return my_strength > max_strength
    
    @staticmethod
    def get_winning_cards(hand, current_trick, trump_suit, lead_suit):
        """
        Get all cards from hand that can win the current trick.
        """
        legal_plays = CardAnalyzer.get_legal_plays(hand, lead_suit)

        winning_cards = []
        for card in legal_plays:
            if CardAnalyzer.can_win_trick(card, current_trick, trump_suit, lead_suit):
                winning_cards.append(card)

        return winning_cards
    
    @staticmethod
    def get_lowest_winning_card(hand, current_trick, trump_suit, lead_suit):
        """
        Get the weakest card that can still win the trick.
        (Strategy: win cheaply!)
        """
        winning_cards = CardAnalyzer.get_winning_cards(hand, current_trick, trump_suit, lead_suit)
        if not winning_cards:
            return None
        
        return min(winning_cards, key=lambda card: CardAnalyzer.get_card_strength(card, trump_suit, lead_suit))
    
    @staticmethod
    def get_lowest_card(cards, trump_suit=None, lead_suit=None):
        """
        Get the lowest value card from a list.
        Prioritize lowest points and then lowest strength.
        """
        if not cards:
            return None
        
        return min(cards, key=lambda card: (CardMapper.get_card_points(card), CardAnalyzer.get_card_strength(card, trump_suit, lead_suit)))
    
    @staticmethod
    def get_highest_winning_card(hand, current_trick, trump_suit, lead_suit):
        """
        Get the highest card that can win the trick.
        (Strategy: cash out on points!)
        """
        winning_cards = CardAnalyzer.get_winning_cards(hand, current_trick, trump_suit, lead_suit)
        if not winning_cards:
            return None
        
        return max(winning_cards, key=lambda card: CardAnalyzer.get_card_strength(card, trump_suit, lead_suit))

    @staticmethod
    def get_highest_card(cards, trump_suit=None, lead_suit=None):
        """
        Get the highest strength card from a list.
        """
        if not cards:
            return None
        
        return max(cards, key=lambda card: CardAnalyzer.get_card_strength(card, trump_suit, lead_suit))
    
    @staticmethod
    def is_high_value_card(card_id):
        """
        Check if card has high point value (Ace or 7).
        """ 
        card_points = CardMapper.get_card_points(card_id)
        return card_points>=10
    
    @staticmethod
    def count_higher_cards_remaining(card_id, remaining_cards, trump_suit, lead_suit):
        """
        Count how many cards of the same suit are stronger than card_id and still in play.
        """
        card_suit = CardMapper.get_card_suit(card_id)
        card_strength = CardAnalyzer.get_card_strength(card_id, trump_suit, lead_suit)

        counter = 0
        for card in remaining_cards:
            if CardMapper.get_card_suit(card) == card_suit:
                strength = CardAnalyzer.get_card_strength(card, trump_suit, lead_suit)
                if strength > card_strength:
                    counter += 1

        return counter

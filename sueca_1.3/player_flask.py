"""
Player class adapted for Flask-SocketIO
Removes socket handling - communication is handled by Flask-SocketIO events
"""

class Player:
    """
    Represents a player in the Sueca game
    Socket communication removed - handled by Flask-SocketIO
    """
    
    def __init__(self, player_name):
        self.player_name = player_name
        self.hand = []
        self.position = None
        self.trump_suit = None
        self.round_suit = None
        self.team1 = []
        self.team2 = []
        self.partner_name = None
        self.plays_in_trick = 0
    
    def __str__(self):
        return self.player_name
    
    def __repr__(self):
        return f"Player({self.player_name}, {self.position})"
    
    def has_card(self, card):
        """Check if player has a specific card in hand"""
        return card in self.hand
    
    def remove_card(self, card):
        """Remove and return a card from hand"""
        if card in self.hand:
            self.hand.remove(card)
            return card
        return None
    
    def get_hand_by_suit(self, suit):
        """Get all cards of a specific suit from hand"""
        from card_mapper import CardMapper
        return [card for card in self.hand if CardMapper.get_card_suit(card) == suit]
    
    def has_suit(self, suit):
        """Check if player has any card of a specific suit"""
        return len(self.get_hand_by_suit(suit)) > 0
    
    def sort_hand(self):
        """Sort hand by card value"""
        self.hand.sort()
    
    def get_hand_str(self):
        """Get string representation of hand"""
        from card_mapper import CardMapper
        return [CardMapper.get_card(card) for card in self.hand]

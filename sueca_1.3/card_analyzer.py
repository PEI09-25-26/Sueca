"""
CardAnalyzer - Pure utility functions for analyzing cards
START WITH THIS CLASS - it has no dependencies!
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
        
        Returns: tuple (category, strength)
            - category: 0 = off-suit (weakest)
                       1 = lead suit (medium)
                       2 = trump (strongest)
            - strength: rank order within category (0-9)
        
        TODO:
        1. Get the card's suit using CardMapper.get_card_suit(card_id)
        2. Get the card's rank using CardMapper.get_card_rank(card_id)
        3. Get rank strength from RANK_ORDER dictionary
        4. Determine category:
           - If card_suit == trump_suit: category = 2
           - Else if card_suit == lead_suit: category = 1
           - Else: category = 0
        5. Return tuple (category, rank_strength)
        
        Example: A♠ when ♠ is trump and ♥ is lead → (2, 9)
                 7♥ when ♠ is trump and ♥ is lead → (1, 8)
                 K♣ when ♠ is trump and ♥ is lead → (0, 7)
        """
        category = 0
        card_suit = CardMapper.get_card_suit(card_id)
        card_rank = CardMapper.get_card_rank(card_id)
        rank_strength = CardAnalyzer.RANK_ORDER[card_rank]

        if card_suit == trump_suit:
            category = 2
        elif card_suit==lead_suit:
            category = 1

        return (category,rank_strength)
    
    @staticmethod
    def get_legal_plays(hand, lead_suit):
        """
        Get cards that can be legally played (must follow suit if possible).
        
        Args:
            hand: list of card_ids in player's hand
            lead_suit: suit of first card played (None if leading)
        
        Returns: list of card_ids that can be legally played
        
        TODO:
        1. If lead_suit is None (we're leading):
           - Return entire hand (all cards legal)
        2. Filter hand to find cards matching lead_suit:
           - Use CardMapper.get_card_suit(card) for each card
           - Collect cards where suit == lead_suit
        3. If we have cards in lead_suit:
           - Return only those cards (must follow suit)
        4. If we don't have cards in lead_suit:
           - Return entire hand (we're void, can play anything)
        
        Example: hand=[0,1,10,20], lead_suit="♦"
                 Cards 10-19 are diamonds (♦)
                 → must return [10] only
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
        
        Args:
            card_id: card we want to check
            current_trick: list of (player_name, card_id) tuples already played
            trump_suit: trump suit for this game
            lead_suit: suit of first card in trick
        
        Returns: bool - True if card_id beats all cards in current_trick
        
        TODO:
        1. If current_trick is empty:
           - Return True (first card always "wins" initially)
        2. Get strength of our card using get_card_strength()
        3. Loop through each (player, card) in current_trick:
           - Get that card's strength
           - Track the maximum strength seen
        4. Return True if our card's strength > max strength in trick
        
        Hint: Strengths are tuples (category, rank). Python compares
              tuples left-to-right: (2, 0) > (1, 9) because 2 > 1
        """
        if not current_trick:
            return True
        
        card_strength = CardAnalyzer.get_card_strength(card_id)
        myMax = 0
        for (player,card) in current_trick:
            this_card_strength = CardAnalyzer.get_card_strength(card)
            if this_card_strength>myMax:
                myMax=this_card_strength
        return card_strength>myMax
    
    @staticmethod
    def get_winning_cards(hand, current_trick, trump_suit, lead_suit):
        """
        Get all cards from hand that can win the current trick.
        
        Returns: list of card_ids that can win
        
        TODO:
        1. Get legal plays using get_legal_plays()
        2. Filter legal plays to find cards that can_win_trick()
        3. Return list of winning cards
        
        Hint: Use a list comprehension or filter
        """
        legal_plays = CardAnalyzer.get_legal_plays(hand,lead_suit)

        return filter(legal_plays,CardAnalyzer.can_win_trick([card for card in hand],current_trick,trump_suit,lead_suit))
    
    @staticmethod
    def get_lowest_winning_card(hand, current_trick, trump_suit, lead_suit):
        """
        Get the weakest card that can still win the trick.
        (Strategy: win cheaply!)
        
        Returns: card_id or None if no card can win
        
        TODO:
        1. Get all winning cards using get_winning_cards()
        2. If no winning cards, return None
        3. Find the card with minimum strength among winners
        4. Return that card
        
        Hint: Use min() with a key function that gets card strength
        """
        winning_cards = CardAnalyzer.get_winning_cards(hand,current_trick,trump_suit,lead_suit)
        if not winning_cards:
            return None
        maximum_strength_card = min(winning_cards,key=CardAnalyzer.get_card_strength)
        if maximum_strength_card:
            return maximum_strength_card
        return None
    
    @staticmethod
    def get_lowest_card(cards, trump_suit=None):
        """
        Get the lowest value card from a list.
        Prioritize: lowest points, then lowest strength.
        
        Returns: card_id or None if cards is empty
        
        TODO:
        1. If cards is empty, return None
        2. Find card with minimum value, considering:
           - Primary: card points (use CardMapper.get_card_points)
           - Secondary: card strength (use get_card_strength)
        3. Return that card
        
        Hint: min() with key that returns tuple (points, strength)
              Python compares tuples left-to-right
        
        Example: Between 2♣ (0 pts) and 3♣ (0 pts), choose 2♣ (lower rank)
        """
        if not cards:
            return None

        minimum_value_card = min(cards,key=lambda card: (CardMapper.get_card_points(card),CardAnalyzer.get_card_strength(card))
        )
        
        return minimum_value_card
    
    @staticmethod
    def get_highest_card(cards, trump_suit=None, lead_suit=None):
        """
        Get the highest strength card from a list.
        
        Returns: card_id or None if cards is empty
        
        TODO:
        1. If cards is empty, return None
        2. Find card with maximum strength
        3. Return that card
        
        Hint: Use max() with key=get_card_strength
        """
        if not cards:
            return None
        
        return CardAnalyzer.get_highest_card(cards,trump_suit,lead_suit)
    
    @staticmethod
    def is_high_value_card(card_id):
        """
        Check if card has high point value (Ace or 7).
        
        Returns: bool - True if points >= 10
        
        TODO:
        1. Get card points using CardMapper.get_card_points()
        2. Return True if points >= 10, False otherwise
        
        Note: Only A (11 pts) and 7 (10 pts) are high value
        """ 
        card_points = CardMapper.get_card_points(card_id)
        return card_points>=10
    
    @staticmethod
    def count_higher_cards_remaining(card_id, remaining_cards, trump_suit, lead_suit):
        """
        Count how many cards of the same suit are stronger than card_id
        and still in play (not yet played).
        
        Returns: int - count of higher cards
        
        TODO:
        1. Get our card's suit and strength
        2. Initialize counter = 0
        3. Loop through each card in remaining_cards:
           - Get that card's suit
           - If suit matches our card's suit:
             - Get that card's strength
             - If stronger than our card: increment counter
        4. Return counter
        
        Use case: Know if your K♥ is likely to win
                 (are A♥ and 7♥ still in play?)
        """
        card_suit = CardMapper.get_card_suit(card_id)
        card_strength = CardAnalyzer.get_card_strength(card_id,trump_suit,lead_suit)

        counter = 0
        for card in remaining_cards:
            remaining_card_suit = CardMapper.get_card_suit(CardMapper.get_card(card))
            if remaining_card_suit == card_suit:
                remaining_card_strength = CardAnalyzer.get_card_strength(CardMapper.get_card(card))
                if remaining_card_strength>card_strength:
                    counter+=1


        return counter

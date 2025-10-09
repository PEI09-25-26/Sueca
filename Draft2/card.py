class Card:
    def __init__(self,rank,suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}|{self.suit}"
    
    def to_dict(self):
        return {
            "rank":self.rank,
            "suit":self.suit
        }
    
    @classmethod
    def from_string(cls, card_str):
        rank, suit = card_str.split('|')
        return cls(rank, suit)
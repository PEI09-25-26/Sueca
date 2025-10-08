class Player:
    def __init__(self,name,player_id):
        self.name = name
        self.hand = []
        self.player_id = player_id

    def receive_cards(self,set_of_cards):
        self.hand = set_of_cards

    def play_card(self):
        while True:
            try:
                print(f"Select a card by its number (1 to {len(self.hand)}):")
                choice = int(input("Choice? ").strip()) - 1  
                if 0 <= choice < len(self.hand):
                    card = self.hand.pop(choice)
                    return card
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Please enter a valid number.")


    def __repr__(self):
        return f"Player {self.player_id} == {self.name}"
    
    def _view_hand(self):
        print(f"Hand of Player {self.player_id} ({self.name})=>")
        hand_str = '    '.join(str(card) for card in self.hand)  
        return hand_str

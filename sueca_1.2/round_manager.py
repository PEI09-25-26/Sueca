from constants import *
from card_mapper import *
class RoundManager:
    def __init__(self, game_ref, players, player_sockets, last_round_winner, card_mapper, trump_card_suit):
        self.game_ref = game_ref
        self.players = players
        self.player_sockets = player_sockets
        self.last_round_winner = last_round_winner
        
        self.card_mapper = card_mapper
        self.trump_card_suit = trump_card_suit
        
        self.round_vector = []  
        self.round_suit = None  
        self.turn_order = []    
        

    def play_round(self):
        for player in self.turn_order:
            print(f"[PLAYER-ORDER] It's Player [{player.player_name}]'s turn")
            self.broadcast_message(
                f"[PLAYER-ORDER] It's Player's [{player.player_name}]'s turn "
            )
            if player == self.last_round_winner:
                print(
                    f"[PLAYER-ORDER] Player [{player.player_name}] takes the lead this round, as they played the strongest last round, or distributed the deck"
                )
                self.broadcast_message(
                    f"[PLAYER-ORDER] Player {player.player_name} takes the lead this round, as they played the strongest last round, or distributed the deck"
                )
                south_player_socket = self.player_sockets[player.player_name]
                self.send_direct_message(
                    f"[CHOICE] It's your turn, choose a number between 1 and {len(player.hand)} ",
                    south_player_socket,
                )
                first_card_number = south_player_socket.recv(BYTESIZE).decode(ENCODER)
                print(f"THIS IS THE IRST CARD {first_card_number}")
                self.broadcast_message(
                    f"[PLAY] Player [{player.player_name}] played [{CardMapper.get_card(first_card_number)}]"
                )
                for i, c in enumerate(player.hand):
                    if CardMapper.get_card_rank(c) == CardMapper.get_card_rank(
                        first_card_number
                    ) and CardMapper.get_card_suit(c) == CardMapper.get_card_suit(
                        first_card_number
                    ):
                        player.hand.pop(i)
                        removed = True
                        break
                if not removed:
                    print(
                        f"[WARNING] Played card not found in server-side hand: {card_number}"
                    )
                self.round_vector.append(first_card_number)
                self.round_suit = self.round_vector[0][0]
                print(
                    f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {CardMapper.get_card_suit(self.trump_card)} alternatively"
                )
                self.broadcast_message(
                    f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {CardMapper.get_card_suit(self.trump_card)} alternatively "
                )
            else:
                player_socket = self.player_sockets[player.player_name]
                self.send_direct_message(
                    "[CHOICE] It's your turn, choose a number between 1 and 10",
                    player_socket,
                )
                while True:
                    card_number = player_socket.recv(BYTESIZE).decode(ENCODER)
                    if self.assure_card_can_be_played(card_number, player):
                        removed = False
                        for i, c in enumerate(player.hand):
                            if CardMapper.get_card_rank(c) == CardMapper.get_card_rank(
                                card_number
                            ) and CardMapper.get_card_suit(
                                c
                            ) == CardMapper.get_card_suit(
                                card_number
                            ):
                                player.hand.pop(i)
                                removed = True
                                break
                        if not removed:
                            print(
                                f"[WARNING] Played card not found in server-side hand: {CardMapper.get_card(card_number)}"
                            )

                        self.broadcast_message(
                            f"[PLAY] Player [{player.player_name}] played [{CardMapper.get_card(card_number)}]"
                        )
                        round_vector.append(card_number)
                        break
                    else:
                        self.send_direct_message(
                            f"[INVALID] You must follow suit [{self.round_suit}]. Try again ",
                            player_socket,
                        )
                        print(f"[INVALID]You must follow suit [{self.round_suit}] \n")

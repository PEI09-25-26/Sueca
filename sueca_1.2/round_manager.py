from constants import *
from card_mapper import *
class RoundManager:
    def __init__(self, game_ref, players, player_sockets, last_round_winner, card_mapper, trump_card_suit,trump_card):
        self.game_ref = game_ref
        self.players = players
        self.player_sockets = player_sockets
        self.last_round_winner = last_round_winner
        
        self.card_mapper = card_mapper
        self.trump_card = trump_card
        self.trump_card_suit = trump_card_suit
        
        self.round_vector = []  
        self.round_suit = None  
        self.turn_order = []    


    def assure_card_can_be_played(self, card_number, player):
        has_round_suit = any(
            CardMapper.get_card_suit(card) == self.round_suit for card in player.hand
        )
        print(f"Player {player} has_round_suit={has_round_suit}")
        if CardMapper.get_card_suit(card_number) == self.round_suit:
            return True
        elif (
            CardMapper.get_card_suit(card_number) != self.round_suit
            and not has_round_suit
        ):
            return True
        else:
            return False

    def determine_turn_order(self):
        start_index = self.players.index(self.last_round_winner)
        self.turn_order = self.players[start_index:] + self.players[:start_index]

    def play_round(self):
        self.determine_turn_order()
        for player in self.turn_order:
            print(f"[PLAYER-ORDER] It's Player [{player.player_name}]'s turn")
            self.game_ref.broadcast_message(
                f"[PLAYER-ORDER] It's Player's [{player.player_name}]'s turn "
            )
            if player == self.last_round_winner:
                print(
                    f"[PLAYER-ORDER] Player [{player.player_name}] takes the lead this round, as they played the strongest last round, or distributed the deck"
                )
                self.game_ref.broadcast_message(
                    f"[PLAYER-ORDER] Player {player.player_name} takes the lead this round, as they played the strongest last round, or distributed the deck"
                )
                south_player_socket = self.player_sockets[player.player_name]
                self.game_ref.send_direct_message(
                    f"[CHOICE] It's your turn, choose a number between 1 and {len(player.hand)} ",
                    south_player_socket,
                )
                first_card_number = south_player_socket.recv(BYTESIZE).decode(ENCODER)
                self.game_ref.broadcast_message(
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
                self.game_ref.broadcast_message(
                    f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {CardMapper.get_card_suit(self.trump_card)} alternatively "
                )
            else:
                player_socket = self.player_sockets[player.player_name]
                self.game_ref.send_direct_message(
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

                        self.game_ref.broadcast_message(
                            f"[PLAY] Player [{player.player_name}] played [{CardMapper.get_card(card_number)}]"
                        )
                        self.round_vector.append(card_number)
                        break
                    else:
                        self.game_ref.send_direct_message(
                            f"[INVALID] You must follow suit [{self.round_suit}]. Try again ",
                            player_socket,
                        )
                        print(f"[INVALID]You must follow suit [{self.round_suit}] \n")



    def determine_round_winner(self):
            trump_was_played = any(
                card[0] == self.trump_card_suit for card in self.round_vector
            )
            if trump_was_played:
                trump_cards = [
                    card for card in self.round_vector if card[0] == self.trump_card_suit
                ]
                winner = max(trump_cards)
                winner_index = self.round_vector.index(winner)
                return winner, winner_index
            
            winner = max(self.round_vector)
            print("WINNER IS YIIIIPEEEEE", winner)
            winner_index = self.round_vector.index(winner)
            return winner, winner_index
    

    def get_round_sum(self):
        round_sum = sum(
            (self.card_mapper.get_card_points(card_number)) for card_number in self.round_vector
        )
        return round_sum
from constants import *
from socket import socket, SOL_SOCKET, SO_REUSEADDR
from player import *
from deck import *
import time
from positions import Positions
from random import shuffle,choice


class GameServer:

    def __init__(self):
        self.deck = Deck()
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.player_sockets = {}
        self.players = []
        self.max_players = 4
        self.trump_card = None
        self.trump_card_suit = None
        self.player_sockets = {}
        self.round_counter = 1
        self.last_round_winner = None
        self.round_suit = None
        self.scores = {}
        self.teams = [[], []]
        self.positions = [
            Positions.NORTH,
            Positions.EAST,
            Positions.SOUTH,
            Positions.WEST,
        ]
        self.deck_backup = None

    def shuffle_positions(self):
        shuffle(self.positions)

    def connect_server_socket(self):
        self.server_socket.bind(SERVER_BIND)
        self.server_socket.listen(4)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        print(f"[CONNECTED] Game Server is online")

    def disconnect_server_socket(self):
        self.server_socket.close()
        print(f"[DISCONNECTED] Game Server is offline")

    def broadcast_message(self, message):
        for player_socket in self.player_sockets.values():
            player_socket.sendall((message + "\n").encode(ENCODER))
            time.sleep(0.01)

    def send_direct_message(self, message, player_socket):
        player_socket.sendall((message + "\n").encode(ENCODER))

    def accept_player_sockets(self):
        while len(self.players) < self.max_players:
            player_socket, player_address = self.server_socket.accept()
            player_name = player_socket.recv(BYTESIZE).decode(ENCODER)
            broadcast_message = f"[CONNECTED] Player [{len(self.players)+1}] [{player_name}] has joined the game from {player_address}"
            print(broadcast_message)
            self.broadcast_message(broadcast_message)
            self.player_sockets[player_name] = player_socket
            self.assign_player(player_name)

    def assign_player(self, player_name):
        player = Player(player_name)
        player.position = self.positions[len(self.players)]
        self.players.append(player)
        self.scores[player_name] = 0
        print(
            f"[ANNOUNCEMENT] {player_name} was assigned position [{player.position}] "
        )
        self.broadcast_message(
            f"[ANNOUNCEMENT] {player_name} was assigned position [{player.position}] "
        )

    def assign_teams(self):
        for player in self.players:
            print(
                f"[ANNOUNCEMENT Player {player.player_name} is to the {player.position} "
            )
            if player.position in (Positions.NORTH, Positions.SOUTH):
                self.teams[0].append(player)
                print(
                    f"[ANNOUNCEMENT] {player.player_name} was assigned to the first team "
                )
                self.broadcast_message(
                    f"[ANNOUNCEMENT] {player.player_name} was assigned to the first team "
                )
            else:
                print(
                    f"[ANNOUNCEMENT] {player.player_name} was assigned to the second team "
                )
                self.broadcast_message(
                    f"[ANNOUNCEMENT] {player.player_name} was assigned to the second team "
                )
                self.teams[1].append(player)

    def deal_cards(self):
        for player in self.players:
            set_of_cards = [self.deck.cards.pop(0) for _ in range(10)]
            player.hand = set_of_cards
            player_socket = self.player_sockets[player.player_name]
            data = " ".join(str(card) for card in set_of_cards)
            payload = f"[HAND]{data}\n"
            player_socket.sendall(payload.encode(ENCODER))

    def pick_trump_card(self, choice):
        if choice == "top":
            trump_card = self.deck.cards[0]
        elif choice == "bottom":
            trump_card = self.deck.cards[-1]
        self.trump_card = trump_card
        self.trump_card_suit = CardMapper.get_card_suit(self.trump_card)

    def start_game(self):
        message = "[START] Game has started"
        print(message)
        self.broadcast_message(message)

        # Shuffle deck
        self.broadcast_message("[SHUFFLING] Shuffling deck")
        self.deck.shuffle_deck()
        print(str(self.deck))
        self.broadcast_message("[SHUFFLED] Deck has been shuffled")

        # Shuffle positions & assign teams
        self.shuffle_positions()
        self.assign_teams()

        # Get players by position
        north_player = next(p for p in self.players if p.position == Positions.NORTH)
        west_player = next(p for p in self.players if p.position == Positions.WEST)
        south_player = next(p for p in self.players if p.position == Positions.SOUTH)

        north_socket = self.player_sockets[north_player.player_name]
        west_socket = self.player_sockets[west_player.player_name]

        # NORTH cuts the deck
        self.broadcast_message(
            f"[ANNOUNCEMENT] Player [{north_player.player_name}] (NORTH) will cut the deck"
        )
        print(f"[ANNOUNCEMENT] Player [{north_player.player_name}] (NORTH) will cut the deck")

        self.send_direct_message("[CHOICE] Cut from what index ", north_socket)
        cut_index = int(north_socket.recv(BYTESIZE).decode(ENCODER))

        print(f"[CUT-RECEIVED] Player {north_player.player_name} cut at index [{cut_index}]")
        self.broadcast_message(
            f"[CUT-RECEIVED] Player [{north_player.player_name}] cut the deck at index [{cut_index}]"
        )

        print("Deck before cut:")
        print(str(self.deck))
        self.deck.cut_deck(cut_index)
        print("Deck after cut:")
        print(str(self.deck))

        # WEST picks trump
        self.broadcast_message(
            f"[ANNOUNCEMENT] Player [{west_player.player_name}] (WEST) will pick the trump card"
        )
        print(f"[ANNOUNCEMENT] Player [{west_player.player_name}] (WEST) will pick the trump card")

        self.send_direct_message("[CHOICE] Top or Bottom ", west_socket)
        choice = west_socket.recv(BYTESIZE).decode(ENCODER)
        self.pick_trump_card(choice)

        self.broadcast_message(f"[TRUMP-CARD] This game's trump card is [{self.trump_card}]")
        print(f"[TRUMP-CARD] This game's trump card is {self.trump_card}")

        # Deal cards
        self.deck_backup = self.deck.cards.copy()
        self.deal_cards()

        # SOUTH starts the game (default Sueca rule)
        self.last_round_winner = south_player


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

    def play_round(self):
        message1 = f"[ROUND-START] Round has started"
        print(message1)
        self.broadcast_message(message1)
        message2 = f"[ROUND-COUNTER] Round number {self.round_counter}"
        print(message2)
        self.broadcast_message(message2)
        round_vector = []
        current_player = self.last_round_winner
        start_index = self.players.index(self.last_round_winner)
        turn_order = self.players[start_index:] + self.players[:start_index]
        for player in turn_order:
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
                round_vector.append(first_card_number)
                self.round_suit = round_vector[0][0]
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

        print("[ANNOUNCEMENT Cards played this round ")
        for i, card in enumerate(round_vector, start=1):
            print(
                f"[ANNOUNCEMENT] Player [{self.players[i-1].player_name}] played  [{CardMapper.get_card(card_number)}]"
            )
            self.broadcast_message(
                f"[ANNOUNCEMENT] Player [{self.players[i-1].player_name}] played  [{CardMapper.get_card(card_number)}]"
            )

        def _determine_round_winner():
            trump_was_played = any(
                card[0] == self.trump_card_suit for card in round_vector
            )

            if trump_was_played:
                trump_cards = [
                    card for card in round_vector if card[0] == self.trump_card_suit
                ]
                winner = max(trump_cards)
                winner_index = round_vector.index(winner)
                return winner, winner_index

            winner = max(round_vector)
            print("WINNER IS YIIIIPEEEEE", winner)
            winner_index = round_vector.index(winner)
            return winner, winner_index

        round_winner, winner_index = _determine_round_winner()
        winner_player = self.players[winner_index]
        self.last_round_winner = winner_player

        round_sum = sum(
            (CardMapper.get_card_points(card_number)) for card_number in round_vector
        )
        print(
            f"[ANNOUNCEMENT] Round winner was [{CardMapper.get_card(round_winner)}],  Player [{winner_player.player_name}] wins [{round_sum}] points"
        )
        self.broadcast_message(
            f"[ANNOUNCEMENT] Round winner was [{CardMapper.get_card(round_winner)}],  Player [{winner_player.player_name}] wins [{round_sum}] points."
        )
        self.scores[winner_player.player_name] += round_sum
        self.round_counter += 1

    def end_game(self):
        message = f"[END] Game has ended"
        print(message)
        self.broadcast_message(message)
        for player in self.players:
            player.disconnect_player_socket()
        self.disconnect_server_socket()

    def show_final_scores_and_print_winner(self):
        team1_score = sum(self.scores[player.player_name] for player in self.teams[0])
        team2_score = 120 - team1_score

        print(
            f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0]} & {self.teams[0][1]}] scored [{team1_score}]"
        )
        self.broadcast_message(
            f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0]} & {self.teams[0][1]}] scored [{team1_score}]"
        )
        print(
            f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0]} & {self.teams[1][1]}] scored [{team2_score}]"
        )
        self.broadcast_message(
            f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0]} & {self.teams[1][1]}] scored [{team2_score}]"
        )

        if team1_score > team2_score:
            print("[ANNOUNCEMENT] Team 1 is victorious 🏆")
            self.broadcast_message("[ANNOUNCEMENT] Team 1 is victorious 🏆")
        elif team2_score > team1_score:
            print("[ANNOUNCEMENT] Team 2 is victorious 🏆")
            self.broadcast_message("[ANNOUNCEMENT] Team 2 is victorious 🏆!")

    @staticmethod
    def initialize_server():
        server = GameServer()
        server.connect_server_socket()
        server.accept_player_sockets()
        return server


def main():
    server = GameServer.initialize_server()
    server.start_game()
    for i in range(10):
        server.play_round()
    server.show_final_scores_and_print_winner()
    server.end_game()


if __name__ == "__main__":
    main()

from constants import *
from socket import socket, SOL_SOCKET, SO_REUSEADDR
from player import *
from deck import *
import time
from positions import Positions
from random import shuffle, choice
from round_manager import RoundManager
from game_logger import GameLogger


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
        self.game_logger = GameLogger()

    def shuffle_positions(self):
        shuffle(self.positions)

    def connect_server_socket(self):
        self.server_socket.bind(SERVER_BIND)
        self.server_socket.listen(4)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.game_logger.log_info(f"[CONNECTED] Game Server is online")

    def disconnect_server_socket(self):
        self.server_socket.close()
        self.game_logger.log_info(f"[DISCONNECTED] Game Server is offline")

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
            self.game_logger.log_info(
                f"[CONNECTED] Player [{len(self.players)+1}] [{player_name}] has joined the game from {player_address}"
            )
            self.broadcast_message(f"[CONNECTED] Player [{len(self.players)+1}] [{player_name}] has joined the game from {player_address}")
            self.player_sockets[player_name] = player_socket
            self.assign_player(player_name)

    def assign_player(self, player_name):
        player = Player(player_name)
        player.position = self.positions[len(self.players)]
        self.players.append(player)
        self.scores[player_name] = 0
        
        self.game_logger.log_info(f"[ANNOUNCEMENT] {player_name} was assigned position [{player.position}] ")
        
        self.broadcast_message(
            f"[ANNOUNCEMENT] {player_name} was assigned position [{player.position}] "
        )

    def assign_teams(self):
        for player in self.players:
            self.game_logger.log_info(f"[ANNOUNCEMENT Player {player.player_name} is to the {player.position} ")
            
            if player.position in (Positions.NORTH, Positions.SOUTH):
                self.teams[0].append(player)
                self.game_logger.log_info(
                    f"[ANNOUNCEMENT] {player.player_name} was assigned to the first team "
                )
                self.broadcast_message(
                    f"[ANNOUNCEMENT] {player.player_name} was assigned to the first team "
                )
            else:
                self.game_logger.log_info(
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
        self.game_logger.log_info("[START] Game has started")
        self.broadcast_message("[START] Game has started")

        # Shuffle deck
        self.broadcast_message("[SHUFFLING] Shuffling deck")
        self.deck.shuffle_deck()
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

        self.send_direct_message("[CHOICE] Cut from what index ", north_socket)
        cut_index = int(north_socket.recv(BYTESIZE).decode(ENCODER))

        
        self.game_logger.log_info(f"[CUT-RECEIVED] Player {north_player.player_name} cut at index [{cut_index}]")
        
        self.broadcast_message(
            f"[CUT-RECEIVED] Player [{north_player.player_name}] cut the deck at index [{cut_index}]"
        )

        self.deck.cut_deck(cut_index)

        # WEST picks trump
        self.broadcast_message(
            f"[ANNOUNCEMENT] Player [{west_player.player_name}] (WEST) will pick the trump card"
        )
        
        self.game_logger.log_info(f"[ANNOUNCEMENT] Player [{west_player.player_name}] (WEST) will pick the trump card")
        

        self.send_direct_message("[CHOICE] Top or Bottom ", west_socket)
        choice = west_socket.recv(BYTESIZE).decode(ENCODER)
        self.pick_trump_card(choice)

        self.broadcast_message(
            f"[TRUMP-CARD] This game's trump card is [{CardMapper.get_card(self.trump_card)}]"
        )
        self.game_logger.log_info(
            f"[TRUMP-CARD] This game's trump card is {CardMapper.get_card(self.trump_card)}"
        )

        # Deal cards
        self.deck_backup = self.deck.cards.copy()
        self.deal_cards()

        # SOUTH starts the game (default Sueca rule)
        self.last_round_winner = south_player

    def compute_round(self):
        round_manager = RoundManager(
            self,
            self.players,
            self.player_sockets,
            self.last_round_winner,
            CardMapper(),
            self.trump_card_suit,
            self.trump_card,
        )
        round_manager.play_round()
        round_winner, winner_index = round_manager.determine_round_winner()
        winner_player = self.players[winner_index]
        self.last_round_winner = winner_player
        round_sum = round_manager.get_round_sum()
        self.game_logger.log_info(
            f"[ANNOUNCEMENT] Round winner was [{CardMapper.get_card(round_winner)}],  Player [{winner_player.player_name}] wins [{round_sum}] points"
        )
        self.broadcast_message(
            f"[ANNOUNCEMENT] Round winner was [{CardMapper.get_card(round_winner)}],  Player [{winner_player.player_name}] wins [{round_sum}] points."
        )
        self.scores[winner_player.player_name] += round_sum
        self.round_counter += 1

    def end_game(self):
        self.game_logger.log_info(f"[END] Game has ended")
        self.broadcast_message(f"[END] Game has ended")
        for player in self.players:
            player.disconnect_player_socket()
        self.disconnect_server_socket()

    def show_final_scores_and_print_winner(self):
        team1_score = sum(self.scores[player.player_name] for player in self.teams[0])
        team2_score = 120 - team1_score

        self.game_logger.log_info(
            f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0]} & {self.teams[0][1]}] scored [{team1_score}]"
        )
        self.broadcast_message(
            f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0]} & {self.teams[0][1]}] scored [{team1_score}]"
        )
        self.game_logger.log_info(
            f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0]} & {self.teams[1][1]}] scored [{team2_score}]"
        )
        self.broadcast_message(
            f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0]} & {self.teams[1][1]}] scored [{team2_score}]"
        )

        if team1_score > team2_score:
            self.game_logger.log_info("[ANNOUNCEMENT] Team 1 is victorious 🏆")
            self.broadcast_message("[ANNOUNCEMENT] Team 1 is victorious 🏆")
        elif team2_score > team1_score:
            self.game_logger.log_info("[ANNOUNCEMENT] Team 2 is victorious 🏆")
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
        server.compute_round()
    server.show_final_scores_and_print_winner()
    server.end_game()


if __name__ == "__main__":
    main()

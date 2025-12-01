from socket import *
from src.constants import *
import time
from threading import Thread, Lock
from src.card_mapper import CardMapper


class Player:
    """AI Player implementation based on the logic of the new Player class."""

    def __init__(self, player_name):
        self.player_name = player_name
        self.player_socket = socket(AF_INET, SOCK_STREAM)
        self.running = True
        self.hand = []
        self.print_mutex = Lock()
        self.turn_mutex = Lock()
        self.position = None

    def send_response(self, response):
        """Sends a given message via socket."""
        self.player_socket.send(response.encode(ENCODER))

    def send_card(self, card):
        """Sends a given card via socket."""
        self.player_socket.send(str(card).encode(ENCODER))

    def disconnect_player_socket(self):
        """Disconnects the player socket."""
        self.running = False
        self.player_socket.close()
        print(f"[DISCONNECTED] [{self.player_name}]")

    def connect_player_socket(self, server_ip=None):
        """Connects the player socket to the game server."""
        target = CONNECT_INFO if server_ip is None else (server_ip, PORT)
        try:
            self.player_socket.connect(target)
            print(f"[CONNECTED] [NAME:{self.player_name}] [TO:{target[0]}:{target[1]}]")
        except Exception as e:
            print(f"[ERROR] Could not connect to {target}: {e}")
            raise

    def __repr__(self):
        return f"[PLAYER-INFORMATION] [NAME:{self.player_name}] [POSITION:{self.position}] "

    def handle_cut_deck_request(self):
        """AI automatically chooses a cut index."""
        with self.print_mutex:
            print("[AI] Handling cut request → sending '10'")
        self.send_response("10")

    def handle_trump_card_request(self):
        """AI automatically chooses 'top'."""
        with self.print_mutex:
            print("[AI] Handling trump request → sending 'top'")
        self.send_response("top")

    def receive_cards(self, message):
        """Receives a space-separated list of integers."""
        data = message[len("[HAND]"):]
        split_cards = data.split(" ")
        self.hand = [int(card) for card in split_cards if card]
        self.hand.sort()
        print("[HAND-RECEIVED] Hand received")

    def handle_turn(self, sock_file):
        """AI chooses cards automatically based on validity."""
        while True:
            sorted_hand = sorted(self.hand, key=CardMapper.get_card_points)

            self.turn_mutex.acquire()

            self.print_mutex.acquire()
            print("[AI] It's my turn. Current hand:")
            self.view_hand_statically()
            self.print_mutex.release()

            for card_index, card in enumerate(sorted_hand):
                self.send_card(card)
                server_response = sock_file.readline().strip()
                self.print_mutex.acquire()
                print(f"[AI] Trying card {CardMapper.get_card(card)} → Server: {server_response}")
                self.print_mutex.release()
                if not server_response.startswith("[INVALID]"):
                    print(f"[AI] Played card: {CardMapper.get_card(card)}")
                    self.hand.remove(card)
                    self.turn_mutex.release()
                    return

            self.print_mutex.acquire()
            print("[AI ERROR] No valid card found!")
            self.print_mutex.release()
            self.turn_mutex.release()
            return

    def listen(self):
        """Listens for server feedback."""
        sock_file = self.player_socket.makefile("r")
        while self.running:
            message = sock_file.readline()
            if not message:
                break

            message = message.strip()

            if message == "[CHOICE] Cut from what index":
                self.handle_cut_deck_request()

            elif message == "[CHOICE] Top or Bottom":
                self.handle_trump_card_request()

            elif message.startswith("[HAND]"):
                self.receive_cards(message)

            elif message.startswith("[CHOICE] It's your turn"):
                self.handle_turn(sock_file)

            else:
                with self.print_mutex:
                    print(f"{message}\n")

    def view_hand_continuously(self):
        """Prints the players hand every 8 seconds."""
        while self.running:
            with self.print_mutex:
                if len(self.hand) == 0:
                    print("[EMPTY-HAND] Waiting for cards...")
                else:
                    print("[VIEW-HAND] Your hand\n")
                    sorted_hand = sorted(self.hand, key=CardMapper.get_card_points)
                    hand_str = "    ".join(CardMapper.get_card(card) for card in sorted_hand)
                    print(hand_str)
            time.sleep(8)

    def view_hand_statically(self):
        """Prints the player's hand once."""
        if len(self.hand) == 0:
            print("[EMPTY-HAND] Waiting for cards...")
        else:
            print("[VIEW-HAND] Your hand\n")
            sorted_hand = sorted(self.hand, key=CardMapper.get_card_points)
            hand_str = "    ".join(CardMapper.get_card(card) for card in sorted_hand)
            print(hand_str)

    @staticmethod
    def initialize_player():
        """Initialize player + auto-connect."""
        name = input("[REGISTER] Enter your player name: ")
        player = Player("AI PLAYER: " + name)

        server_ip = input("[CONNECT] Enter server IP (leave blank for default): ").strip()
        player.connect_player_socket(server_ip if server_ip else None)

        player.send_response(name)
        return player


def main():
    player = Player.initialize_player()
    listen_thread = Thread(target=player.listen, daemon=True)
    view_hand_thread = Thread(target=player.view_hand_continuously, daemon=True)

    listen_thread.start()
    view_hand_thread.start()

    listen_thread.join()
    view_hand_thread.join()
    player.disconnect_player_socket()


if __name__ == "__main__":
    main()

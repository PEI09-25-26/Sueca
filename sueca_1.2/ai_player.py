from socket import *
from constants import *
import json
import time
from threading import Thread, Lock


class Player:
    def __init__(self, player_name):
        self.player_name = player_name
        self.player_socket = socket(AF_INET, SOCK_STREAM)
        self.running = True
        self.hand = []
        self.print_mutex = Lock()
        self.turn_mutex = Lock()
        self.position = None

    def send_response(self, response):
        self.player_socket.send(response.encode(ENCODER))

    def disconnect_player_socket(self):
        self.running = False
        self.player_socket.close()
        print(f"[DISCONNECTED] [{self.player_name}]")

    def connect_player_socket(self, server_ip=None):
        """Connect to the game server.

        If `server_ip` is provided it will connect to (server_ip, PORT).
        Otherwise it will use the default `CONNECT_INFO` from `constants.py`.
        """
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
        self.print_mutex.acquire()
        self.send_response("10")
        self.print_mutex.release()

    def handle_trump_card_request(self):
        self.print_mutex.acquire()
        self.send_response("top")
        self.print_mutex.release()

    def receive_cards(self, message):
        data = message[len("[HAND]") :]
        card_strings = json.loads(data)
        self.hand = card_strings
        print("[HAND-RECEIVED] Hand received")

    def handle_turn(self, sock_file):
        while True:
            self.turn_mutex.acquire()
            self.print_mutex.acquire()
            print("[AI] It's my turn. Current hand:")
            self.view_hand_statically()
            self.print_mutex.release()
            card = self.hand[0]
            card_string = json.dumps(card)
            self.send_response(card_string)
            server_response = sock_file.readline().strip()
            self.print_mutex.acquire()
            print(f"[AI] Server response to first choice: {server_response}")
            self.print_mutex.release()
            if not server_response.startswith("[INVALID]"):
                print(f"[AI] Played card: {card}")
                self.hand.pop(0)
                self.turn_mutex.release()
                return
            for card_index, card in enumerate(self.hand[1:], start=1):
                card_string = json.dumps(card)
                self.send_response(card_string)
                server_response = sock_file.readline().strip()
                self.print_mutex.acquire()
                print(f"[AI] Trying card {card} → Server: {server_response}")
                self.print_mutex.release()
                if server_response.startswith("[INVALID]"):
                    continue
                print(f"[AI] Played card: {card}")
                self.hand.pop(card_index)
                self.turn_mutex.release()
                return
            print("[AI ERROR] No valid card found!")
            self.turn_mutex.release()

    def __repr__(self):
        return f"[PLAYER-INFO] [{self.player_name}]"

    def listen(self):
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
                self.print_mutex.acquire()
                print(f"{message}\n")
                self.print_mutex.release()

    def view_hand_continuously(self):
        while self.running:
            if len(self.hand) == 0:
                self.print_mutex.acquire()
                print(
                    f"[EMPTY-HAND] Your hand is empty, waiting for cards to be distributed "
                )
                self.print_mutex.release()
            else:
                self.print_mutex.acquire()
                print(f"[VIEW-HAND] Your hand \n")
                hand_str = "    ".join(str(card) for card in self.hand)
                print(hand_str)
                self.print_mutex.release()
            time.sleep(8)

    def view_hand_statically(self):
        if len(self.hand) == 0:
            print(
                f"[EMPTY-HAND] Your hand is empty, waiting for cards to be distributed "
            )
        else:
            print(f"[VIEW-HAND] Your hand \n")
            hand_str = "    ".join(str(card) for card in self.hand)
            print(hand_str)

    @staticmethod
    def initialize_player():
        name = input("[REGISTER] Enter your player name: ")
        player = Player("AI PLAYER: " + name)
        server_ip = input(
            "[CONNECT] Enter server IP (leave blank for default): "
        ).strip()
        player.connect_player_socket(server_ip if server_ip != "" else None)
        player.send_response(name)
        return player


def main():
    player = Player.initialize_player()
    listen_thread = Thread(target=player.listen, daemon=True)
    view_hand_continuously_thread = Thread(
        target=player.view_hand_continuously, daemon=True
    )
    listen_thread.start()
    view_hand_continuously_thread.start()
    listen_thread.join()
    view_hand_continuously_thread.join()


if __name__ == "__main__":
    main()

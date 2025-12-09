from socket import *
from src.constants import *
import time
from threading import Thread, Lock
from src.card_mapper import CardMapper



class Player:
    """This class represents a player """
    def __init__(self, player_name):
        self.player_name = player_name
        self.player_socket = socket(AF_INET, SOCK_STREAM)
        self.running = True
        self.hand = []
        self.print_mutex = Lock()
        self.turn_mutex = Lock()
        self.position = None
        self.trump_suit = None
        self.round_suit = None
        self.team1 = []
        self.team2 = []
        self.partner_name = None
        self.plays_in_trick = 0


    def send_response(self, response):
        """Sends a given message via socket. """
        self.player_socket.send(response.encode(ENCODER))

    def send_card(self, card):
        """Sends a given card via socket. """
        self.player_socket.send(str(card).encode(ENCODER))

    def disconnect_player_socket(self):
        """Disconnects the player socket. """
        self.running = False
        self.player_socket.close()
        print(f"[DISCONNECTED] [{self.player_name}]")

    def connect_player_socket(self, server_ip=None):
        """Connects the player socket to the game server. """
        target = CONNECT_INFO if server_ip is None else (server_ip, PORT)
        try:
            self.player_socket.connect(target)
            print(f"[CONNECTED] [NAME:{self.player_name}] [TO:{target[0]}:{target[1]}]")
        except Exception as e:
            print(f"[ERROR] Could not connect to {target}: {e}")
            raise

    def __repr__(self):
        return f"[PLAYER-INFORMATION] [NAME:{self.player_name}] [POSITION:{self.position}] "
    
    def handle_teams(self, message):
        """Player receives info and learns about the teams and its teammate"""
        p_name = message[len("[ANNOUNCEMENT] "):].split(" was ")[0]
        if message.__contains__("first"):
            self.team1.append(p_name)
        else:
            self.team2.append(p_name)
        if self.player_name in self.team1 and len(self.team1) == 2:
            self.partner_name = next(p for p in self.team1 if p != self.player_name)
        elif self.player_name in self.team2 and len(self.team2) == 2:
            self.partner_name = next(p for p in self.team2 if p != self.player_name)

    def handle_cut_deck_request(self):
        """Handles cut deck request.

        Asks the user for a number between 1 and 40.

        Sends the response via socket, given it's validation. 
        """
        with self.print_mutex:
            while True:
                try:
                    raw = input("Enter cut index (1–40): ").strip()
                    cut_index = int(raw)
                    
                    if 1 <= cut_index <= 40:
                        self.send_response(str(cut_index))
                        break
                    else:
                        print("[INVALID] Cut index must be between 1 and 40.")
                
                except ValueError:
                    print("[ERROR] Please enter a valid number.")


    def handle_trump_card_request(self):
        """Handles trump card request.

        Prompts choice to the user. 

        Sends it via socket, given it's validation. """
        with self.print_mutex:
            while True:
                choice = input("[CHOICE] Choose 'top' or 'bottom': ").strip().lower()

                if choice in ("top", "bottom"):
                    self.send_response(choice)
                    break
                else:
                    print("[INVALID] Choice must be 'top' or 'bottom'.")

    def handle_trump_card_set(self, message):
        """Receives and stores the trump suit in a variable"""
        start = message.index("[", len("[TRUMP-CARD]"))
        end = message.index("]", start)
        trump_card = message[start+1:end]
        self.trump_suit = trump_card[-1:]

    def handle_round_suit_set(self, message):
        """Receives and stores the current round's suit in a variable"""
        prefix = "[ANNOUNCEMENT] This round's suit is "
        suit = message[len(prefix):].rstrip(".")
        self.round_suit = suit[0]

    def receive_cards(self, message):
        """Receives a set of cards. """
        data = message[len("[HAND]") :]
        data_split = data.split(" ")
        self.hand = [int(card) for card in data_split if card]
        self.hand.sort()
        print("[HAND-RECEIVED] Hand received")
    
    def handle_play_count(self, message):
        if self.plays_in_trick == 3:
            self.plays_in_trick = 0
        else:
            self.plays_in_trick += 1

    def handle_turn(self, sock_file):
        """Handles the player's turn.

        Asks the user to index the card they wish to play. 

        Sends it via socket.

        Pops it of the player's hand. 
        """
        while True:
            sorted_hand = sorted(self.hand, key=CardMapper.get_card_points)
            self.turn_mutex.acquire()
            self.print_mutex.acquire()
            self.view_hand_statically()
            while True:
                attempt_str = input(f"[CHOICE] Pick a card number [1-{len(self.hand)}]: ") 
                if not attempt_str:
                    print("[ERROR] Please enter a card index.")
                    continue
                if not attempt_str.isdigit():
                    print("[ERROR] Input must be a number. Please try again.")
                    continue
                card_number = int(attempt_str) 
                if card_number not in range(1, len(self.hand) + 1): 
                    print(f"[ERROR] Card index needs to be between 1 and {len(self.hand)}. Please try again.")
                    continue
                card_index = card_number - 1 
                break
            self.print_mutex.release()
            card = sorted_hand[card_index]
            self.send_card(card)
            server_response = sock_file.readline().strip()
            self.print_mutex.acquire()
            print(server_response)
            self.print_mutex.release()
            self.turn_mutex.release()
            if server_response.startswith("[INVALID]"):
                continue
            else:
                self.hand.pop(card_index)
                self.round_suit = None
                break

    def __repr__(self):
        return f"[PLAYER-INFO] [{self.player_name}]"

    def listen(self):
        """Listens for server feedback.

        Responsible for handing requests and server-related interactions. 
        """
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
            
            elif message.startswith("[TRUMP-CARD]"):
                self.handle_trump_card_set(message)

            elif message.startswith("[ANNOUNCEMENT] This round's suit is"):
                self.handle_round_suit_set(message)

            elif message.startswith(f"[ANNOUNCEMENT]") and message.__contains__("was assigned to the"):
                self.handle_teams(message)

            elif message.startswith(f"[PLAY]"):
                self.handle_play_count(message)

            else:
                self.print_mutex.acquire()
                print(f"{message}\n")
                self.print_mutex.release()

    def view_hand_continuously(self):
        """Prints the players hand every 8 seconds. """
        while self.running:
            if len(self.hand) == 0:
                with self.print_mutex:
                    print(
                        f"[EMPTY-HAND] Your hand is empty, waiting for cards to be distributed "
                    )
            else:
                with self.print_mutex:
                    print(f"[VIEW-HAND] Your hand \n")
                    sorted_hand = sorted(self.hand, key=CardMapper.get_card_points)
                    hand_str = "    ".join(
                        CardMapper.get_card(card_number) for card_number in sorted_hand
                    )
                    print(hand_str)
            time.sleep(8)

    def view_hand_statically(self):
        """Prints the players hand once. """
        if len(self.hand) == 0:
            print(
                f"[EMPTY-HAND] Your hand is empty, waiting for cards to be distributed "
            )
        else:
            print(f"[VIEW-HAND] Your hand \n")
            sorted_hand = sorted(self.hand, key=CardMapper.get_card_points)
            hand_str = "    ".join(
                CardMapper.get_card(card_number) for card_number in sorted_hand
            )
            print(hand_str)

    @staticmethod
    def initialize_player():
        """Factory method.

        Responsible for initializing a player object.

        Prompts the user for name.
        
        Connects the player socket to the server. """
        while True:
            name = input("[REGISTER] Enter your player name: ")
            if not name:
                print("[ERROR] Empty names are not permitted, try again.")
                continue
            player = Player(name)
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
    player.disconnect_player_socket()


if __name__ == "__main__":
    main()

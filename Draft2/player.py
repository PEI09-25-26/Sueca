from socket import *
from constants import *
import json

class Player:
    def __init__(self,player_name):
        self.player_name = player_name
        self.player_socket = socket(AF_INET,SOCK_STREAM)
        self.running = True
        self.hand = []

    def send_response(self,response):
        self.player_socket.send(response.encode(ENCODER))

    def disconnect_player_socket(self):
        self.running = False
        self.player_socket.close()
        print(f"[DISCONNECTED] [{self.player_name}] \n",flush=True)

    def connect_player_socket(self):
        self.player_socket.connect(CONNECT_INFO)
        print(f"[CONNECTED] [NAME:{self.player_name}] \n",flush=True)

    def __repr__(self):
        return f"[PLAYER-INFORMATION] [NAME:{self.player_name}] "
    
    def listen(self):
        sock_file = self.player_socket.makefile('r') 
        while self.running:
            message = sock_file.readline()
            if not message:
                break

            message = message.strip()
            print(f"{message}\n", flush=True)

            # --- handle commands ---
            if message == "[CHOICE] Cut from what index":
                cut_index = input("Enter cut index: ")
                self.send_response(cut_index)

            elif message == "[CHOICE] Top or Bottom":
                choice = input("Choose top or bottom: ")
                self.send_response(choice)

            elif message.startswith("[HAND]"):
                data = message[len("[HAND]"):]
                card_strings = json.loads(data)
                self.hand = card_strings
                print("[HAND-RECEIVED] Hand received")
                self.view_hand()
                continue

            elif message.startswith("[CHOICE] It's your turn"):
                while True:
                    self.view_hand()

                    card_index = int(input(f"[CHOICE] Pick a card number [1-{len(self.hand)}]: ")) - 1
                    card = self.hand[card_index]
                    card_string = json.dumps(card)
                    self.send_response(card_string)

                    server_response = sock_file.readline().strip()
                    print(server_response)

                    if server_response.startswith("[INVALID]"):
                        print("Invalid card. Try again.")
                        continue  
                    else:
                        self.hand.pop(card_index)
                        break


            elif message == "[ROUND-START] Round has started \n":
                self.view_hand()


            


    def __repr__(self):
        return f"[PLAYER-INFO] [{self.player_name}] \n"

    def receive_cards(self,set_of_cards):
        self.hand = set_of_cards

    def view_hand(self):
        print(f"[VIEW-HAND] Your hand \n",flush=True)
        hand_str = '    '.join(str(card) for card in self.hand) + "\n"
        print(hand_str,flush=True)


def main():
    name = input("[REGISTER] Enter your player name: ")
    player = Player(name)
    player.connect_player_socket()
    player.send_response(name)
    player.listen()

if __name__ == "__main__":
    main()
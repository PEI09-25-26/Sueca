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
        print(f"[DISCONNECTED] [{self.player_name}] ")

    def connect_player_socket(self):
        self.player_socket.connect(CONNECT_INFO)
        print(f"[CONNECTED] [NAME:{self.player_name}] ")

    def __repr__(self):
        return f"[PLAYER-INFORMATION] [NAME:{self.player_name}] "
    
    def listen(self):
        while self.running:
            message = self.player_socket.recv(BYTESIZE).decode(ENCODER)
            if not message:
                break
            print(message)

            if message=="[CHOICE] Cut from what index ":
                cut_index = input("")
                self.send_response(cut_index)

            if message=="[CHOICE] Top or Bottom ":
                choice = input("")
                self.send_response(choice)

            if message.startswith("[HAND]"):
                data = message[len("[HAND]"):] 
                card_strings = json.loads(data)
                self.hand = card_strings
                print("[HAND-RECEIVED] Hand received ")
                self.view_hand()
                continue

            if message == f"[CHOICE] It's your turn, choose a number between 1 and 10 ":
                card_index = int(input(""))
                card = self.hand.pop(card_index)
                card_string = json.dumps(card)
                self.send_response(card_string)

    def __repr__(self):
        return f"[PLAYER-INFO] [{self.player_name}] "

    def receive_cards(self,set_of_cards):
        self.hand = set_of_cards

    def view_hand(self):
        print(f"[VIEW-HAND] Your hand ")
        hand_str = '    '.join(str(card) for card in self.hand)  
        print(hand_str)


def main():
    name = input("[REGISTER] Enter your player name: ")
    player = Player(name)
    player.connect_player_socket()
    player.send_response(name)
    player.listen()

if __name__ == "__main__":
    main()
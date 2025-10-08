from socket import *
from constants import *
import json

class Player:
    def __init__(self,player_name):
        self.player_name = player_name
        self.player_socket = socket(AF_INET,SOCK_STREAM)
        self.running = True

    def send_name(self,name):
        self.player_socket.send(name.encode(ENCODER))

    def disconnect_player_socket(self):
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



def main():
    name = input("[REGISTER] Enter your player name: ")
    player = Player(name)
    player.connect_player_socket()
    player.send_name(name)
    player.listen()       

if __name__ == "__main__":
    main()
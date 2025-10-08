from constants import *
from socket import *
from player import *
from deck import *
import json

class GameServer:

    def __init__(self):
        self.deck = Deck()
        self.server_socket = socket(AF_INET,SOCK_STREAM)
        self.player_sockets = {}
        self.players = []
        self.max_players = 4

    def connect_server_socket(self):
        self.server_socket.bind(CONNECT_INFO)
        self.server_socket.listen(4)
        print(f"[CONNECTED] Game Server is online ")

    def disconnect_server_socket(self):
        self.server_socket.close()
        print(f"[DISCONNECTED] Game Server is offline ")


    def broadcast_message(self,message):
        for player_socket in self.player_sockets.values():
            player_socket.send(message)

    def accept_player_sockets(self):
        while len(self.players)<self.max_players:
            player_socket, player_address = self.server_socket.accept()
            player_name = player_socket.recv(BYTESIZE).decode(ENCODER)

            broadcast_message = f"[CONNECTED] Player [{len(self.players)+1}] [{player_name}] has joined the game from {player_address} ".encode(ENCODER)
            print(broadcast_message.decode(ENCODER))

            self.broadcast_message(broadcast_message)
            
            self.player_sockets[player_address] = player_socket
            self.players.append(Player(player_name))

    def start_game(self):
        message = f"[START] Game has started "
        print(message)
        self.broadcast_message(message.encode(ENCODER))


    def end_game(self):
        message = f"[END] Game has ended"
        print(message)
        self.broadcast_message(message.encode(ENCODER))
        
def main():
    server = GameServer()
    server.connect_server_socket()
    server.accept_player_sockets()
    server.start_game()
    server.end_game()
    server.disconnect_server_socket()
    
if __name__ == "__main__":
    main()
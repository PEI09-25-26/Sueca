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
        self.trump_card = None
        self.trump_card_suit = None
        self.player_sockets = {

        }
        self.round_counter = 1
        self.last_round_winner = None
        self.round_suit = None

    def connect_server_socket(self):
        self.server_socket.bind(CONNECT_INFO)
        self.server_socket.listen(4)
        print(f"[CONNECTED] Game Server is online ")

    def disconnect_server_socket(self):
        self.server_socket.close()
        print(f"[DISCONNECTED] Game Server is offline ")


    def broadcast_message(self,message):
        for player_socket in self.player_sockets.values():
            player_socket.send(message.encode(ENCODER))

    def send_direct_message(self,message,player_socket):
        player_socket.send(message.encode(ENCODER))

    def accept_player_sockets(self):
        while len(self.players)<self.max_players:
            player_socket, player_address = self.server_socket.accept()
            player_name = player_socket.recv(BYTESIZE).decode(ENCODER)

            broadcast_message = f"[CONNECTED] Player [{len(self.players)+1}] [{player_name}] has joined the game from {player_address} "
            print(broadcast_message)

            self.broadcast_message(broadcast_message)
            
            self.player_sockets[player_name] = player_socket
            self.players.append(Player(player_name))

    def distribute_cards(self):
        for player in self.players:
            set_of_cards = [self.deck.pile.pop(0) for _ in range(10)]
            player_socket = self.player_sockets[player.player_name]
            card_strings = [str(card) for card in set_of_cards]
            data = json.dumps(card_strings)
            payload = "[HAND]" + data
            player_socket.sendall(payload.encode(ENCODER))

    def pick_trump_card(self,choice):
        if choice == "top":
            trump_card = self.deck.pile[0]
        elif choice == "bottom":
            trump_card = self.deck.pile[-1]
        self.trump_card=trump_card
        self.trump_card_suit=self.trump_card.suit


    def start_game(self):
        message = f"[START] Game has started "
        print(message)
        self.broadcast_message(message)
        self.broadcast_message("[SHUFFLING] Shuffling deck ")
        self.deck.shuffle_deck()
        print(str(self.deck))
        self.broadcast_message(str(self.deck))
        self.broadcast_message("[SHUFFLED] Deck has been shuffled ")
        self.broadcast_message("[CUTTING] Cutting deck ")
        print("[CUTTING] Cutting deck ")
        first_player_socket = list(self.player_sockets.values())[0]
        self.broadcast_message(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to cut the deck ")
        print(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to cut the deck ")
        self.send_direct_message("[CHOICE] Cut from what index ",first_player_socket)
        cut_index = int(first_player_socket.recv(BYTESIZE).decode(ENCODER))
        print(f"[CUT-RECEIVED] Player cut the deck at index [{cut_index}]")
        self.broadcast_message(f"[CUT-RECEIVED] Player cut the deck at index [{cut_index}]")
        print("Deck before the cut:")
        print(str(self.deck))
        self.deck.cut_deck(cut_index)
        print("Deck after the cut:")
        print(str(self.deck))
        self.broadcast_message(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to pick trump card from the top or the bottom of the deck ")
        print(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to pick the trump card from the top or the bottom of the deck ")
        self.send_direct_message("[CHOICE] Top or Bottom ",first_player_socket)
        choice = first_player_socket.recv(BYTESIZE).decode(ENCODER)
        self.pick_trump_card(choice)
        self.broadcast_message(f"[TRUMP-CARD] This game's trump card is [{self.trump_card}] ")
        print(f"[TRUMP-CARD This game's trump card is {self.trump_card} ")
        self.distribute_cards()
        self.last_round_winner=self.players[0]


   


    def play_round(self):
        message1 = f"[ROUND-START] Round has started "
        print(message1)
        self.broadcast_message(message1)
        message2 = f"[ROUND-COUNTER] Round number {self.round_counter} "
        print(message2)
        self.broadcast_message(message2)
        round_vector = []
        current_player = self.last_round_winner
        start_index = self.players.index(self.last_round_winner)
        turn_order = self.players[start_index:] + self.players[:start_index]
        for player in turn_order:
            print(f"[PLAYER-ORDER] It's Player [{player.player_name}]'s turn ")
            self.broadcast_message(f"[PLAYER-ORDER] It's Player's [{player.player_name}]'s turn ")
            if player == self.last_round_winner:
                print(f"[PLAYER-ORDER] Player [{player.player_name}] takes the lead this round, as they played the strongest last round, or distributed the deck ")
                self.broadcast_message(f"[PLAYER-ORDER] Player {player.player_name} takes the lead this round, as they played the strongest last round, or distributed the deck ")
                first_player_socket = self.player_sockets[player.player_name]
                self.send_direct_message("[CHOICE] It's your turn, choose a number between 1 and 10 ",first_player_socket)
                first_card_json = first_player_socket.recv(BYTESIZE).decode(ENCODER)
                first_card_str = json.loads(first_card_json)
                first_card = Card.from_string(first_card_str)
                print(first_card)
                round_vector.append(first_card)
                self.round_suit = round_vector[0].suit
                print(f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {self.trump_card.suit}  alternatively ")
                self.broadcast_message(f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {self.trump_card.suit}  alternatively ")

            else:
                pass

    def end_game(self):
        message = f"[END] Game has ended "
        print(message)
        self.broadcast_message(message)
        self.disconnect_server_socket()


def main():
    server = GameServer()
    server.connect_server_socket()
    server.accept_player_sockets()
    server.start_game()
    for i in range(10):
        server.play_round()
    server.end_game()
    
    
if __name__ == "__main__":
    main()
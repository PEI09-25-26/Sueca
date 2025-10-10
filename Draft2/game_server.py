from constants import *
from socket import *
from player import *
from deck import *
import json
import time

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
        self.scores = {

        }
        self.teams = []

    def connect_server_socket(self):
        self.server_socket.bind(CONNECT_INFO)
        self.server_socket.listen(4)
        print(f"[CONNECTED] Game Server is online \n",flush=True)

    def disconnect_server_socket(self):
        self.server_socket.close()
        print(f"[DISCONNECTED] Game Server is offline \n",flush=True)


    def broadcast_message(self, message):
        for player_socket in self.player_sockets.values():
            player_socket.sendall((message + "\n").encode(ENCODER))
            time.sleep(0.05)


    
    def send_direct_message(self, message, player_socket):
        player_socket.sendall((message + "\n").encode(ENCODER))


    def accept_player_sockets(self):
        while len(self.players)<self.max_players:
            player_socket, player_address = self.server_socket.accept()
            player_name = player_socket.recv(BYTESIZE).decode(ENCODER)

            broadcast_message = f"[CONNECTED] Player [{len(self.players)+1}] [{player_name}] has joined the game from {player_address} \n"
            print(broadcast_message,flush=True)

            self.broadcast_message(broadcast_message)
            
            self.player_sockets[player_name] = player_socket
            self.players.append(Player(player_name))
            self.scores[player_name] = 0
        
        self.teams.append([self.players[0],self.players[2]])
        self.teams.append([self.players[1],self.players[3]])


    def distribute_cards(self):
        for player in self.players:
            set_of_cards = [self.deck.pile.pop(0) for _ in range(10)]
            player_socket = self.player_sockets[player.player_name]
            card_strings = [str(card) for card in set_of_cards]
            data = json.dumps(card_strings)
            payload = "[HAND]" + data + "\n"
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
        print("[SHUFFLING] Shuffling deck ")
        self.broadcast_message("[SHUFFLING] Shuffling deck ")
        self.deck.shuffle_deck()
        print(str(self.deck))
        self.broadcast_message("[SHUFFLED] Deck has been shuffled ")
        self.broadcast_message("[CUTTING] Cutting deck ")
        print("[CUTTING] Cutting deck \n",flush=True)
        first_player_socket = list(self.player_sockets.values())[0]
        self.broadcast_message(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to cut the deck ")
        print(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to cut the deck \n,flush=True")
        self.send_direct_message("[CHOICE] Cut from what index ",first_player_socket)
        cut_index = int(first_player_socket.recv(BYTESIZE).decode(ENCODER))
        print(f"[CUT-RECEIVED] Player cut the deck at index [{cut_index}] \n",flush=True)
        self.broadcast_message(f"[CUT-RECEIVED] Player cut the deck at index [{cut_index}]")
        print("Deck before the cut \n",flush=True)
        print(str(self.deck))
        self.deck.cut_deck(cut_index)
        print("Deck after the cut ",flush=True)
        print(str(self.deck))
        self.broadcast_message(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to pick trump card from the top or the bottom of the deck ")
        print(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to pick the trump card from the top or the bottom of the deck \n",flush=True)
        self.send_direct_message("[CHOICE] Top or Bottom ",first_player_socket)
        choice = first_player_socket.recv(BYTESIZE).decode(ENCODER)
        self.pick_trump_card(choice)
        self.broadcast_message(f"[TRUMP-CARD] This game's trump card is [{self.trump_card}] ")
        print(f"[TRUMP-CARD This game's trump card is {self.trump_card} \n",flush=True)
        self.distribute_cards()
        self.last_round_winner=self.players[0]


   

    def assure_card_can_be_played(self, card, player):    
        has_round_suit = any(c.suit == self.round_suit for c in player.hand)
        print(f"Player {player} has_round_suit={has_round_suit}")
        print(list(c.suit == self.round_suit for c in player.hand))
        print(f"Player {player.player_name} hand length: {len(player.hand)}")
        print(f"Cards in hand: {[c.suit + c.rank for c in player.hand]}")

        if card.suit == self.round_suit:
            return True
        if card.suit == self.trump_card.suit:
            return True
        if has_round_suit and card.suit !=self.trump_card.suit and card.suit!=self.round_suit:
            return False
        return True


    def play_round(self):
        message1 = f"[ROUND-START] Round has started \n"
        print(message1,flush=True)
        self.broadcast_message(message1)
        message2 = f"[ROUND-COUNTER] Round number {self.round_counter} \n"
        print(message2,flush=True)
        self.broadcast_message(message2)
        round_vector = []
        current_player = self.last_round_winner
        start_index = self.players.index(self.last_round_winner)
        turn_order = self.players[start_index:] + self.players[:start_index]
        for player in turn_order:
            print(f"[PLAYER-ORDER] It's Player [{player.player_name}]'s turn \n",flush=True)
            self.broadcast_message(f"[PLAYER-ORDER] It's Player's [{player.player_name}]'s turn ")
            if player == self.last_round_winner:
                print(f"[PLAYER-ORDER] Player [{player.player_name}] takes the lead this round, as they played the strongest last round, or distributed the deck \n",flush=True)
                self.broadcast_message(f"[PLAYER-ORDER] Player {player.player_name} takes the lead this round, as they played the strongest last round, or distributed the deck ")
                first_player_socket = self.player_sockets[player.player_name]
                self.send_direct_message(f"[CHOICE] It's your turn, choose a number between 1 and {len(player.hand)} ",first_player_socket)
                first_card_json = first_player_socket.recv(BYTESIZE).decode(ENCODER)
                first_card_str = json.loads(first_card_json)
                first_card = Card.from_string(first_card_str)
                self.broadcast_message(f"[PLAY] Player [{player.player_name}] played [{first_card}] ")
                round_vector.append(first_card)
                self.round_suit = round_vector[0].suit
                print(f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {self.trump_card.suit}  alternatively \n",flush=True)
                self.broadcast_message(f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {self.trump_card.suit}  alternatively ")
            else:
                player_socket = self.player_sockets[player.player_name]
                self.send_direct_message("[CHOICE] It's your turn, choose a number between 1 and 10 ",player_socket)
                while True:
                    card_json = player_socket.recv(BYTESIZE).decode(ENCODER)
                    card_str = json.loads(card_json)
                    card = Card.from_string(card_str)
                    print(card)
                    if self.assure_card_can_be_played(card,player):
                        self.broadcast_message(f"[PLAY] Player [{player.player_name}] played [{card}] ")
                        round_vector.append(card)
                        break
                    else:
                        self.send_direct_message(f"[INVALID] You must follow suit [{self.round_suit}]. Try again ", player_socket)
                        print(f"[INVALID]You must follow suit [{self.round_suit}] \n")
                        player.hand.append(card)

        
        print("[ANNOUNCEMENT Cards played this round ")
        for i, card in enumerate(round_vector, start=1):
            print(f"[ANNOUNCEMENT] Player [{self.players[i-1].player_name}] played  [{card}] \n",flush=True)
            self.broadcast_message(f"[ANNOUNCEMENT] Player [{self.players[i-1].player_name}] played  [{card}]")
        
        def determine_round_winner():
            trump_was_played = any(card.suit == self.trump_card_suit for card in round_vector)

            
            if trump_was_played:
                trump_cards = [card for card in round_vector if card.suit == self.trump_card_suit]
                winner = max(trump_cards,key=lambda card:ranks_map[card.rank])
                winner_index = round_vector.index(winner)
                return winner,winner_index
            
            winner = max(round_vector,key=lambda card:ranks_map[card.rank])
            winner_index = round_vector.index(winner)
            return winner,winner_index
        

        round_winner,winner_index = determine_round_winner()
        winner_player = self.players[winner_index]
        self.last_round_winner = winner_player

        def get_round_sum():
            round_sum = 0
            for card in round_vector:
                round_sum+=ranks_map[card.rank]
            return round_sum
        
        print(f"[ANNOUNCEMENT] Round winner was [{round_winner}],  Player [{winner_player.player_name}] wins [{get_round_sum()}] points \n",flush=True)
        self.broadcast_message(f"[ANNOUNCEMENT] Round winner was [{round_winner}],  Player [{winner_player.player_name}] wins [{get_round_sum()}] points.")
        self.scores[winner_player.player_name] += get_round_sum()
        self.round_counter+=1


    def end_game(self):
        message = f"[END] Game has ended \n"
        print(message,flush=True)
        self.broadcast_message(message)
        self.disconnect_server_socket()


    def show_final_scores_and_print_winner(self):
        team1_score = sum(self.scores[player] for player in self.teams[0])
        team2_score = sum(self.players_and_scores[player] for player in self.teams[1])

        print(f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0].name} & {self.teams[0][1].name}] scored [{team1_score}] \n",flush=True)
        self.broadcast_message(f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0].name} & {self.teams[0][1].name}] scored [{team1_score}]")
        print(f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0].name} & {self.teams[1][1].name}] scored [{team2_score}] \n",flush=True)
        self.broadcast_message(f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0].name} & {self.teams[1][1].name}] scored [{team2_score}]")

        if team1_score > team2_score:
            print("[ANNOUNCEMENT] Team 1 is victorious 🏆 \n",flush=True)
            self.broadcast_message("[ANNOUNCEMENT] Team 1 is victorious 🏆")
        elif team2_score > team1_score:
            print("[ANNOUNCEMENT] Team 2 is victorious 🏆 \n",flush=True)
            self.broadcast_message("[ANNOUNCEMENT] Team 2 is victorious 🏆!")


def main():
    server = GameServer()
    server.connect_server_socket()
    server.accept_player_sockets()
    server.start_game()
    for i in range(10):
        server.play_round()
    server.show_final_scores_and_print_winner()
    server.end_game()
    
    
if __name__ == "__main__":
    main()
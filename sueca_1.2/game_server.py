from constants import *
from socket import *
from player import *
from deck import *
import time
from positions import Positions
from random import shuffle

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
        self.teams = [[],[]]
        self.positions = [Positions.NORTH,
                          Positions.EAST,
                          Positions.SOUTH,
                          Positions.WEST]
        
        self.deck_backup = None

    def shuffle_positions(self):
        shuffle(self.positions)

    def connect_server_socket(self):
        self.server_socket.bind(SERVER_BIND)
        self.server_socket.listen(4)
        print(f"[CONNECTED] Game Server is online")

    def disconnect_server_socket(self):
        self.server_socket.close()
        print(f"[DISCONNECTED] Game Server is offline")

    def broadcast_message(self, message):
        for player_socket in self.player_sockets.values():
            player_socket.sendall((message + "\n").encode(ENCODER))
            time.sleep(0.01)

    def send_direct_message(self, message, player_socket):
        player_socket.sendall((message + "\n").encode(ENCODER))

    def accept_player_sockets(self):
        while len(self.players)<self.max_players:
            player_socket, player_address = self.server_socket.accept()
            player_name = player_socket.recv(BYTESIZE).decode(ENCODER)
            broadcast_message = f"[CONNECTED] Player [{len(self.players)+1}] [{player_name}] has joined the game from {player_address}"
            print(broadcast_message)
            self.broadcast_message(broadcast_message)
            self.player_sockets[player_name] = player_socket
            self.assign_player(player_name)

    def assign_player(self,player_name):
        player = Player(player_name)
        player.position=self.positions[len(self.players)]
        self.players.append(player)
        self.scores[player_name] = 0
        print(f"[ANNOUNCEMENT] {player_name} was assigned position [{player.position}] ")
        self.broadcast_message(f"[ANNOUNCEMENT] {player_name} was assigned position [{player.position}] ")

    def assign_teams(self):
        for player in self.players:
            print(f"[ANNOUNCEMENT Player {player.player_name} is to the {player.position} ")
            if player.position in (Positions.NORTH,Positions.SOUTH):
                self.teams[0].append(player)
                print(f"[ANNOUNCEMENT] {player.player_name} was assigned to the first team ")
                self.broadcast_message(f"[ANNOUNCEMENT] {player.player_name} was assigned to the first team ")
            else:
                print(f"[ANNOUNCEMENT] {player.player_name} was assigned to the second team ")
                self.broadcast_message(f"[ANNOUNCEMENT] {player.player_name} was assigned to the second team ")
                self.teams[1].append(player)

    def deal_cards(self):
        for player in self.players:
            set_of_cards = [self.deck.pile.pop(0) for _ in range(10)]
            player.hand = set_of_cards
            player_socket = self.player_sockets[player.player_name]
            data = " ".join(str(card) for card in set_of_cards)
            payload = f"[HAND]{data}\n"
            print(f"Sending this: {payload}")
            player_socket.sendall(payload.encode(ENCODER))

    def pick_trump_card(self,choice):
        if choice == "top":
            trump_card = self.deck.pile[0]
        elif choice == "bottom":
            trump_card = self.deck.pile[-1]
        self.trump_card=trump_card
        self.trump_card_suit=self.trump_card[0]

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
        print("[CUTTING] Cutting deck")
        self.shuffle_positions()
        self.assign_teams()
        first_player_socket = list(self.player_sockets.values())[0]
        self.broadcast_message(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to cut the deck ")
        print(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to cut the deck")
        self.send_direct_message("[CHOICE] Cut from what index ",first_player_socket)
        cut_index = int(first_player_socket.recv(BYTESIZE).decode(ENCODER))
        print(f"[CUT-RECEIVED] Player cut the deck at index [{cut_index}]")
        self.broadcast_message(f"[CUT-RECEIVED] Player cut the deck at index [{cut_index}]")
        print("Deck before the cut")
        print(str(self.deck))
        self.deck.cut_deck(cut_index)
        print("Deck after the cut ")
        print(str(self.deck))
        self.broadcast_message(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to pick trump card from the top or the bottom of the deck")
        print(f"[ANNOUNCEMENT] Player [1] [{self.players[0].player_name}] gets to pick the trump card from the top or the bottom of the deck")
        self.send_direct_message("[CHOICE] Top or Bottom ",first_player_socket)
        choice = first_player_socket.recv(BYTESIZE).decode(ENCODER)
        self.pick_trump_card(choice)
        self.broadcast_message(f"[TRUMP-CARD] This game's trump card is [{self.trump_card}] ")
        print(f"[TRUMP-CARD] This game's trump card is {self.trump_card}")
        self.deck_backup = self.deck.pile.copy()
        self.deal_cards()
        self.last_round_winner=self.players[0]


    def assure_card_can_be_played(self, card, player):    
        has_round_suit = any(card[0] == self.round_suit for card in player.hand)
        print(f"Player {player} has_round_suit={has_round_suit}")
        if card[0] == self.round_suit:
            return True
        if card[0] == self.trump_card_suit:
            return True
        if has_round_suit and card[0] !=self.trump_card_suit and card[0]!=self.round_suit:
            return False
        return True


    def play_round(self):
        message1 = f"[ROUND-START] Round has started"
        print(message1)
        self.broadcast_message(message1)
        message2 = f"[ROUND-COUNTER] Round number {self.round_counter}"
        print(message2)
        self.broadcast_message(message2)
        round_vector = []
        current_player = self.last_round_winner
        start_index = self.players.index(self.last_round_winner)
        turn_order = self.players[start_index:] + self.players[:start_index]
        for player in turn_order:
            print(f"[PLAYER-ORDER] It's Player [{player.player_name}]'s turn")
            self.broadcast_message(f"[PLAYER-ORDER] It's Player's [{player.player_name}]'s turn ")
            if player == self.last_round_winner:
                print(f"[PLAYER-ORDER] Player [{player.player_name}] takes the lead this round, as they played the strongest last round, or distributed the deck")
                self.broadcast_message(f"[PLAYER-ORDER] Player {player.player_name} takes the lead this round, as they played the strongest last round, or distributed the deck")
                first_player_socket = self.player_sockets[player.player_name]
                self.send_direct_message(f"[CHOICE] It's your turn, choose a number between 1 and {len(player.hand)} ",first_player_socket)
                first_card = first_player_socket.recv(BYTESIZE).decode(ENCODER)
                print(f"THIS IS THE IRST CARD {first_card}")
                self.broadcast_message(f"[PLAY] Player [{player.player_name}] played [{first_card}]")
                for i, c in enumerate(player.hand):
                    if c[2] == first_card[2] and c[0] == first_card[0]:
                        player.hand.pop(i)
                        removed = True
                        break
                if not removed:
                        print(f"[WARNING] Played card not found in server-side hand: {card}")
                round_vector.append(first_card)
                self.round_suit = round_vector[0][0]
                print(f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {self.trump_card[0]}  alternatively")
                self.broadcast_message(f"[ANNOUNCEMENT] This round's suit is {self.round_suit}. You're forced to play a card of suit {self.round_suit} if you have one in hand! You can play a card with the trump suit {self.trump_card[0]}  alternatively ")
            else:
                player_socket = self.player_sockets[player.player_name]
                self.send_direct_message("[CHOICE] It's your turn, choose a number between 1 and 10",player_socket)
                while True:
                    card = player_socket.recv(BYTESIZE).decode(ENCODER)
                    print("RECEIVED THIS!!!",card)
                    if self.assure_card_can_be_played(card,player):
                        removed = False
                        for i, c in enumerate(player.hand):
                            if c[2] == card[2] and c[0] == card[0]:
                                player.hand.pop(i)
                                removed = True
                                break
                        if not removed:
                            print(f"[WARNING] Played card not found in server-side hand: {card}")

                        self.broadcast_message(f"[PLAY] Player [{player.player_name}] played [{card}]")
                        round_vector.append(card)
                        break
                    else:
                        self.send_direct_message(f"[INVALID] You must follow suit [{self.round_suit}]. Try again ", player_socket)
                        print(f"[INVALID]You must follow suit [{self.round_suit}] \n")

        
        print("[ANNOUNCEMENT Cards played this round ")
        for i, card in enumerate(round_vector, start=1):
            print(f"[ANNOUNCEMENT] Player [{self.players[i-1].player_name}] played  [{card}]")
            self.broadcast_message(f"[ANNOUNCEMENT] Player [{self.players[i-1].player_name}] played  [{card}]")
        
        def _determine_round_winner():
            trump_was_played = any(card[0] == self.trump_card_suit for card in round_vector)

            print("LE PILE",self.deck.pile)
            print("LE BACKUP PILE",self.deck_backup)
            if trump_was_played:
                trump_cards = [card for card in round_vector if card[0] == self.trump_card_suit]
                winner = max(trump_cards,key=lambda card:self.deck.points[self.deck_backup.index(card)])
                print("WINNER IS YIIIIPEEEEierieriieriierieirirE",winner)
                winner_index = round_vector.index(winner)
                return winner,winner_index
            

            winner = max(round_vector,key=lambda card:self.deck.points[self.deck_backup.index(card)])
            print("WINNER IS YIIIIPEEEEE",winner)
            winner_index = round_vector.index(winner)
            return winner,winner_index
        

        round_winner,winner_index = _determine_round_winner()
        winner_player = self.players[winner_index]
        self.last_round_winner = winner_player

        def _get_round_sum():
            round_sum = 0
            for card in round_vector:
                round_sum+=ranks_map[card[2]]
            return round_sum
        
        print(f"[ANNOUNCEMENT] Round winner was [{round_winner}],  Player [{winner_player.player_name}] wins [{_get_round_sum()}] points")
        self.broadcast_message(f"[ANNOUNCEMENT] Round winner was [{round_winner}],  Player [{winner_player.player_name}] wins [{_get_round_sum()}] points.")
        self.scores[winner_player.player_name] += _get_round_sum()
        self.round_counter+=1


    def end_game(self):
        message = f"[END] Game has ended"
        print(message)
        self.broadcast_message(message)
        for player in self.players:
            player.disconnect_player_socket()
        self.disconnect_server_socket()


    def show_final_scores_and_print_winner(self):
        team1_score = sum(self.scores[player.player_name] for player in self.teams[0])
        team2_score = 120-team1_score

        print(f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0]} & {self.teams[0][1]}] scored [{team1_score}]")
        self.broadcast_message(f"[ANNOUNCEMENT] Team 1 [Players {self.teams[0][0]} & {self.teams[0][1]}] scored [{team1_score}]")
        print(f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0]} & {self.teams[1][1]}] scored [{team2_score}]")
        self.broadcast_message(f"[ANNOUNCEMENT] Team 2 [Players {self.teams[1][0]} & {self.teams[1][1]}] scored [{team2_score}]")

        if team1_score > team2_score:
            print("[ANNOUNCEMENT] Team 1 is victorious 🏆")
            self.broadcast_message("[ANNOUNCEMENT] Team 1 is victorious 🏆")
        elif team2_score > team1_score:
            print("[ANNOUNCEMENT] Team 2 is victorious 🏆")
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
        server.play_round()
    server.show_final_scores_and_print_winner()
    server.end_game()
    
    
if __name__ == "__main__":
    main()
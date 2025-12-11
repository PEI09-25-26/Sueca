from src.constants import *
from src.player import Player
from src.deck import Deck
from src.positions import Positions
from pprint import pprint
from src.card_mapper import CardMapper
from src.constants import * 

class TurnDisplayer:
    def __init__(self,player,turn,trump_owner,trump_card,players):
        self.players = players
        self.trump_card = trump_card
        self.player = player
        self.trump_owner = trump_owner  
        self.turn = turn
        self.card_faced_down = "🂠"
        self.height = TABLE_HEIGHT
        self.width = TABLE_WIDTH
        self.table = [[" " for _ in range(self.width)] for _ in range(self.height)]
        self.margin = margin
        
    def draw_borders(self):
        for x in range(self.width):
            self.table[0][x] = "="
            self.table[self.height - 1][x] = "="
        for y in range(self.height):
            self.table[y][0] = "="
            self.table[y][self.width - 1] = "="

       
    def render_table(self):
        self.player.hand.sort(key=CardMapper.get_card_points)
        self.draw_borders()
        self.draw_this_player_cards()
        self.draw_trump_owner_cards()
        self.draw_other_cards()
        for row in self.table:
            print("".join(row))


    def inject_card(self, card, x, y):
        for i, c in enumerate(card):
            self.table[x][y + i] = c

        
    def draw_this_player_cards(self):
        match self.player.position:
            case Positions.SOUTH:
                for i,card in enumerate(self.player.hand):
                    self.inject_card(CardMapper.get_card(card),self.height-3,margin+i*6)
            case Positions.NORTH:

                for i,card in enumerate(self.player.hand):
                    self.inject_card(CardMapper.get_card(card),3,margin+i*6)
            case Positions.WEST:

                for i, card in enumerate(self.player.hand):
                    self.inject_card(CardMapper.get_card(card), margin + i*2, 3)
            case Positions.EAST:

                for i, card in enumerate(self.player.hand):
                    self.inject_card(CardMapper.get_card(card), margin + i*2, self.width-10)

    def draw_trump_owner_cards(self):
        trump_owner_cards = [self.trump_card] + [self.card_faced_down] * (9 - self.turn + 1)

        match self.trump_owner.position:
            case Positions.SOUTH:
                for i, card in enumerate(trump_owner_cards):
                    actual_card = CardMapper.get_card(card) if i == 0 else self.card_faced_down
                    self.inject_card(actual_card, self.height - 3, margin + i * 6)

            case Positions.NORTH:
                for i, card in enumerate(trump_owner_cards):
                    actual_card = CardMapper.get_card(card) if i == 0 else self.card_faced_down
                    self.inject_card(actual_card, 3, margin + i * 6)

            case Positions.WEST:
                for i, card in enumerate(trump_owner_cards):
                    actual_card = CardMapper.get_card(card) if i == 0 else self.card_faced_down
                    self.inject_card(actual_card, margin + i * 2, 3)

            case Positions.EAST:
                for i, card in enumerate(trump_owner_cards):
                    actual_card = CardMapper.get_card(card) if i == 0 else self.card_faced_down
                    self.inject_card(actual_card, margin + i * 2, self.width - 10)

    def draw_other_cards(self):
        for p in self.players:
            if p == self.player or p == self.trump_owner:
                continue

            face_down_cards = [self.card_faced_down] * len(p.hand)

            match p.position:
                case Positions.SOUTH:
                    for i, card in enumerate(face_down_cards):
                        self.inject_card(card, self.height - 3, margin + i * 6)
                case Positions.NORTH:
                    for i, card in enumerate(face_down_cards):
                        self.inject_card(card, 3, margin + i * 6)
                case Positions.WEST:
                    for i, card in enumerate(face_down_cards):
                        self.inject_card(card, margin + i * 2, 3)
                case Positions.EAST:
                    for i, card in enumerate(face_down_cards):
                        self.inject_card(card, margin + i * 2, self.width - 10)
"""
Simple Flask REST API Server for Sueca
No WebSockets - just simple HTTP endpoints
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from deck import Deck
from player_flask import Player
from positions import Positions
from card_mapper import CardMapper
from random import shuffle
import logging
import requests

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameState:
    """Simple game state manager"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.deck = Deck()
        self.players = []  # List of Player objects
        self.max_players = 4
        self.trump_card = None
        self.trump_suit = None
        self.teams = [[], []]
        self.scores = {}  # Individual player scores
        self.team_scores = [0, 0]  # Team 1 and Team 2 scores
        self.positions = [Positions.NORTH, Positions.EAST, Positions.SOUTH, Positions.WEST]
        self.game_started = False
        self.phase = 'waiting'  # waiting, deck_cutting, trump_selection, playing, finished
        self.current_round = 1
        self.round_plays = []  # Cards played in current round
        self.round_suit = None  # Suit of first card in round
        self.current_player = None  # Player whose turn it is
        self.last_winner = None
        self.turn_order = []  # Order of players for current round
        shuffle(self.positions)
        self._push_state("game_reset")
    
    def add_player(self, name):
        if len(self.players) >= self.max_players:
            return False, "Game is full"
        
        if any(p.player_name == name for p in self.players):
            return False, "Name already taken"
        
        player = Player(name)
        player.position = self.positions[len(self.players)]
        self.players.append(player)
        self.scores[name] = 0
        
        # Assign to team
        if player.position in (Positions.NORTH, Positions.SOUTH):
            self.teams[0].append(player)
        else:
            self.teams[1].append(player)
        
        logger.info(f"Player {name} joined at position {player.position}")
        
        # Prepare for deck cutting when 4 players join
        if len(self.players) == self.max_players and not self.game_started:
            self.phase = 'deck_cutting'
            self.deck.shuffle_deck()
            logger.info("All players joined - ready for deck cutting")
        
        self._push_state("player_joined")
        return True, f"Joined as {player.position}"
    
    def cut_deck(self, player_name, cut_index):
        """NORTH player cuts the deck at given index"""
        player = self.get_player(player_name)
        if not player:
            return False, "Player not found"
        
        if player.position != Positions.NORTH:
            return False, "Only NORTH player can cut deck"
        
        if self.phase != 'deck_cutting':
            return False, "Not in deck cutting phase"
        
        try:
            cut_index = int(cut_index)
            if cut_index < 1 or cut_index > 40:
                return False, "Cut index must be between 1 and 40"
        except ValueError:
            return False, "Cut index must be a number"
        
        self.deck.cut_deck(cut_index)
        logger.info(f"Deck cut by {player_name} at index {cut_index}")
        
        # Move to trump selection phase
        self.phase = 'trump_selection'

        self._push_state("deck_cut")
        return True, f"Deck cut at index {cut_index}"
    
    def select_trump(self, player_name, choice):
        """WEST player selects trump card (top or bottom)"""
        player = self.get_player(player_name)
        if not player:
            return False, "Player not found"
        
        if player.position != Positions.WEST:
            return False, "Only WEST player can select trump"
        
        if self.phase != 'trump_selection':
            return False, "Not in trump selection phase"
        
        if choice.lower() == 'top':
            self.trump_card = self.deck.cards[0]
        elif choice.lower() == 'bottom':
            self.trump_card = self.deck.cards[-1]
        else:
            return False, "Choice must be 'top' or 'bottom'"
        
        self.trump_suit = CardMapper.get_card_suit(self.trump_card)
        logger.info(f"Trump selected by {player_name}: {CardMapper.get_card(self.trump_card)}")
        
        # Now deal cards and start game
        self._deal_cards()
        self.phase = 'playing'
        self.game_started = True
        
        self._push_state("trump_selected")
        return True, f"Trump card is {CardMapper.get_card(self.trump_card)}"
    
    def _deal_cards(self):
        """Internal method to deal cards to all players"""
        for player in self.players:
            player.hand = sorted([self.deck.cards.pop(0) for _ in range(10)])
        
        # Set starting player to SOUTH
        for player in self.players:
            if player.position == Positions.SOUTH:
                self.last_winner = player
                self.current_player = player
                break
        
        # Set initial turn order
        self._set_turn_order()
    
    def _set_turn_order(self):
        """Set turn order starting from last winner"""
        if not self.last_winner:
            return
        start_index = self.players.index(self.last_winner)
        self.turn_order = self.players[start_index:] + self.players[:start_index]
        if self.turn_order:
            self.current_player = self.turn_order[0]
    
    def start_game(self):
        """Legacy method - now handled by cut_deck -> select_trump flow"""
        if self.game_started:
            return False, "Game already started"
        if len(self.players) < self.max_players:
            return False, f"Need {self.max_players} players"
        
        if self.phase == 'deck_cutting':
            return False, "Waiting for NORTH player to cut deck"
        
        if self.phase == 'trump_selection':
            return False, "Waiting for WEST player to select trump (top/bottom)"
        
        return False, "Game cannot be started in current phase"
    

    def get_player(self, name):
        for player in self.players:
            if player.player_name == name:
                return player
        return None
    
    def _can_play_card(self, player, card_id):
        """Check if player can play this card (prevent renounce)"""
        if not self.round_suit:
            # First card of round, any card is valid
            return True
        
        card_suit = CardMapper.get_card_suit(card_id)
        
        # Check if player has cards of round suit
        has_round_suit = any(
            CardMapper.get_card_suit(c) == self.round_suit for c in player.hand
        )
        
        # If playing round suit, always valid
        if card_suit == self.round_suit:
            return True
        
        # If not playing round suit but player has round suit cards, invalid (renounce!)
        if has_round_suit:
            return False
        
        # Player doesn't have round suit, can play anything
        return True
    
    def _determine_round_winner(self):
        """Determine who won the round"""
        if len(self.round_plays) != 4:
            return None
        
        # Check if any trump cards were played
        trump_played = [
            play for play in self.round_plays 
            if CardMapper.get_card_suit(int(play['card'])) == self.trump_suit
        ]
        
        if trump_played:
            # Highest trump wins
            winner_play = max(trump_played, key=lambda p: int(p['card']))
        else:
            # Highest card of round suit wins
            round_suit_plays = [
                play for play in self.round_plays
                if CardMapper.get_card_suit(int(play['card'])) == self.round_suit
            ]
            winner_play = max(round_suit_plays, key=lambda p: int(p['card']))
        
        return self.get_player(winner_play['player'])
    
    def _calculate_round_points(self):
        """Calculate total points in the round"""
        total = 0
        for play in self.round_plays:
            total += CardMapper.get_card_points(int(play['card']))
        return total
    
    def _finish_round(self):
        """Finish the round and update scores"""
        winner = self._determine_round_winner()
        if not winner:
            return
        
        points = self._calculate_round_points()
        
        # Add points to winner's team
        if winner in self.teams[0]:
            self.team_scores[0] += points
            team_name = "Team 1 (N/S)"
        else:
            self.team_scores[1] += points
            team_name = "Team 2 (E/W)"
        
        logger.info(f"Round {self.current_round} won by {winner.player_name} - {points} points to {team_name}")
        
        # Prepare for next round
        self.last_winner = winner
        self.current_round += 1
        self.round_plays = []
        self.round_suit = None
        
        # Check if game is over
        if self.current_round > 10:
            self.phase = 'finished'
            self.game_started = False
        else:
            self._set_turn_order()
        
        event = {
            "type": "round_end",
            "round": self.current_round - 1,
            "winner": winner.player_name,
            "game_finished": self.phase == "finished",
            "state": self.get_state()
        }
        try:
            requests.post(
                "http://localhost:8000/game/event",
                json=event,
                timeout=0.3
            )
        except:
            pass
    
    def play_card(self, player_name, card_str):
        player = self.get_player(player_name)
        if not player:
            return False, "Player not found"
        
        # Check if it's this player's turn
        if self.current_player != player:
            return False, f"Not your turn! Waiting for {self.current_player.player_name}"
        
        # Find card in hand
        card = None
        for c in player.hand:
            if str(c) == card_str:
                card = c
                break
        
        if not card:
            return False, "Card not in hand"
        
        # Check if card can be played (prevent renounce)
        if not self._can_play_card(player, card):
            return False, f"You must follow suit {self.round_suit}!"
        
        # Play the card
        player.hand.remove(card)
        self.round_plays.append({'player': player_name, 'card': str(card), 'position': str(player.position)})
        
        # Set round suit if this is first card
        if len(self.round_plays) == 1:
            self.round_suit = CardMapper.get_card_suit(card)
        
        logger.info(f"{player_name} played {CardMapper.get_card(card)}")
        
        # Move to next player in turn order
        current_index = self.turn_order.index(player)
        if current_index + 1 < len(self.turn_order):
            self.current_player = self.turn_order[current_index + 1]

        success = True
        if success:
            event = {
                "type": "card_played",
                "player": player_name,
                "card": card_str,
                "state": self.get_state()
            }
            try:
                requests.post(
                    "http://localhost:8000/game/event",
                    json=event,
                    timeout=0.5
                )
            except:
                pass
        
        # Check if round is complete
        if len(self.round_plays) == 4:
            self._finish_round()
        
        return True, f"Played {CardMapper.get_card(card)}"
    
    def get_state(self):
        # Find NORTH and WEST players
        north_player = None
        west_player = None
        for p in self.players:
            if p.position == Positions.NORTH:
                north_player = p.player_name
            elif p.position == Positions.WEST:
                west_player = p.player_name
        
        # Get last round winner info
        last_round_info = None
        if self.round_plays and len(self.round_plays) == 0 and self.current_round > 1:
            # Show previous round result
            pass
        
        return {
            'players': [
                {
                    'name': p.player_name,
                    'position': str(p.position),
                    'cards_left': len(p.hand)
                }
                for p in self.players
            ],
            'player_count': len(self.players),
            'game_started': self.game_started,
            'phase': self.phase,
            'north_player': north_player,
            'west_player': west_player,
            'current_player': self.current_player.player_name if self.current_player else None,
            'trump': str(self.trump_card) if self.trump_card else None,
            'trump_suit': self.trump_suit,
            'current_round': self.current_round,
            'round_suit': self.round_suit,
            'teams': {
                'team1': [p.player_name for p in self.teams[0]],
                'team2': [p.player_name for p in self.teams[1]]
            },
            'scores': self.scores,
            'team_scores': {'team1': self.team_scores[0], 'team2': self.team_scores[1]},
            'round_plays': self.round_plays
        }
    
    def _push_state(self, event_type="state_update"):
        event = {
            "type": event_type,
            "state": self.get_state()
        }

        try:
            requests.post(
                "http://localhost:8000/game/event",
                json=event,
                timeout=0.3
            )
        except:
            pass


# Global game state
game = GameState()


# === API ENDPOINTS ===

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current game state"""
    return jsonify(game.get_state())


@app.route('/api/join', methods=['POST'])
def join_game():
    """Join the game"""
    data = request.get_json()
    name = data.get('name', '')
    
    if not name:
        return jsonify({'success': False, 'message': 'Name required'}), 400
    
    success, message = game.add_player(name)
    return jsonify({'success': success, 'message': message})


@app.route('/api/start', methods=['POST'])
def start_game():
    """Start the game"""
    success, message = game.start_game()
    return jsonify({'success': success, 'message': message})


@app.route('/api/cut_deck', methods=['POST'])
def cut_deck():
    """Cut the deck (NORTH player only)"""
    data = request.get_json()
    player_name = data.get('player')
    cut_index = data.get('index')
    
    if not player_name or not cut_index:
        return jsonify({'success': False, 'message': 'Player and index required'}), 400
    
    success, message = game.cut_deck(player_name, cut_index)
    return jsonify({'success': success, 'message': message})


@app.route('/api/select_trump', methods=['POST'])
def select_trump():
    """Select trump card (WEST player only)"""
    data = request.get_json()
    player_name = data.get('player')
    choice = data.get('choice')  # 'top' or 'bottom'
    
    if not player_name or not choice:
        return jsonify({'success': False, 'message': 'Player and choice required'}), 400
    
    success, message = game.select_trump(player_name, choice)
    return jsonify({'success': success, 'message': message})





@app.route('/api/hand/<player_name>', methods=['GET'])
def get_hand(player_name):
    """Get player's hand"""
    player = game.get_player(player_name)
    if not player:
        return jsonify({'success': False, 'message': 'Player not found'}), 404
    
    return jsonify({
        'success': True,
        'hand': [str(c) for c in player.hand]
    })


@app.route('/api/play', methods=['POST'])
def play_card():
    """Play a card"""
    data = request.get_json()
    player_name = data.get('player')
    card = data.get('card')
    
    if not player_name or not card:
        return jsonify({'success': False, 'message': 'Player and card required'}), 400
    
    success, message = game.play_card(player_name, card)
    return jsonify({'success': success, 'message': message})


@app.route('/api/reset', methods=['POST'])
def reset_game():
    """Reset the game"""
    game.reset()
    return jsonify({'success': True, 'message': 'Game reset'})


if __name__ == '__main__':
    print("=" * 50)
    print("Sueca Game Server")
    print("=" * 50)
    print("Server running on http://localhost:5000")
    print("Press Ctrl+C to stop")
    print()
    app.run(host='0.0.0.0', port=5000, debug=True)

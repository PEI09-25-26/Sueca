"""
Simple Flask REST API Server for Sueca
Supports multiple game rooms by game ID.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from deck import Deck
from player_flask import Player
from positions import Positions
from card_mapper import CardMapper
import logging
import requests
import threading
import uuid

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameState:
    """Game state manager for a single room."""

    def __init__(self, game_id):
        self.game_id = game_id
        self.reset()

    def reset(self):
        self.deck = Deck()
        self.players = []
        self.max_players = 4
        self.trump_card = None
        self.trump_suit = None
        self.teams = [[], []]
        self.scores = {}
        self.team_scores = [0, 0]
        self.positions = [Positions.NORTH, Positions.EAST, Positions.SOUTH, Positions.WEST]
        self.available_team_positions = {
            'team1': [Positions.NORTH, Positions.SOUTH],
            'team2': [Positions.EAST, Positions.WEST],
        }
        self.game_started = False
        self.phase = 'waiting'  # waiting, deck_cutting, trump_selection, playing, finished
        self.current_round = 1
        self.round_plays = []
        self.round_suit = None
        self.current_player = None
        self.last_winner = None
        self.turn_order = []
        self._push_state('game_reset')

    _POSITION_MAP = {
        'north': Positions.NORTH,
        'south': Positions.SOUTH,
        'east':  Positions.EAST,
        'west':  Positions.WEST,
    }
    _TEAM1_POSITIONS = {Positions.NORTH, Positions.SOUTH}

    def _normalize_position(self, position_choice):
        if position_choice is None:
            return None
        return self._POSITION_MAP.get(str(position_choice).strip().lower())

    def add_player(self, name, position_choice):
        if len(self.players) >= self.max_players:
            return False, 'Game is full', None

        position = self._normalize_position(position_choice)
        if not position:
            return False, 'Invalid position. Choose NORTH, SOUTH, EAST, or WEST', None

        team_key = 'team1' if position in self._TEAM1_POSITIONS else 'team2'
        if position not in self.available_team_positions[team_key]:
            return False, f'Position {position.name} is already taken', None

        player = Player(name)
        player.player_id = uuid.uuid4().hex[:8]
        player.position = position
        self.available_team_positions[team_key].remove(position)
        self.players.append(player)
        self.scores[player.player_id] = 0

        if team_key == 'team1':
            self.teams[0].append(player)
        else:
            self.teams[1].append(player)

        logger.info('Player %s joined game %s at position %s', name, self.game_id, player.position)

        if len(self.players) == self.max_players and not self.game_started:
            self.phase = 'deck_cutting'
            self.deck.shuffle_deck()
            logger.info('Game %s ready for deck cutting', self.game_id)

        self._push_state('player_joined')
        return True, f'Joined as {player.position}', player.player_id

    def get_player(self, player_id):
        for player in self.players:
            if getattr(player, 'player_id', None) == player_id:
                return player
        return None

    def cut_deck(self, player_id, cut_index):
        player = self.get_player(player_id)
        if not player:
            return False, 'Player not found'

        if player.position != Positions.NORTH:
            return False, 'Only NORTH player can cut deck'

        if self.phase != 'deck_cutting':
            return False, 'Not in deck cutting phase'

        try:
            cut_index = int(cut_index)
            if cut_index < 1 or cut_index > 40:
                return False, 'Cut index must be between 1 and 40'
        except ValueError:
            return False, 'Cut index must be a number'

        self.deck.cut_deck(cut_index)
        logger.info('Deck cut by %s at index %s in game %s', player.player_name, cut_index, self.game_id)

        self.phase = 'trump_selection'
        self._push_state('deck_cut')
        return True, f'Deck cut at index {cut_index}'

    def select_trump(self, player_id, choice):
        player = self.get_player(player_id)
        if not player:
            return False, 'Player not found'

        if player.position != Positions.WEST:
            return False, 'Only WEST player can select trump'

        if self.phase != 'trump_selection':
            return False, 'Not in trump selection phase'

        if choice.lower() == 'top':
            self.trump_card = self.deck.cards.pop(0)
        elif choice.lower() == 'bottom':
            self.trump_card = self.deck.cards.pop(-1)
        else:
            return False, "Choice must be 'top' or 'bottom'"

        self.trump_suit = CardMapper.get_card_suit(self.trump_card)
        logger.info('Trump selected by %s in game %s: %s', player.player_name, self.game_id, CardMapper.get_card(self.trump_card))

        self._deal_cards(player) # Pass the WEST player to ensure they get the card
        self.phase = 'playing'
        self.game_started = True

        self._push_state('trump_selected')
        return True, f'Trump card is {CardMapper.get_card(self.trump_card)}'

    def _deal_cards(self, dealer):
        # Deal 9 cards to everyone first (to keep one slot open for dealer's trump)
        for player in self.players:
            player.hand = [self.deck.cards.pop(0) for _ in range(9)]
        
        # Give the dealer the trump card + 9 cards (total 10)
        # Sort hands at the end
        for player in self.players:
            if player == dealer:
                player.hand.append(self.trump_card)
            else:
                player.hand.append(self.deck.cards.pop(0))
            player.hand.sort()

        # SOUTH always starts in this implementation
        for player in self.players:
            if player.position == Positions.SOUTH:
                self.last_winner = player
                self.current_player = player
                break

        self._set_turn_order()

    def _set_turn_order(self):
        if not self.last_winner:
            return

        position_order = [Positions.NORTH, Positions.WEST, Positions.SOUTH, Positions.EAST]
        sorted_players = sorted(self.players, key=lambda p: position_order.index(p.position))
        start_index = sorted_players.index(self.last_winner)
        self.turn_order = sorted_players[start_index:] + sorted_players[:start_index]

        if self.turn_order:
            self.current_player = self.turn_order[0]

    def start_game(self):
        if self.game_started:
            return False, 'Game already started'
        if len(self.players) < self.max_players:
            return False, f'Need {self.max_players} players'

        if self.phase == 'deck_cutting':
            return False, 'Waiting for NORTH player to cut deck'

        if self.phase == 'trump_selection':
            return False, "Waiting for WEST player to select trump (top/bottom)"

        return False, 'Game cannot be started in current phase'

    def _can_play_card(self, player, card_id):
        if not self.round_suit:
            return True

        card_suit = CardMapper.get_card_suit(card_id)
        has_round_suit = any(CardMapper.get_card_suit(c) == self.round_suit for c in player.hand)

        if card_suit == self.round_suit:
            return True

        if has_round_suit:
            return False

        return True

    def _determine_round_winner(self):
        if len(self.round_plays) != 4:
            return None

        trump_played = [
            play for play in self.round_plays
            if CardMapper.get_card_suit(int(play['card'])) == self.trump_suit
        ]

        if trump_played:
            winner_play = max(trump_played, key=lambda p: int(p['card']))
        else:
            round_suit_plays = [
                play for play in self.round_plays
                if CardMapper.get_card_suit(int(play['card'])) == self.round_suit
            ]
            winner_play = max(round_suit_plays, key=lambda p: int(p['card']))

        return self.get_player(winner_play['player_id'])

    def _calculate_round_points(self):
        total = 0
        for play in self.round_plays:
            total += CardMapper.get_card_points(int(play['card']))
        return total

    def _finish_round(self):
        winner = self._determine_round_winner()
        if not winner:
            return

        points = self._calculate_round_points()

        if winner in self.teams[0]:
            self.team_scores[0] += points
            team_name = 'Team 1 (N/S)'
        else:
            self.team_scores[1] += points
            team_name = 'Team 2 (E/W)'

        logger.info(
            'Round %s won by %s in game %s - %s points to %s',
            self.current_round,
            winner.player_name,
            self.game_id,
            points,
            team_name,
        )

        self.last_winner = winner
        self.current_round += 1
        self.round_plays = []
        self.round_suit = None

        if self.current_round > 10:
            self.phase = 'finished'
            self.game_started = False
        else:
            self._set_turn_order()

        event = {
            'type': 'round_end',
            'round': self.current_round - 1,
            'winner': winner.player_name,
            'winner_id': winner.player_id,
            'game_finished': self.phase == 'finished',
            'state': self.get_state(),
            'game_id': self.game_id,
        }
        try:
            requests.post('http://localhost:8000/game/event', json=event, timeout=0.3)
        except Exception:
            pass

    def play_card(self, player_id, card_str):
        player = self.get_player(player_id)
        if not player:
            return False, 'Player not found'

        if self.current_player != player:
            return False, f'Not your turn! Waiting for {self.current_player.player_name}'

        card = None
        for c in player.hand:
            if str(c) == card_str:
                card = c
                break

        if card is None:
            return False, 'Card not in hand'

        if not self._can_play_card(player, card):
            return False, f'You must follow suit {self.round_suit}!'

        player.hand.remove(card)
        self.round_plays.append({
            'player_id': player.player_id,
            'player_name': player.player_name,
            'card': str(card),
            'position': str(player.position)
        })

        if len(self.round_plays) == 1:
            self.round_suit = CardMapper.get_card_suit(card)

        logger.info('%s played %s in game %s', player.player_name, CardMapper.get_card(card), self.game_id)

        current_index = self.turn_order.index(player)
        if current_index + 1 < len(self.turn_order):
            self.current_player = self.turn_order[current_index + 1]

        event = {
            'type': 'card_played',
            'player': player.player_name,
            'player_id': player.player_id,
            'card': card_str,
            'state': self.get_state(),
            'game_id': self.game_id,
        }
        try:
            requests.post('http://localhost:8000/game/event', json=event, timeout=0.5)
        except Exception:
            pass

        if len(self.round_plays) == 4:
            threading.Timer(1.69, self._finish_round).start()

        return True, f'Played {CardMapper.get_card(card)}'

    def get_state(self):
        north_player = None
        north_player_id = None
        west_player = None
        west_player_id = None
        for p in self.players:
            if p.position == Positions.NORTH:
                north_player = p.player_name
                north_player_id = p.player_id
            elif p.position == Positions.WEST:
                west_player = p.player_name
                west_player_id = p.player_id

        return {
            'game_id': self.game_id,
            'players': [
                {
                    'id': p.player_id,
                    'name': p.player_name,
                    'position': str(p.position),
                    'cards_left': len(p.hand),
                }
                for p in self.players
            ],
            'player_count': len(self.players),
            'game_started': self.game_started,
            'phase': self.phase,
            'north_player': north_player,
            'north_player_id': north_player_id,
            'west_player': west_player,
            'west_player_id': west_player_id,
            'current_player': self.current_player.player_name if self.current_player else None,
            'current_player_name': self.current_player.player_name if self.current_player else None,
            'current_player_id': self.current_player.player_id if self.current_player else None,
            'trump': str(self.trump_card) if self.trump_card else None,
            'trump_suit': self.trump_suit,
            'current_round': self.current_round,
            'round_suit': self.round_suit,
            'teams': {
                'team1': [p.player_name for p in self.teams[0]],
                'team2': [p.player_name for p in self.teams[1]],
            },
            'scores': self.scores,
            'team_scores': {'team1': self.team_scores[0], 'team2': self.team_scores[1]},
            'round_plays': self.round_plays,
            'available_slots': [
                {'position': p.name, 'team': 'team1', 'team_label': 'N/S'}
                for p in self.available_team_positions['team1']
            ] + [
                {'position': p.name, 'team': 'team2', 'team_label': 'E/W'}
                for p in self.available_team_positions['team2']
            ],
        }

    def _push_state(self, event_type='state_update'):
        event = {
            'type': event_type,
            'state': self.get_state(),
            'game_id': self.game_id,
        }

        try:
            requests.post('http://localhost:8000/game/event', json=event, timeout=0.3)
        except Exception:
            pass


class GameManager:
    def __init__(self):
        self.games = {}
        self.default_game_id = 'default'
        self._lock = threading.Lock()
        self.games[self.default_game_id] = GameState(self.default_game_id)

    def _generate_game_id(self):
        while True:
            candidate = uuid.uuid4().hex[:6].upper()
            if candidate not in self.games:
                return candidate

    def get_game(self, game_id=None):
        if not game_id:
            return self.games.get(self.default_game_id)
        return self.games.get(game_id)

    def create_room(self):
        with self._lock:
            game_id = self._generate_game_id()
            self.games[game_id] = GameState(game_id)
            return game_id

    def create_game(self, creator_name, position_choice):
        with self._lock:
            game_id = self._generate_game_id()
            game = GameState(game_id)
            success, message, player_id = game.add_player(creator_name, position_choice)
            if not success:
                return False, message, None

            self.games[game_id] = game
            return True, message, game_id, player_id


manager = GameManager()


def _get_game_from_request(data=None):
    game_id = None
    if isinstance(data, dict):
        game_id = data.get('game_id')
    if not game_id:
        game_id = request.args.get('game_id')

    if not game_id:
        game_id = manager.default_game_id

    game = manager.get_game(game_id)
    return game, game_id


@app.route('/api/status', methods=['GET'])
def get_status():
    game, game_id = _get_game_from_request()
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404
    return jsonify(game.get_state())


@app.route('/api/room/<game_id>/lobby', methods=['GET'])
def get_room_lobby(game_id):
    """Get room information before joining (available seats and teams)."""
    game = manager.get_game(game_id)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    state = game.get_state()
    available_slots = state.get('available_slots', [])

    return jsonify({
        'success': True,
        'game_id': game_id,
        'phase': state.get('phase'),
        'player_count': state.get('player_count', 0),
        'max_players': game.max_players,
        'available_slots': available_slots,
        'teams': {
            'team1': state.get('teams', {}).get('team1', []),
            'team2': state.get('teams', {}).get('team2', []),
        },
    })


@app.route('/api/create_room', methods=['POST'])
def create_room_endpoint():
    """Create an empty game room and return its ID."""
    game_id = manager.create_room()
    return jsonify({'success': True, 'game_id': game_id})


@app.route('/api/create_game', methods=['POST'])
def create_game():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    position = data.get('position')

    if not name:
        return jsonify({'success': False, 'message': 'Name required'}), 400

    success, message, game_id, player_id = manager.create_game(name, position)
    return jsonify({'success': success, 'message': message, 'game_id': game_id, 'player_id': player_id})


@app.route('/api/join', methods=['POST'])
def join_game():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    position = data.get('position')
    game_id = data.get('game_id') or manager.default_game_id

    if not name:
        return jsonify({'success': False, 'message': 'Name required'}), 400

    game = manager.get_game(game_id)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    success, message, player_id = game.add_player(name, position)
    return jsonify({'success': success, 'message': message, 'game_id': game_id, 'player_id': player_id})


@app.route('/api/start', methods=['POST'])
def start_game():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    success, message = game.start_game()
    return jsonify({'success': success, 'message': message})


@app.route('/api/cut_deck', methods=['POST'])
def cut_deck():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player_id = data.get('player_id') or data.get('player')
    cut_index = data.get('index')

    if not player_id or cut_index is None:
        return jsonify({'success': False, 'message': 'Player and index required'}), 400

    success, message = game.cut_deck(player_id, cut_index)
    return jsonify({'success': success, 'message': message})


@app.route('/api/select_trump', methods=['POST'])
def select_trump():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player_id = data.get('player_id') or data.get('player')
    choice = data.get('choice')

    if not player_id or not choice:
        return jsonify({'success': False, 'message': 'Player and choice required'}), 400

    success, message = game.select_trump(player_id, choice)
    return jsonify({'success': success, 'message': message})


@app.route('/api/hand/<player_id>', methods=['GET'])
def get_hand(player_id):
    game, game_id = _get_game_from_request()
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player = game.get_player(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Player not found'}), 404

    return jsonify({'success': True, 'hand': [str(c) for c in player.hand]})


@app.route('/api/play', methods=['POST'])
def play_card():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player_id = data.get('player_id') or data.get('player')
    card = data.get('card')

    if not player_id or card is None:
        return jsonify({'success': False, 'message': 'Player and card required'}), 400

    success, message = game.play_card(player_id, str(card))
    return jsonify({'success': success, 'message': message})


@app.route('/api/reset', methods=['POST'])
def reset_game():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    game.reset()
    return jsonify({'success': True, 'message': 'Game reset'})


if __name__ == '__main__':
    print('=' * 50)
    print('Sueca Game Server')
    print('=' * 50)
    print('Server running on http://localhost:5000')
    print('Use /api/create_game to create isolated rooms')
    print('Press Ctrl+C to stop')
    print()
    app.run(host='0.0.0.0', port=5000, debug=False)

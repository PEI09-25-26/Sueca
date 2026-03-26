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
from randomAgent.randomAgent import RandomAgent
from hybrid_vision_service import HybridVisionService
from hybrid_game_coordinator import HybridGameCoordinator
import logging
import requests
import threading
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path

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
        self.creator_id = None  # Track who created/owns the room
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
        self.match_history = []
        self.match_points = {'team1': 0, 'team2': 0}
        self.next_match_number = 1
        self.current_match_number = None
        # Dealer rotates each match. Initial dealer is WEST to preserve current first-match behavior.
        self.dealer_index = self.positions.index(Positions.WEST)
        self._push_state('game_reset')

    def _prepare_new_match(self, advance_dealer=False):
        self.deck = Deck()
        self.trump_card = None
        self.trump_suit = None
        self.team_scores = [0, 0]
        self.game_started = False
        self.current_round = 1
        self.round_plays = []
        self.round_suit = None
        self.current_player = None
        self.last_winner = None
        self.turn_order = []

        for player in self.players:
            player.hand = []

        if len(self.players) == self.max_players:
            if advance_dealer:
                self.dealer_index = (self.dealer_index + 1) % len(self.positions)
            self.phase = 'deck_cutting'
            self.deck.shuffle_deck()
            self.current_match_number = self.next_match_number
            self.next_match_number += 1
        else:
            self.phase = 'waiting'

    def _current_dealer_position(self):
        return self.positions[self.dealer_index]

    def _current_cutter_position(self):
        # Cutter is next clockwise from dealer in the configured position order.
        return self.positions[(self.dealer_index + 1) % len(self.positions)]

    def _get_player_by_position(self, position):
        for player in self.players:
            if player.position == position:
                return player
        return None

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
            self.current_match_number = self.next_match_number
            self.next_match_number += 1
            logger.info('Game %s ready for deck cutting', self.game_id)

        self._push_state('player_joined')
        return True, f'Joined as {player.position}', player.player_id

    def remove_player(self, actor_id, target_id):
        actor = self.get_player(actor_id)
        if not actor:
            return False, 'Actor player not found'

        if actor_id != self.creator_id:
            return False, 'Only the host can remove players'

        target = self.get_player(target_id)
        if not target:
            return False, 'Target player not found'

        if self.game_started:
            return False, 'Cannot remove players after game has started'

        if target_id == self.creator_id:
            return False, 'Host cannot remove themselves'

        team_key = 'team1' if target.position in self._TEAM1_POSITIONS else 'team2'
        self.available_team_positions[team_key].append(target.position)
        
        self.players.remove(target)
        if target in self.teams[0]:
            self.teams[0].remove(target)
        else:
            self.teams[1].remove(target)
        
        if target_id in self.scores:
            del self.scores[target_id]

        logger.info('Player %s was removed from game %s by host %s', target.player_name, self.game_id, actor.player_name)

        self._push_state('player_removed')
        return True, f'Player {target.player_name} removed successfully'

    def get_player(self, player_id):
        for player in self.players:
            if getattr(player, 'player_id', None) == player_id:
                return player
        return None

    def cut_deck(self, player_id, cut_index):
        player = self.get_player(player_id)
        if not player:
            return False, 'Player not found'

        required_cutter = self._current_cutter_position()
        if player.position != required_cutter:
            return False, f'Only {required_cutter.name} player can cut deck'

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

        required_selector = self._current_dealer_position()
        if player.position != required_selector:
            return False, f'Only {required_selector.name} player can select trump'

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

        self._deal_cards(player)  # Pass dealer/selector so they receive the trump card
        self.phase = 'playing'
        self.game_started = True

        self._push_state('trump_selected')
        return True, f'Trump card is {CardMapper.get_card(self.trump_card)}'

    def select_trump_by_card(self, player_id, trump_card_id):
        player = self.get_player(player_id)
        if not player:
            return False, 'Player not found'

        required_selector = self._current_dealer_position()
        if player.position != required_selector:
            return False, f'Only {required_selector.name} player can select trump'

        if self.phase != 'trump_selection':
            return False, 'Not in trump selection phase'

        try:
            trump_card_id = int(trump_card_id)
        except (TypeError, ValueError):
            return False, 'Invalid trump card id'

        self.trump_card = trump_card_id
        self.trump_suit = CardMapper.get_card_suit(self.trump_card)

        # Keep deck consistency if detected card exists in the shuffled deck.
        if trump_card_id in self.deck.cards:
            self.deck.cards.remove(trump_card_id)

        logger.info(
            'Trump selected by capture by %s in game %s: %s',
            player.player_name,
            self.game_id,
            CardMapper.get_card(self.trump_card)
        )

        self._deal_cards(player)
        self.phase = 'playing'
        self.game_started = True

        self._push_state('trump_selected_capture')
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
            return False, f'Waiting for {self._current_cutter_position().name} player to cut deck'

        if self.phase == 'trump_selection':
            return False, f"Waiting for {self._current_dealer_position().name} player to select trump (top/bottom)"

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

            match_winner_team = None
            if self.team_scores[0] > self.team_scores[1]:
                match_winner_team = 'team1'
                self.match_points['team1'] += 1
            elif self.team_scores[1] > self.team_scores[0]:
                match_winner_team = 'team2'
                self.match_points['team2'] += 1

            self.match_history.append({
                'match_number': self.current_match_number,
                'winner_team': match_winner_team,
                'winner_label': 'Team 1 (N/S)' if match_winner_team == 'team1' else ('Team 2 (E/W)' if match_winner_team == 'team2' else 'draw'),
                'team_scores': {'team1': self.team_scores[0], 'team2': self.team_scores[1]},
                'finished_at': datetime.now(timezone.utc).isoformat(),
            })
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

    def play_card_hybrid_capture(self, player_id, card_str):
        """
        Hybrid mode play: trust the physically captured card.
        Hand membership and follow-suit are not enforced here because
        physical dealing can differ from backend synthetic dealing.
        """
        player = self.get_player(player_id)
        if not player:
            return False, 'Player not found'

        if self.current_player != player:
            return False, f'Not your turn! Waiting for {self.current_player.player_name}'

        try:
            card = int(card_str)
        except (TypeError, ValueError):
            return False, 'Invalid card'

        if card in player.hand:
            player.hand.remove(card)

        self.round_plays.append({
            'player_id': player.player_id,
            'player_name': player.player_name,
            'card': str(card),
            'position': str(player.position)
        })

        if len(self.round_plays) == 1:
            self.round_suit = CardMapper.get_card_suit(card)

        logger.info('[HYBRID] %s played %s in game %s', player.player_name, CardMapper.get_card(card), self.game_id)

        current_index = self.turn_order.index(player)
        if current_index + 1 < len(self.turn_order):
            self.current_player = self.turn_order[current_index + 1]

        event = {
            'type': 'card_played',
            'player': player.player_name,
            'player_id': player.player_id,
            'card': str(card),
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

    def rematch(self):
        if len(self.players) < self.max_players:
            return False, f'Need {self.max_players} players for rematch'

        if self.phase not in ('finished', 'waiting'):
            return False, 'Rematch is only available after a finished game'

        self._prepare_new_match(advance_dealer=True)
        self._push_state('rematch_ready')
        return True, f'Rematch #{self.current_match_number} ready'

    def get_state(self):
        cutter_position = self._current_cutter_position()
        selector_position = self._current_dealer_position()
        cutter_player = self._get_player_by_position(cutter_position)
        selector_player = self._get_player_by_position(selector_position)

        cutter_player_name = cutter_player.player_name if cutter_player else None
        cutter_player_id = cutter_player.player_id if cutter_player else None
        selector_player_name = selector_player.player_name if selector_player else None
        selector_player_id = selector_player.player_id if selector_player else None

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
            # Backward-compatible keys consumed by existing clients.
            'north_player': cutter_player_name,
            'north_player_id': cutter_player_id,
            'west_player': selector_player_name,
            'west_player_id': selector_player_id,
            # Explicit role keys for newer clients.
            'cutter_player': cutter_player_name,
            'cutter_player_id': cutter_player_id,
            'cutter_position': cutter_position.name,
            'trump_selector_player': selector_player_name,
            'trump_selector_player_id': selector_player_id,
            'trump_selector_position': selector_position.name,
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
            'match_points': self.match_points,
            'matches_played': len(self.match_history),
            'current_match_number': self.current_match_number,
            'last_match': self.match_history[-1] if self.match_history else None,
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

def create_random_bot(bot_name, position=None, game_id=None):
    agent = RandomAgent(bot_name)
    agent.position = position
    agent.game_id = game_id
    return agent

class BotFactory:
    """Factory for creating different types of bots."""
    
    _bot_types = {
        'random': create_random_bot,
    }
    
    @classmethod
    def register_bot(cls, bot_type, factory_function):
        """Register a new bot type that can be created."""
        cls._bot_types[bot_type.lower()] = factory_function
    
    @classmethod
    def create_bot(cls, bot_name, position, game_id, difficulty='random'):
        """Create a bot of the specified type and return the agent."""
        bot_type = difficulty.lower()
        if bot_type not in cls._bot_types:
            return None
        
        factory_function = cls._bot_types[bot_type]
        agent = factory_function(bot_name, position, game_id)
        return agent
    
    @classmethod
    def get_available_bots(cls):
        """Return list of available bot types."""
        return list(cls._bot_types.keys())

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

            game.creator_id = player_id  # Creator is the first player of this room
            self.games[game_id] = game
            return True, message, game_id, player_id

manager = GameManager()

# Shared hybrid recognition sessions by game_id.
_HYBRID_CV12_ROOT = Path(__file__).resolve().parent.parent / "ComputerVision_1.2"
hybrid_vision = HybridVisionService(templates_root=None, cv12_root=_HYBRID_CV12_ROOT)
hybrid_coordinator = HybridGameCoordinator()


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


@app.route('/api/room/<game_id>/history', methods=['GET'])
def get_room_history(game_id):
    """Get all finished matches for a room."""
    game = manager.get_game(game_id)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    return jsonify({
        'success': True,
        'game_id': game_id,
        'matches_played': len(game.match_history),
        'history': game.match_history,
    })


@app.route('/api/room/<game_id>/match_points', methods=['GET'])
def get_room_match_points(game_id):
    """Get number of match wins per team for a room (1 win = 1 point)."""
    game = manager.get_game(game_id)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    return jsonify({
        'success': True,
        'game_id': game_id,
        'points': {
            'team1': game.match_points['team1'],
            'team2': game.match_points['team2'],
        },
        'teams': {
            'team1': [p.player_name for p in game.teams[0]],
            'team2': [p.player_name for p in game.teams[1]],
        },
        'matches_played': len(game.match_history),
    })


@app.route('/api/room/<game_id>/rematch', methods=['POST'])
def start_room_rematch(game_id):
    """Start a new match in the same room with the same 4 players/positions."""
    game = manager.get_game(game_id)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    success, message = game.rematch()
    if not success:
        return jsonify({'success': False, 'message': message}), 400

    return jsonify({'success': True, 'message': message, 'state': game.get_state()})


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
    if success and game.creator_id is None:
        game.creator_id = player_id
    return jsonify({'success': success, 'message': message, 'game_id': game_id, 'player_id': player_id})

@app.route('/api/change_position', methods=['POST'])
def change_position():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player_id = data.get('player_id') or data.get('player')
    new_position = data.get('position')

    if not player_id or not new_position:
        return jsonify({'success': False, 'message': 'Player and new position required'}), 400

    player = game.get_player(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Player not found'}), 404

    if game.game_started:
        return jsonify({'success': False, 'message': 'Cannot change position after game has started'}), 400
    
    normalized_new_position = game._normalize_position(new_position)
    if not normalized_new_position:
        return jsonify({'success': False, 'message': 'Invalid position. Choose NORTH, SOUTH, EAST, or WEST'}), 400

    if player.position == normalized_new_position:
        return jsonify({'success': True, 'message': 'Position unchanged', 'state': game.get_state()}), 200

    # If new position occupied by another player, reject change
    for p in game.players:
        if getattr(p, 'player_id', None) != player_id and p.position == normalized_new_position:
            return jsonify({'success': False, 'message': f'Position {new_position} is already taken by {p.player_name}'}), 400

    old_position = player.position
    old_team_key = 'team1' if old_position in game._TEAM1_POSITIONS else 'team2'
    new_team_key = 'team1' if normalized_new_position in game._TEAM1_POSITIONS else 'team2'

    # Free old slot
    if old_position not in game.available_team_positions[old_team_key]:
        game.available_team_positions[old_team_key].append(old_position)

    # Reserve new slot
    if normalized_new_position not in game.available_team_positions[new_team_key]:
        return jsonify({'success': False, 'message': f'Position {new_position} is not available'}), 400
    game.available_team_positions[new_team_key].remove(normalized_new_position)

    # Move the same player object between teams if needed
    game.teams[0] = [p for p in game.teams[0] if getattr(p, 'player_id', None) != player_id]
    game.teams[1] = [p for p in game.teams[1] if getattr(p, 'player_id', None) != player_id]
    player.position = normalized_new_position
    if new_team_key == 'team1':
        game.teams[0].append(player)
    else:
        game.teams[1].append(player)

    game._push_state('position_changed')
    return jsonify({'success': True, 'message': f'Position changed to {player.position.name}', 'state': game.get_state()})

@app.route('/api/add_bot', methods=['POST'])
def add_bot():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    # Only the room creator can add bots
    requester_id = data.get('player_id')
    if not requester_id:
        return jsonify({'success': False, 'message': 'player_id required'}), 400
    if game.creator_id != requester_id:
        return jsonify({'success': False, 'message': 'Only room creator can add bots'}), 403
    position = data.get('position')
    if not position:
        return jsonify({'success': False, 'message': 'Position required'}), 400

    if game.game_started:
        return jsonify({'success': False, 'message': 'Cannot add bots after game has started'}), 400

    # Extract bot details from request
    bot_name = data.get('name', f'Bot_{position}')
    difficulty = data.get('difficulty', 'random')
    
    # Use factory to create bot
    agent = BotFactory.create_bot(bot_name, position, game_id, difficulty)
    if not agent:
        available = ', '.join(BotFactory.get_available_bots())
        return jsonify({
            'success': False, 
            'message': f'Unknown bot type. Available: {available}'
        }), 400
    
    # Wait a moment for the bot to join through the API
    time.sleep(0.5)
    
    # Find the bot player that just joined
    bot_player = None
    for p in game.players:
        if p.player_name == bot_name:
            bot_player = p
            break
    
    if bot_player:
        return jsonify({
            'success': True, 
            'message': f'Bot {bot_name} added at position {position}', 
            'game_id': game_id, 
            'player_id': bot_player.player_id
        })
    else:
        return jsonify({
            'success': True,
            'message': f'Bot {bot_name} is joining...',
            'game_id': game_id,
            'player_id': None
        })


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


@app.route('/api/remove_player', methods=['POST'])
@app.route('/api/the_council_has_decided_your_fate', methods=['POST'])
def remove_player_endpoint():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    actor_id = data.get('actor_id')
    target_id = data.get('target_id')

    if not actor_id or not target_id:
        return jsonify({'success': False, 'message': 'Both actor_id and target_id are required'}), 400

    success, message = game.remove_player(actor_id, target_id)
    return jsonify({'success': success, 'message': message})


@app.route('/api/reset', methods=['POST'])
def reset_game():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    game.reset()
    return jsonify({'success': True, 'message': 'Game reset'})


@app.route('/api/hybrid/session/reset', methods=['POST'])
def reset_hybrid_session():
    data = request.get_json() or {}
    game_id = data.get('game_id') or manager.default_game_id
    target_count = data.get('target_count', 10)

    try:
        target_count = int(target_count)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'target_count must be an integer'}), 400

    session = hybrid_vision.reset_session(game_id, target_count)
    return jsonify({
        'success': True,
        'game_id': game_id,
        'target_count': session.target_count,
        'confirmed_count': len(session.cards),
        'done': False,
        'cards': [],
    })


@app.route('/api/hybrid/session/status', methods=['GET'])
def get_hybrid_session_status():
    game_id = request.args.get('game_id') or manager.default_game_id
    target_count = request.args.get('target_count', default=10, type=int)
    return jsonify(hybrid_vision.get_status_payload(game_id, target_count))


@app.route('/api/hybrid/recognize_card', methods=['POST'])
def recognize_hybrid_card():
    data = request.get_json() or {}
    game_id = data.get('game_id') or manager.default_game_id
    target_count = data.get('target_count', 10)
    frame_base64 = data.get('frame_base64')

    if not frame_base64:
        return jsonify({'success': False, 'message': 'frame_base64 is required'}), 400

    try:
        target_count = int(target_count)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'target_count must be an integer'}), 400

    payload = hybrid_vision.process_frame(game_id=game_id, frame_base64=frame_base64, target_count=target_count)
    return jsonify(payload)


def _players_meta(game):
    return {
        p.player_id: {
            'name': p.player_name,
            'position': str(p.position),
        }
        for p in game.players
    }


def _maybe_skip_hybrid_cut(game, room):
    """Hybrid mode does not use the deck cutting step."""
    if not game or not room:
        return
    if game.phase != 'deck_cutting':
        return
    if not room.host_player_id and not room.player_roles:
        return

    game.phase = 'trump_selection'
    game._push_state('hybrid_cut_skipped')
    logger.info('[HYBRID] Skipped deck_cutting and moved game %s to trump_selection', game.game_id)


def _autofill_missing_real_players_for_hybrid(game):
    """Ensure hybrid rooms always have 4 players by adding real placeholders."""
    if not game:
        return
    if len(game.players) >= game.max_players:
        return
    if game.phase == 'finished':
        return

    # Keep deterministic seat fill so host/device mappings remain stable.
    for position in game.positions:
        if len(game.players) >= game.max_players:
            break
        if game._get_player_by_position(position):
            continue

        base_name = f'Real_{position.name}'
        candidate = base_name
        idx = 2
        existing_names = {p.player_name for p in game.players}
        while candidate in existing_names:
            candidate = f'{base_name}_{idx}'
            idx += 1

        success, message, _ = game.add_player(candidate, position.name)
        if success:
            logger.info('[HYBRID] Auto-added missing real player %s at %s in game %s', candidate, position.name, game.game_id)
        else:
            logger.warning('[HYBRID] Failed auto-adding player at %s in game %s: %s', position.name, game.game_id, message)

    if len(game.players) == game.max_players:
        game._push_state('hybrid_real_players_autofilled')


@app.route('/api/hybrid/register_player', methods=['POST'])
def hybrid_register_player():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player_id = data.get('player_id')
    role = data.get('role', 'real')
    is_host = bool(data.get('is_host', False))

    if not player_id:
        return jsonify({'success': False, 'message': 'player_id is required'}), 400

    if not game.get_player(player_id):
        return jsonify({'success': False, 'message': 'Player not found in this game'}), 404

    room = hybrid_coordinator.register_player(game_id, player_id, role, is_host)
    _autofill_missing_real_players_for_hybrid(game)
    _maybe_skip_hybrid_cut(game, room)
    return jsonify({'success': True, 'state': hybrid_coordinator.to_payload(room, _players_meta(game))})


@app.route('/api/hybrid/state', methods=['GET'])
def hybrid_state():
    game_id = request.args.get('game_id') or manager.default_game_id
    game = manager.get_game(game_id)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    room = hybrid_coordinator.get_room_state(game_id)
    _autofill_missing_real_players_for_hybrid(game)
    _maybe_skip_hybrid_cut(game, room)
    return jsonify({'success': True, 'state': hybrid_coordinator.to_payload(room, _players_meta(game))})


@app.route('/api/hybrid/deal/reset', methods=['POST'])
def hybrid_deal_reset():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    host_player_id = data.get('player_id')
    cards_per_virtual = data.get('cards_per_virtual', 10)

    if not host_player_id:
        return jsonify({'success': False, 'message': 'player_id is required'}), 400

    if game.phase != 'playing':
        return jsonify({
            'success': False,
            'message': 'Hybrid card assignment is only available after trump selection (playing phase)',
            'phase': game.phase,
        }), 409

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)
    if room.host_player_id and room.host_player_id != host_player_id:
        return jsonify({'success': False, 'message': 'Only host can reset deal'}), 403

    registered_virtual_ids = [
        pid for pid, role in room.player_roles.items()
        if role == 'virtual' and game.get_player(pid) is not None and pid != host_player_id
    ]

    if not (0 <= len(registered_virtual_ids) <= 3):
        return jsonify({'success': False, 'message': 'Hybrid mode supports up to 3 virtual players'}), 400

    room = hybrid_coordinator.reset_deal(
        game_id=game_id,
        host_player_id=host_player_id,
        virtual_player_ids=registered_virtual_ids,
        cards_per_virtual=cards_per_virtual,
    )
    return jsonify({'success': True, 'state': hybrid_coordinator.to_payload(room, _players_meta(game))})


@app.route('/api/hybrid/trump/confirm_capture', methods=['POST'])
def hybrid_confirm_trump_capture():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    host_player_id = data.get('host_player_id')
    frame_base64 = data.get('frame_base64')

    if not host_player_id or not frame_base64:
        return jsonify({'success': False, 'message': 'host_player_id and frame_base64 are required'}), 400

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)

    if game.phase != 'trump_selection':
        return jsonify({'success': False, 'message': 'Not in trump selection phase', 'phase': game.phase}), 409

    if room.host_player_id and host_player_id != room.host_player_id:
        return jsonify({'success': False, 'message': 'Only host can submit trump frame'}), 403

    selector = game._get_player_by_position(game._current_dealer_position())
    if selector is None:
        return jsonify({'success': False, 'message': 'Trump selector player not found'}), 400

    recognized = hybrid_vision.recognize_once(frame_base64)
    if recognized is None:
        return jsonify({'success': False, 'message': 'No valid card detected'}), 400

    success, message = game.select_trump_by_card(selector.player_id, recognized.card_id)
    if not success:
        return jsonify({'success': False, 'message': message}), 400

    return jsonify({
        'success': True,
        'message': message,
        'captured_card_id': recognized.card_id,
        'captured_display': recognized.display,
        'game_state': game.get_state(),
        'state': hybrid_coordinator.to_payload(room, _players_meta(game)),
    })


@app.route('/api/hybrid/deal/recognize', methods=['POST'])
def hybrid_deal_recognize():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    host_player_id = data.get('player_id')
    frame_base64 = data.get('frame_base64')
    target_player_id = data.get('target_player_id')

    if not host_player_id:
        return jsonify({'success': False, 'message': 'player_id is required'}), 400
    if not frame_base64:
        return jsonify({'success': False, 'message': 'frame_base64 is required'}), 400

    if game.phase != 'playing':
        return jsonify({
            'success': False,
            'recognized': False,
            'confirmed': False,
            'message': 'Waiting for trump selection to finish before dealing virtual cards',
            'phase': game.phase,
            'state': hybrid_coordinator.to_payload(hybrid_coordinator.get_room_state(game_id), _players_meta(game)),
        }), 409

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)
    if room.host_player_id and room.host_player_id != host_player_id:
        return jsonify({'success': False, 'message': 'Only host can process deal frames'}), 403

    recognized = hybrid_vision.recognize_once(frame_base64)
    if recognized is None:
        return jsonify({
            'success': True,
            'recognized': False,
            'confirmed': False,
            'message': 'No valid card detected',
            'state': hybrid_coordinator.to_payload(room, _players_meta(game)),
        })

    target = target_player_id or hybrid_coordinator.deal_next_target(game_id)
    if not target:
        return jsonify({
            'success': True,
            'recognized': True,
            'confirmed': False,
            'message': 'All virtual players already have their cards',
            'card': {'id': recognized.card_id, 'display': recognized.display},
            'state': hybrid_coordinator.to_payload(room, _players_meta(game)),
        })

    ok, message, room = hybrid_coordinator.add_deal_card(game_id, target, recognized.card_id)
    return jsonify({
        'success': True,
        'recognized': True,
        'confirmed': ok,
        'message': message,
        'target_player_id': target,
        'card': {
            'id': recognized.card_id,
            'rank': recognized.rank,
            'suit': recognized.suit_name,
            'suit_symbol': recognized.suit_symbol,
            'drawable_key': recognized.drawable_key,
            'display': recognized.display,
        },
        'state': hybrid_coordinator.to_payload(room, _players_meta(game)),
    })


@app.route('/api/hybrid/virtual/select_card', methods=['POST'])
def hybrid_virtual_select_card():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player_id = data.get('player_id')
    card = data.get('card')

    if not player_id or card is None:
        return jsonify({'success': False, 'message': 'player_id and card are required'}), 400

    try:
        card = int(card)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'card must be an integer'}), 400

    ok, message, room = hybrid_coordinator.select_virtual_card(game_id, player_id, card)
    status = 200 if ok else 400
    return jsonify({'success': ok, 'message': message, 'state': hybrid_coordinator.to_payload(room, _players_meta(game))}), status


@app.route('/api/hybrid/pending_play', methods=['GET'])
def hybrid_pending_play():
    game_id = request.args.get('game_id') or manager.default_game_id
    game = manager.get_game(game_id)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    room = hybrid_coordinator.get_room_state(game_id)
    payload = hybrid_coordinator.to_payload(room, _players_meta(game))
    return jsonify({'success': True, 'pending': payload.get('pending_virtual_play'), 'state': payload})


@app.route('/api/hybrid/play/confirm_capture', methods=['POST'])
def hybrid_confirm_capture():
    data = request.get_json() or {}
    game, game_id = _get_game_from_request(data)
    if not game:
        return jsonify({'success': False, 'message': f'Game {game_id} not found'}), 404

    player_id = data.get('player_id')
    host_player_id = data.get('host_player_id')
    frame_base64 = data.get('frame_base64')

    if not player_id or not frame_base64:
        return jsonify({'success': False, 'message': 'player_id and frame_base64 are required'}), 400

    room = hybrid_coordinator.get_room_state(game_id)
    _maybe_skip_hybrid_cut(game, room)
    if room.host_player_id:
        if not host_player_id:
            return jsonify({'success': False, 'message': 'host_player_id is required for capture confirmation'}), 400
        if host_player_id != room.host_player_id:
            return jsonify({'success': False, 'message': 'Only host can submit capture frames'}), 403

    recognized = hybrid_vision.recognize_once(frame_base64)
    if recognized is None:
        return jsonify({'success': False, 'message': 'No valid card detected'}), 400

    recognized_card = str(recognized.card_id)
    room = hybrid_coordinator.get_room_state(game_id)
    pending = room.pending_virtual_play

    # If this player has a pending virtual card, enforce exact match.
    if pending and pending.player_id == player_id:
        if int(recognized.card_id) != int(pending.card_id):
            return jsonify({
                'success': False,
                'message': f'Captured card {recognized.display} does not match selected virtual card',
                'expected_card_id': pending.card_id,
                'captured_card_id': recognized.card_id,
            }), 400

    success, message = game.play_card_hybrid_capture(player_id, recognized_card)
    if not success:
        return jsonify({'success': False, 'message': message, 'captured_card_id': recognized.card_id}), 400

    room = hybrid_coordinator.confirm_play_success(game_id, player_id, recognized.card_id)
    return jsonify({
        'success': True,
        'message': message,
        'captured_card_id': recognized.card_id,
        'captured_display': recognized.display,
        'state': hybrid_coordinator.to_payload(room, _players_meta(game)),
        'game_state': game.get_state(),
    })


if __name__ == '__main__':
    print('=' * 50)
    print('Sueca Game Server')
    print('=' * 50)
    print('Server running on http://localhost:5000')
    print('Use /api/create_game to create isolated rooms')
    print('Press Ctrl+C to stop')
    print()
    app.run(host='0.0.0.0', port=5000, debug=False)

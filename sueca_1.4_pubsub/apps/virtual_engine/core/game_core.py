"""
Core game logic for Sueca virtual engine.
"""
from ..deck import Deck
from ..player import Player
from ..positions import Positions
from ..card_mapper import CardMapper
from ..agents.random_agent.random_agent import RandomAgent
from ..agents.weak_agent import WeakAgent
from apps.agents.agents import AverageAgent
from apps.agents.agents import SmartAgent
import logging
import os
import queue
import requests
import threading
import uuid
from datetime import datetime, timezone

from apps.emqx import mqtt_client
from ..event_publisher import publish_room_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from shared.firebase_client import get_firestore_db
    from firebase_admin import firestore as admin_firestore
except Exception:
    get_firestore_db = None
    admin_firestore = None

FIRESTORE_STATS_ENABLED = os.getenv("SUECA_FIRESTORE_STATS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
FIRESTORE_GAME_HISTORY_COLLECTION = os.getenv("SUECA_FIRESTORE_GAME_HISTORY_COLLECTION", "player_game_history")
FIRESTORE_PLAYER_STATS_COLLECTION = os.getenv("SUECA_FIRESTORE_PLAYER_STATS_COLLECTION", "player_stats")
FIRESTORE_USERS_COLLECTION = os.getenv("SUECA_FIRESTORE_USERS_COLLECTION", "users")


ACTIVE_BOT_THREADS: dict[str, threading.Thread] = {}


class _EventDispatcher:
    """Best-effort async HTTP dispatcher to avoid blocking game critical paths."""

    def __init__(self, target_url: str, workers: int = 2, queue_size: int = 512):
        self.target_url = target_url
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=queue_size)
        self._workers: list[threading.Thread] = []
        self._stop = threading.Event()
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=64)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        for index in range(max(1, workers)):
            worker = threading.Thread(target=self._run, daemon=True, name=f"event-dispatcher-{index}")
            worker.start()
            self._workers.append(worker)

    def dispatch(self, payload: dict):
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            # Drop noisy events when under pressure to keep game loop responsive.
            logger.warning("Dropping event because dispatcher queue is full")

    def _run(self):
        while not self._stop.is_set():
            try:
                payload = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue

            try:
                self._session.post(self.target_url, json=payload, timeout=0.3)
            except Exception:
                # Event delivery is best-effort and must never block gameplay.
                pass
            finally:
                self._queue.task_done()


EVENT_DISPATCHER = _EventDispatcher("http://localhost:8000/game/event")


def launch_bot_thread(agent, game_id: str, bot_name: str) -> bool:
    """Start bot run loop in background and keep a reference by game/name."""
    key = f"{game_id}:{bot_name}"
    existing = ACTIVE_BOT_THREADS.get(key)
    if existing and existing.is_alive():
        return False

    def _run_bot_safely():
        try:
            agent.run()
        except Exception:
            logger.exception('Bot thread crashed for %s in game %s', bot_name, game_id)

    thread = threading.Thread(target=_run_bot_safely, daemon=True, name=f"bot-{bot_name}-{game_id}")
    thread.start()
    ACTIVE_BOT_THREADS[key] = thread
    return True


class GameState:
    """Game state manager for a single room."""

    RESERVED_SEAT_SECONDS = 10

    def __init__(self, game_id):
        self.game_id = game_id
        self._play_lock = threading.Lock()
        self.reset()

    def reset(self):
        self.deck = Deck()
        self.players = []
        self.max_players = 4
        self.creator_id = None
        self.is_public = True
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
        self.reservations = {} # position -> {uid, expires}
        self.game_started = False
        self.phase = 'waiting'  # waiting, deck_cutting, trump_selection, playing, finished
        self.current_round = 1
        self.round_plays = []
        self.round_suit = None
        self.round_resolving = False
        self.current_player = None
        self.last_winner = None
        self.turn_order = []
        self.match_history = []
        self.match_points = {'team1': 0, 'team2': 0}
        self.next_match_number = 1
        self.current_match_number = None
        self.starting_hands = {}
        self._published_match_ids = set()
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
        self.round_resolving = False
        self.current_player = None
        self.last_winner = None
        self.turn_order = []
        self.starting_hands = {}

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

    def _pick_first_available_position(self):
        ordered_positions = [
            Positions.NORTH,
            Positions.EAST,
            Positions.SOUTH,
            Positions.WEST,
        ]
        for position in ordered_positions:
            team_key = 'team1' if position in self._TEAM1_POSITIONS else 'team2'
            if position in self.available_team_positions[team_key]:
                return position
        return None

    def _resolve_player_id_from_firestore(self, name: str | None):
        if not name or get_firestore_db is None:
            return None

        try:
            db = get_firestore_db()
        except Exception:
            logger.exception("Failed to initialize Firestore client for player lookup")
            return None

        collection = db.collection(FIRESTORE_USERS_COLLECTION)
        # Support both generated name and username fields during lookup.
        for field in ("name", "username"):
            try:
                docs = list(collection.where(field, "==", name).limit(1).stream())
            except Exception:
                logger.exception("Failed to query Firestore users by %s", field)
                return None

            if not docs:
                continue

            data = docs[0].to_dict() or {}
            friend_code = data.get("friendCode")
            if friend_code:
                return str(friend_code)
            return None

        return None

    def add_player(self, name, position_choice, player_id=None):
        if len(self.players) >= self.max_players:
            return False, 'Game is full', None

        if not player_id:
            player_id = self._resolve_player_id_from_firestore(name)

        if player_id and self.get_player(player_id):
            return False, 'Player already in game', None

        # Position is OPTIONAL - allows entering room before choosing a seat
        position = self._normalize_position(position_choice)
        
        if position:
            team_key = 'team1' if position in self._TEAM1_POSITIONS else 'team2'
            if position not in self.available_team_positions[team_key]:
                # Check if it's reserved for this player
                reservation = self.reservations.get(position.name)
                if reservation:
                    # Check expiration
                    if datetime.now(timezone.utc).timestamp() > reservation['expires']:
                         del self.reservations[position.name]
                         # Now it's effectively free, but wait, it's still not in available_team_positions
                         # This logic needs to be careful.
                         pass
                    elif reservation['uid'] != player_id: # Assuming player_id is the uid here? 
                        # In this system player_id is often the UID if authenticated.
                        return False, f'Position {position.name} is reserved', None
                    else:
                        # Reserved for this player!
                        del self.reservations[position.name]
                else:
                    return False, f'Position {position.name} is already taken', None

        player = Player(name, player_id)
        player.position = position
        self.players.append(player)
        self.scores[player.player_id] = 0

        if position:
            team_key = 'team1' if position in self._TEAM1_POSITIONS else 'team2'
            if position in self.available_team_positions[team_key]:
                self.available_team_positions[team_key].remove(position)
            
            if team_key == 'team1':
                self.teams[0].append(player)
            else:
                self.teams[1].append(player)
            logger.info('Player %s joined game %s at position %s', name, self.game_id, player.position)
        else:
            logger.info('Player %s joined game %s without position', name, self.game_id)

        # Check if we can start deck cutting - only when 4 players are seated
        seated_players = [p for p in self.players if p.position is not None]
        if len(seated_players) == self.max_players and not self.game_started:
            self.phase = 'deck_cutting'
            self.deck.shuffle_deck()
            self.current_match_number = self.next_match_number
            self.next_match_number += 1
            logger.info('Game %s ready for deck cutting', self.game_id)

        self._push_state('player_joined')
        return True, f'Joined as {player.position}' if position else 'Joined room', player.player_id

    def reserve_seat(self, uid, position_choice):
        position = self._normalize_position(position_choice)
        if not position:
            return False, 'Invalid position'
        
        team_key = 'team1' if position in self._TEAM1_POSITIONS else 'team2'
        if position not in self.available_team_positions[team_key]:
            return False, 'Position already taken or reserved'
        
        # Reserve it!
        self.available_team_positions[team_key].remove(position)
        self.reservations[position.name] = {
            'uid': uid,
            'expires': datetime.now(timezone.utc).timestamp() + self.RESERVED_SEAT_SECONDS
        }
        self._push_state('seat_reserved')
        return True, 'Seat reserved'

    def release_reserved_seat(self, uid, position_choice):
        position = self._normalize_position(position_choice)
        if not position:
            return False, 'Invalid position'

        reservation = self.reservations.get(position.name)
        if reservation and str(reservation.get('uid')) not in {str(uid), 'None'}:
            return False, 'Seat reserved by another player'

        if reservation:
            del self.reservations[position.name]

        occupied_player = self._get_player_by_position(position)
        if occupied_player is None:
            team_key = 'team1' if position in self._TEAM1_POSITIONS else 'team2'
            if position not in self.available_team_positions[team_key]:
                self.available_team_positions[team_key].append(position)

        self._push_state('seat_released')
        return True, 'Seat released'

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

        if target.position:
            team_key = 'team1' if target.position in self._TEAM1_POSITIONS else 'team2'
            if target.position not in self.available_team_positions[team_key]:
                self.available_team_positions[team_key].append(target.position)
        
        self.players.remove(target)
        if target in self.teams[0]:
            self.teams[0].remove(target)
        elif target in self.teams[1]:
            self.teams[1].remove(target)
        
        if target_id in self.scores:
            del self.scores[target_id]

        logger.info('Player %s was removed from game %s by host %s', target.player_name, self.game_id, actor.player_name)

        self._push_state('player_removed')
        return True, f'Player {target.player_name} removed successfully'

    def leave(self, player_id):
        """
        Voluntary leave by a player. This removes the player from the room,
        frees their seat, reassigns creator if needed, and emits state.
        Returns (success: bool, message: str).
        """
        target = self.get_player(player_id)
        if not target:
            return False, 'Player not found'

        # Do not allow leaving while a game is actively in progress
        if self.game_started and self.phase != 'finished':
            return False, 'Cannot leave while game is in progress'

        if target.position:
            team_key = 'team1' if target.position in self._TEAM1_POSITIONS else 'team2'
            # Free up the position
            if target.position not in self.available_team_positions[team_key]:
                self.available_team_positions[team_key].append(target.position)

        try:
            self.players.remove(target)
        except ValueError:
            pass

        if target in self.teams[0]:
            self.teams[0].remove(target)
        elif target in self.teams[1]:
            self.teams[1].remove(target)

        if target.player_id in self.scores:
            del self.scores[target.player_id]

        # If the leaving player was the creator, assign a new creator if any players remain
        if self.creator_id == player_id:
            if len(self.players) > 0:
                # pick first player as new creator
                new_creator = self.players[0]
                self.creator_id = getattr(new_creator, 'player_id', None)
            else:
                self.creator_id = None

        logger.info('Player %s left game %s', target.player_name, self.game_id)
        self._push_state('player_left')
        return True, f'Player {target.player_name} left the game'

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

        self._snapshot_starting_hands()

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

    def _snapshot_starting_hands(self):
        self.starting_hands = {
            player.player_id: [str(card) for card in player.hand]
            for player in self.players
            if getattr(player, "player_id", None)
        }

    def _player_team_key(self, player):
        if player in self.teams[0]:
            return "team1"
        if player in self.teams[1]:
            return "team2"
        return None

    def _build_game_history_payload(self, player, match_entry):
        team_scores = match_entry.get("team_scores") or {}
        position = player.position.name if getattr(player, "position", None) else None
        return {
            "player_id": player.player_id,
            "game_id": self.game_id,
            "position": position,
            "starting_hand": self.starting_hands.get(player.player_id, []),
            "trump_suit": self.trump_suit,
            "match_number": match_entry.get("match_number"),
            "finished_at": match_entry.get("finished_at"),
            "game_stats": {
                "team1_points": team_scores.get("team1", 0),
                "team2_points": team_scores.get("team2", 0),
                "winner": match_entry.get("winner_label"),
            },
        }

    def _build_player_stats_update(self, player, match_entry):
        winner_team = match_entry.get("winner_team")
        team_key = self._player_team_key(player)
        is_draw = winner_team is None
        is_win = (team_key is not None and winner_team == team_key)
        is_loss = (team_key is not None and winner_team != team_key and not is_draw)

        return {
            "player_id": player.player_id,
            "games_played": admin_firestore.Increment(1),
            "wins": admin_firestore.Increment(1 if is_win else 0),
            "losses": admin_firestore.Increment(1 if is_loss else 0),
            "draws": admin_firestore.Increment(1 if is_draw else 0),
        }

    def _publish_match_stats(self, match_entry):
        if not FIRESTORE_STATS_ENABLED:
            return
        if get_firestore_db is None or admin_firestore is None:
            logger.warning("Firestore client not available; skipping stats publish")
            return

        match_number = match_entry.get("match_number")
        match_id = f"{self.game_id}:{match_number}" if match_number is not None else f"{self.game_id}:unknown"
        if match_id in self._published_match_ids:
            return

        try:
            db = get_firestore_db()
        except Exception:
            logger.exception("Failed to initialize Firestore client")
            return

        for player in self.players:
            if not getattr(player, "player_id", None):
                continue
            history_doc_id = f"{player.player_id}_{self.game_id}_{match_number}" if match_number is not None else f"{player.player_id}_{self.game_id}"
            history_ref = db.collection(FIRESTORE_GAME_HISTORY_COLLECTION).document(history_doc_id)
            try:
                if history_ref.get().exists:
                    continue
                history_payload = self._build_game_history_payload(player, match_entry)
                history_ref.set(history_payload)
                stats_ref = db.collection(FIRESTORE_PLAYER_STATS_COLLECTION).document(player.player_id)
                stats_ref.set(self._build_player_stats_update(player, match_entry), merge=True)
            except Exception:
                logger.exception("Failed to publish match stats for player %s (game %s)", player.player_id, self.game_id)

        self._published_match_ids.add(match_id)

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
        with self._play_lock:
            winner = self._determine_round_winner()
            if not winner:
                self.round_resolving = False
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
            self.round_resolving = False

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

                match_entry = {
                    'match_number': self.current_match_number,
                    'winner_team': match_winner_team,
                    'winner_label': 'Team 1 (N/S)' if match_winner_team == 'team1' else ('Team 2 (E/W)' if match_winner_team == 'team2' else 'draw'),
                    'team_scores': {'team1': self.team_scores[0], 'team2': self.team_scores[1]},
                    'finished_at': datetime.now(timezone.utc).isoformat(),
                }
                self.match_history.append(match_entry)
                self._publish_match_stats(match_entry)
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
        EVENT_DISPATCHER.dispatch(event)

        # Strict MQTT clients rely on this post-resolution state update.
        self._push_state('round_end')

    def play_card(self, player_id, card_str):
        with self._play_lock:
            player = self.get_player(player_id)
            if not player:
                return False, 'Player not found'

            if self.round_resolving or len(self.round_plays) >= 4:
                return False, 'Round resolving, wait for next turn'

            if self.current_player != player:
                waiting_for = self.current_player.player_name if self.current_player else 'next player'
                return False, f'Not your turn! Waiting for {waiting_for}'

            # Safety guard: one play per player per trick.
            if any(play.get('player_id') == player.player_id for play in self.round_plays):
                return False, 'You already played this round'

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
        EVENT_DISPATCHER.dispatch(event)

        if len(self.round_plays) == 4:
            self.current_player = None
            self.round_resolving = True
            threading.Timer(1.69, self._finish_round).start()

        # Keep MQTT/state consumers in sync after every accepted play.
        self._push_state('card_played')

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
        # Clean up expired reservations
        now = datetime.now(timezone.utc).timestamp()
        to_remove = []
        for pos_name, res in self.reservations.items():
            if now > res['expires']:
                to_remove.append(pos_name)
        
        for pos_name in to_remove:
            self._restore_reservation_position(pos_name)

    def _restore_reservation_position(self, pos_name: str):
        reservation = self.reservations.pop(pos_name, None)
        if reservation is None:
            return

        pos = self._POSITION_MAP.get(pos_name.lower())
        if not pos:
            return

        if self._get_player_by_position(pos) is not None:
            return

        team_key = 'team1' if pos in self._TEAM1_POSITIONS else 'team2'
        if pos not in self.available_team_positions[team_key]:
            self.available_team_positions[team_key].append(pos)

    def get_state(self):
        # Clean up expired reservations
        now = datetime.now(timezone.utc).timestamp()
        to_remove = []
        for pos_name, res in self.reservations.items():
            if now > res['expires']:
                to_remove.append(pos_name)

        for pos_name in to_remove:
            self._restore_reservation_position(pos_name)

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
            'creator_id': self.creator_id,
            'is_public': getattr(self, 'is_public', True),
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
        state_snapshot = self.get_state() or {}
        event = {
            'type': event_type,
            'state': state_snapshot,
            'game_id': self.game_id,
        }
        EVENT_DISPATCHER.dispatch(event)

        try:
            if getattr(self, 'is_public', True):
                publish_room_event('room_updated', game_id=self.game_id, state=state_snapshot)
        except Exception:
            pass

        try:
            hands_by_player = {
                player.player_id: [str(card) for card in player.hand]
                for player in self.players
                if getattr(player, 'player_id', None)
            }
            topic = f'sueca/games/{self.game_id}/state'
            published = mqtt_client.publish_json(
                f'sueca/games/{self.game_id}/state',
                {
                    'event_type': event_type,
                    'game_id': self.game_id,
                    'state': state_snapshot,
                    'hands': hands_by_player,
                },
                retain=True,
            )
            if published:
                logger.info('Published state to MQTT topic %s (event=%s, round_plays=%s)', topic, event_type, len(state_snapshot.get('round_plays', [])))
            else:
                logger.warning('Failed to publish state to MQTT topic %s (event=%s, round_plays=%s)', topic, event_type, len(state_snapshot.get('round_plays', [])))
        except Exception:
            logger.exception('Unexpected error while publishing state to MQTT (event=%s, game_id=%s)', event_type, self.game_id)

    def _update_auth_status(self, player_id, status):
        """Update player status in Auth service."""
        try:
            # Only update if player_id looks like a real UID (not guest)
            if len(player_id) >= 20: 
                from shared.auth_client import issue_service_token
                token = threading.local().service_token = getattr(threading.local(), 'service_token', None)
                if not token:
                     # This is slow if done frequently, maybe cache it?
                     # For now, let's just assume we can get one.
                     pass 
                
                # We need the AUTH_SERVICE_URL
                from shared.config import SERVICES
                auth_url = f"{SERVICES.auth_service_url}/user/{player_id}/status"
                
                # Get a fresh token for control plane
                import asyncio
                # We are in a sync environment here... this is tricky.
                # Actually _EventDispatcher uses a background thread.
                
                def _do_update():
                    async def _async_update():
                        from shared.auth_client import issue_service_token
                        svc_token = await issue_service_token("virtual_engine", "control_plane")
                        if svc_token:
                            async with requests.Session() as s: # requests is not async...
                                # Use httpx instead?
                                pass
                    # I'll just use requests since it's already used here.
                    from shared.auth_client import AUTH_SERVICE_URL
                    # auth_client.issue_service_token is async.
                    # I'll skip the async for now and just do a simple requests call if I can get a token.
                    pass
                
                # Let's simplify: Gateway should probably handle this status update 
                # when it receives the player_joined event.
                pass
        except Exception:
            logger.exception("Failed to update status for %s", player_id)

def create_random_bot(bot_name, position=None, game_id=None):
    agent = RandomAgent(bot_name)
    agent.position = position
    agent.game_id = game_id
    return agent


def create_weak_bot(bot_name, position=None, game_id=None):
    agent = WeakAgent()
    agent.agent_name = bot_name
    agent.position = position
    agent.game_id = game_id
    return agent

def create_average_bot(bot_name, position=None, game_id=None):
    agent = AverageAgent()
    agent.agent_name = bot_name
    agent.position = position
    agent.game_id = game_id
    return agent

def create_smart_bot(bot_name, position=None, game_id=None):
    agent = SmartAgent()
    agent.agent_name = bot_name
    agent.position = position
    agent.game_id = game_id
    return agent

class BotFactory:
    """Factory for creating different types of bots."""
    
    _bot_types = {
        'random': create_random_bot,
        'weak': create_weak_bot,
        'weak_agent': create_weak_bot,
        'average': create_average_bot,
        'average_agent': create_average_bot,
        'smart': create_smart_bot,
        'smart_agent': create_smart_bot
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
            publish_room_event('room_created', game_id=game_id)
            return game_id

    def create_room_with_host(self, creator_name, position_choice=None, player_id=None):
        with self._lock:
            game_id = self._generate_game_id()
            game = GameState(game_id)
            success, message, player_id = game.add_player(creator_name, position_choice, player_id=player_id)
            if not success:
                return False, message, None, None

            game.creator_id = player_id
            self.games[game_id] = game
            publish_room_event('room_created', game_id=game_id)
            return True, message, game_id, player_id

    def delete_room(self, game_id: str):
        with self._lock:
            if game_id in self.games and game_id != self.default_game_id:
                del self.games[game_id]
                publish_room_event('room_deleted', game_id=game_id)
                return True
        return False

    def create_game(self, creator_name, position_choice, player_id=None):
        with self._lock:
            game_id = self._generate_game_id()
            game = GameState(game_id)
            success, message, player_id = game.add_player(creator_name, position_choice, player_id=player_id)
            if not success:
                return False, message, None

            game.creator_id = player_id  # Creator is the first player of this room
            self.games[game_id] = game
            publish_room_event('room_created', game_id=game_id)
            return True, message, game_id, player_id

manager = GameManager()

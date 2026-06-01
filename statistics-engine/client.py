"""
Simple CLI client for Sueca game
Supports room creation/join by game ID and manual position selection.
"""

import requests
import os
import time
import json
from threading import Thread, Lock
from urllib.parse import urlparse
from apps.virtual_engine.card_mapper import CardMapper

try:
    from paho.mqtt import client as mqtt_client
except Exception:
    mqtt_client = None

GATEWAY_URL = os.getenv('SUECA_GATEWAY_URL', 'http://localhost:8080').rstrip('/')
GAME_MODE = os.getenv('SUECA_GAME_MODE', 'virtual').strip().lower() or 'virtual'
MQTT_EVENTS_ENABLED = os.getenv('SUECA_MQTT_EVENTS', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', urlparse(GATEWAY_URL).hostname or '127.0.0.1')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_USE_AUTH = os.getenv('MQTT_USE_AUTH', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
HTTP_POLL_INTERVAL = float(os.getenv('SUECA_HTTP_POLL_INTERVAL', '2'))
SUPPORTED_BOT_TYPES = {'random', 'weak', 'weak_agent', 'average', 'average_agent'}
POSITION_REFRESH = '__refresh__'


def normalize_bot_type(value):
    if not value:
        return None
    normalized = value.strip().lower().replace('-', '_')
    aliases = {
        'r': 'random',
        'rand': 'random',
        'w': 'weak',
        'avg': 'average',
        'medium': 'average',
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in SUPPORTED_BOT_TYPES else None

class GameClient:
    def __init__(self):
        self.player_name = None
        self.player_id = None
        self.game_id = None
        self.position = None
        self.running = True
        self.my_hand = []
        self.display_lock = Lock()
        self.pause_updates = False
        self.mqtt_client = None
        self.mqtt_connected = False
        self.latest_state = None
        self.needs_refresh = True

    def clear_screen(self):
        os.system('clear' if os.name != 'nt' else 'cls')

    def set_room_mode(self, game_id, mode=GAME_MODE):
        try:
            requests.post(
                f'{GATEWAY_URL}/game/room_mode/{game_id}',
                json={'mode': mode},
                timeout=2,
            )
        except Exception:
            pass

    def _gateway_command(self, command, payload=None, game_id=None, mode=GAME_MODE, timeout=4):
        try:
            response = requests.post(
                f'{GATEWAY_URL}/game/command/{command}',
                json={
                    'game_id': game_id or self.game_id,
                    'mode': mode,
                    'payload': payload or {},
                },
                timeout=timeout,
            )
            data = response.json() if response.content else {}
            self.needs_refresh = True
            return data.get('success', False), data
        except Exception as error:
            return False, {'message': str(error)}

    def _gateway_error_message(self, gateway_data, default='Unknown error'):
        if isinstance(gateway_data, dict):
            if gateway_data.get('message'):
                return gateway_data.get('message')
            if gateway_data.get('detail'):
                return gateway_data.get('detail')
            nested = gateway_data.get('response')
            if isinstance(nested, dict):
                if nested.get('message'):
                    return nested.get('message')
                if nested.get('detail'):
                    return nested.get('detail')
        return default

    def _gateway_query(self, query_path, game_id=None, mode=GAME_MODE):
        try:
            params = {'mode': mode}
            if game_id or self.game_id:
                params['game_id'] = game_id or self.game_id
            response = requests.get(
                f'{GATEWAY_URL}/game/query/{query_path}',
                params=params,
                timeout=3,
            )
            data = response.json() if response.content else {}
            return data.get('success', False), data
        except Exception as error:
            return False, {'message': str(error)}

    def get_status(self, force=False):
        if MQTT_EVENTS_ENABLED:
            # Strict MQTT mode after joining a game: do not fallback to HTTP polling.
            if self.player_id and self.game_id:
                return self.latest_state
            # Pre-join bootstrap still uses HTTP to create/join rooms through gateway commands.
            if self.mqtt_connected and self.latest_state is not None:
                return self.latest_state

        ok, gateway_data = self._gateway_query('status', game_id=self.game_id)
        if not ok:
            return self.latest_state
        state = gateway_data.get('response')
        if state is not None:
            self.latest_state = state
            self.needs_refresh = False
        return state

    def create_game(self, name, position):
        ok, gateway_data = self._gateway_command('create_game', {'name': name, 'position': position})
        if not ok:
            return False, self._gateway_error_message(gateway_data), None, None
        data = gateway_data.get('response', {})
        success = data.get('success', False)
        message = data.get('message') if isinstance(data, dict) else None
        if not message:
            message = self._gateway_error_message(gateway_data)
        return success, message, data.get('game_id'), data.get('player_id')

    def join_game(self, name, game_id, position):
        ok, gateway_data = self._gateway_command(
            'join',
            {'name': name, 'game_id': game_id, 'position': position},
            game_id=game_id,
        )
        if not ok:
            return False, self._gateway_error_message(gateway_data), None
        data = gateway_data.get('response', {})
        success = data.get('success', False)
        message = data.get('message') if isinstance(data, dict) else None
        if not message:
            message = self._gateway_error_message(gateway_data)
        return success, message, data.get('player_id')

    def get_hand(self):
        if MQTT_EVENTS_ENABLED and self.player_id and self.game_id:
            return self.my_hand
        if not self.player_id:
            return []
        ok, gateway_data = self._gateway_query(f'hand/{self.player_id}', game_id=self.game_id)
        if not ok:
            return []
        data = gateway_data.get('response', {})
        if data.get('success'):
            return data.get('hand', [])
        return []

    def cut_deck(self, index):
        ok, gateway_data = self._gateway_command(
            'cut_deck',
            {'player_id': self.player_id, 'index': index, 'game_id': self.game_id},
            game_id=self.game_id,
        )
        if not ok:
            return False, self._gateway_error_message(gateway_data)
        data = gateway_data.get('response', {})
        return data.get('success', False), data.get('message', 'Unknown error')

    def select_trump(self, choice):
        ok, gateway_data = self._gateway_command(
            'select_trump',
            {'player_id': self.player_id, 'choice': choice, 'game_id': self.game_id},
            game_id=self.game_id,
        )
        if not ok:
            return False, self._gateway_error_message(gateway_data)
        data = gateway_data.get('response', {})
        return data.get('success', False), data.get('message', 'Unknown error')

    def play_card(self, card):
        ok, gateway_data = self._gateway_command(
            'play',
            {'player_id': self.player_id, 'card': card, 'game_id': self.game_id},
            game_id=self.game_id,
        )
        if not ok:
            return False, self._gateway_error_message(gateway_data)
        data = gateway_data.get('response', {})
        return data.get('success', False), data.get('message', 'Unknown error')

    def change_position(self, new_position):
        ok, gateway_data = self._gateway_command(
            'change_position',
            {'player_id': self.player_id, 'position': new_position, 'game_id': self.game_id},
            game_id=self.game_id,
        )
        if not ok:
            return False, self._gateway_error_message(gateway_data)
        data = gateway_data.get('response', {})
        if data.get('success'):
            self.position = new_position.upper()
        return data.get('success', False), data.get('message', 'Unknown error')

    def add_bot(self, bot_name, position, difficulty='random'):
        ok, gateway_data = self._gateway_command(
            'add_bot',
            {
                'player_id': self.player_id,
                'name': bot_name,
                'position': position,
                'difficulty': difficulty,
                'game_id': self.game_id,
            },
            game_id=self.game_id,
            timeout=10,
        )
        if not ok:
            return False, self._gateway_error_message(gateway_data), None
        data = gateway_data.get('response', {})
        return data.get('success', False), data.get('message', 'Unknown error'), data.get('player_id')

    def create_room(self):
        ok, gateway_data = self._gateway_command('create_room', {}, game_id=None)
        if not ok:
            return None, self._gateway_error_message(gateway_data)
        data = gateway_data.get('response', {})
        if data.get('success'):
            return data.get('game_id'), None
        return None, data.get('message', 'Unknown error')

    def get_match_points(self):
        ok, gateway_data = self._gateway_query(f'room/{self.game_id}/match_points', game_id=self.game_id)
        if not ok:
            return False, {'message': self._gateway_error_message(gateway_data)}
        data = gateway_data.get('response', {})
        return data.get('success', False), data

    def request_rematch(self):
        ok, gateway_data = self._gateway_command(f'room/{self.game_id}/rematch', {}, game_id=self.game_id)
        if not ok:
            return False, self._gateway_error_message(gateway_data)
        data = gateway_data.get('response', {})
        return data.get('success', False), data.get('message', 'Unknown error')

    def _prompt_position_choice(self, available_slots):
        if not available_slots:
            print('\n[INFO] No free slots right now. Press Enter to refresh.')
            input('Choose position: ')
            return POSITION_REFRESH

        print('\nAvailable positions:')
        for i, slot in enumerate(available_slots, 1):
            print(f"  [{i}] {slot['position']:6}  (Team {slot['team'][-1]} - {slot['team_label']})")
        print('  [Enter] Refresh list')

        while True:
            choice = input('Choose position: ').strip()
            if not choice or choice.lower() in {'r', 'refresh'}:
                return POSITION_REFRESH
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(available_slots):
                    return available_slots[idx]['position'].lower()
            print(f'[ERROR] Enter a number between 1 and {len(available_slots)}.')

    def _prompt_lobby_action(self):
        while True:
            print('\nChoose an action:')
            print('  [1] Create new game')
            print('  [2] Join existing game')
            choice = input('Action: ').strip()
            if choice in ('1', '2'):
                return choice
            print('[ERROR] Invalid action. Choose 1 or 2.')

    def _resolve_position_input(self, value, available_slots):
        if not value:
            return None

        raw = value.strip().lower()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(available_slots):
                return available_slots[idx]['position'].lower()
            return None

        return raw

    def _parse_bot_args(self, args, available_slots):
        if not args:
            return None, None, None, 'Missing bot arguments.'

        tokens = [token.strip() for token in args if token.strip()]
        if not tokens:
            return None, None, None, 'Missing bot arguments.'

        difficulty = 'random'
        if 'as' in [t.lower() for t in tokens]:
            lower_tokens = [t.lower() for t in tokens]
            as_idx = lower_tokens.index('as')
            if as_idx == len(tokens) - 1:
                available = ', '.join(sorted(SUPPORTED_BOT_TYPES))
                return None, None, None, f'Missing bot type after "as". Available: {available}'
            selected_type = normalize_bot_type(tokens[as_idx + 1])
            if not selected_type:
                available = ', '.join(sorted(SUPPORTED_BOT_TYPES))
                return None, None, None, f'Unknown bot type "{tokens[as_idx + 1]}". Available: {available}'
            difficulty = selected_type
            tokens = tokens[:as_idx] + tokens[as_idx + 2:]
        elif tokens:
            selected_type = normalize_bot_type(tokens[-1])
            if selected_type:
                difficulty = selected_type
                tokens = tokens[:-1]

        if not tokens:
            return None, None, None, 'Missing bot name or position.'

        candidate = tokens[0]
        resolved_position = self._resolve_position_input(candidate, available_slots)
        position_names = {'north', 'south', 'east', 'west'}

        if resolved_position and (candidate.isdigit() or candidate.strip().lower() in position_names):
            position = resolved_position
            bot_name = ' '.join(tokens[1:]).strip() if len(tokens) > 1 else f'Bot_{position}_{difficulty}'
        else:
            position = available_slots[0]['position'].lower()
            bot_name = ' '.join(tokens).strip()

        if not bot_name:
            bot_name = f'Bot_{position}_{difficulty}'

        return position, bot_name, difficulty, None

    def _handle_waiting_command(self, state, user_input):
        parts = user_input.split()
        if not parts:
            return False

        cmd = parts[0]
        if cmd in ('help', 'h'):
            with self.display_lock:
                print('\n[COMMANDS]')
                print('  position <slot_number|north|south|east|west>')
                print('  bot <bot_name>')
                print('  bot <slot_number|north|south|east|west> [bot_name]')
                print('  bot <...> as <random|weak|weak_agent|average|average_agent>')
                print('  quit')
                print('> ', end='', flush=True)
            return True

        if cmd in ('position', 'pos', 'change', 'changepos'):
            if len(parts) < 2:
                with self.display_lock:
                    print('\n[ERROR] Usage: position <slot_number|position_name>')
                    print('> ', end='', flush=True)
                return True

            available_slots = state.get('available_slots', [])
            resolved_position = self._resolve_position_input(parts[1], available_slots)
            if not resolved_position:
                with self.display_lock:
                    print('\n[ERROR] Invalid position choice.')
                    print('> ', end='', flush=True)
                return True

            success, message = self.change_position(resolved_position)
            with self.display_lock:
                if success:
                    print(f'\n[SUCCESS] {message}')
                    self.pause_updates = False
                else:
                    print(f'\n[ERROR] {message}')
                print('> ', end='', flush=True)
            return True

        if cmd in ('bot', 'addbot', 'boot', 'addboot'):
            if len(parts) < 2:
                with self.display_lock:
                    print('\n[ERROR] Usage: bot <bot_name> [as <type>] OR bot <slot_number|position_name> [bot_name] [as <type>]')
                    print('> ', end='', flush=True)
                return True

            available_slots = state.get('available_slots', [])
            if not available_slots:
                with self.display_lock:
                    print('\n[ERROR] No available slots for bot.')
                    print('> ', end='', flush=True)
                return True

            resolved_position, bot_name, difficulty, parse_error = self._parse_bot_args(parts[1:], available_slots)
            if parse_error:
                with self.display_lock:
                    print(f'\n[ERROR] {parse_error}')
                    print('> ', end='', flush=True)
                return True

            success, message, _ = self.add_bot(bot_name, resolved_position, difficulty)
            with self.display_lock:
                if success:
                    print(f'\n[SUCCESS] {message} (type: {difficulty})')
                    self.pause_updates = False
                else:
                    print(f'\n[ERROR] {message}')
                print('> ', end='', flush=True)
            return True

        return False

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        self.mqtt_connected = rc == 0
        if rc != 0:
            return
        if self.game_id:
            client.subscribe(f'sueca/games/{self.game_id}/state', qos=1)
            client.subscribe(f'sueca/games/{self.game_id}/events', qos=1)
            client.subscribe(f'sueca/games/{self.game_id}/players/+', qos=1)

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            if msg.topic.endswith('/state'):
                state = payload.get('state')
                if state is not None:
                    self.latest_state = state
                hands = payload.get('hands', {})
                if self.player_id and isinstance(hands, dict):
                    player_hand = hands.get(self.player_id)
                    if isinstance(player_hand, list):
                        self.my_hand = player_hand
                self.needs_refresh = True
                return

            event_type = payload.get('event_type', 'unknown_event')
            actor = payload.get('player_name') or payload.get('winner_name') or 'system'
            self.needs_refresh = True
            with self.display_lock:
                print(f'\n[MQTT] {event_type} from {actor}')
                print('> ', end='', flush=True)
        except Exception:
            pass

    def _start_mqtt_listener(self):
        if not MQTT_EVENTS_ENABLED or mqtt_client is None or self.mqtt_client is not None:
            return
        try:
            self.mqtt_client = mqtt_client.Client(client_id=f'cli-{int(time.time())}')
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message

            if MQTT_USE_AUTH and MQTT_USERNAME and MQTT_PASSWORD:
                self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

            self.mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            self.mqtt_client.loop_start()
            print(f'[INFO] MQTT events enabled ({MQTT_BROKER_HOST}:{MQTT_BROKER_PORT})')
        except Exception as error:
            self.mqtt_client = None
            print(f'[WARN] MQTT listener unavailable: {error}')

    def _stop_mqtt_listener(self):
        if self.mqtt_client is None:
            return
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except Exception:
            pass
        finally:
            self.mqtt_client = None
            self.mqtt_connected = False

    def display_game(self, force=False):
        if self.pause_updates and not force:
            return

        with self.display_lock:
            state = self.get_status(force=force)
            if not state:
                return

            self.clear_screen()

            print('=' * 70)
            print(f'  SUECA - Room: {self.game_id} - Player: {self.player_name}')
            print('=' * 70)
            print()

            print(f"Players: {state['player_count']}/4  |  ", end='')

            if state['phase'] == 'waiting':
                print('Game: WAITING FOR PLAYERS')
            elif state['phase'] == 'deck_cutting':
                print('Game: DECK CUTTING  |  ', end='')
                print(f"NORTH player ({state['north_player']}) must cut the deck!")
            elif state['phase'] == 'trump_selection':
                print('Game: TRUMP SELECTION  |  ', end='')
                print(f"WEST player ({state['west_player']}) must choose trump!")
            elif state['phase'] == 'playing':
                print(f"Round: {state['current_round']}/10  |  ", end='')
                if state['trump']:
                    try:
                        trump_num = int(state['trump'])
                        trump_display = CardMapper.get_card(trump_num)
                    except Exception:
                        trump_display = state['trump']
                    print(f'Trump: {trump_display}')
                else:
                    print()
            elif state['phase'] == 'finished':
                print('Game: FINISHED!')
            else:
                print(f"Game: {state['phase'].upper()}")

            print()

            if state['players']:
                print('PLAYERS:')
                for p in state['players']:
                    marker = '>>> ' if p.get('id') == self.player_id else '    '
                    print(f"{marker}{p['name']:15} ({p['position']:5}) - {p['cards_left']} cards")
                print()

            if state['teams']['team1']:
                print(f"Team 1 (N/S): {', '.join(state['teams']['team1'])}", end='')
                if state.get('team_scores'):
                    print(f" - {state['team_scores']['team1']} points")
                else:
                    print()

                print(f"Team 2 (E/W): {', '.join(state['teams']['team2'])}", end='')
                if state.get('team_scores'):
                    print(f" - {state['team_scores']['team2']} points")
                else:
                    print()
                print()

            round_resolving = state['phase'] == 'playing' and len(state.get('round_plays', [])) == 4

            if state['phase'] == 'playing' and state.get('current_player_name'):
                print(f">>> TURN: {state['current_player_name']}", end='')
                if state.get('current_player_id') == self.player_id:
                    print(' (YOU!)', end='')
                if state.get('round_suit'):
                    print(f"  |  Round suit: {state['round_suit']}", end='')
                print()
                print()

            if state['round_plays']:
                print('CARDS ON TABLE:')
                for play in state['round_plays']:
                    try:
                        card_num = int(play['card'])
                        card_display = CardMapper.get_card(card_num)
                    except Exception:
                        card_display = play['card']
                    position_str = f"({play.get('position', '?')})" if play.get('position') else ''
                    print(f"  {play.get('player_name', '?'):15} {position_str:7} -> {card_display}")
                print()

            if not (MQTT_EVENTS_ENABLED and self.mqtt_connected):
                self.my_hand = self.get_hand()
            if self.my_hand:
                print('YOUR HAND:')
                for i, card_str in enumerate(self.my_hand, 1):
                    try:
                        card_num = int(card_str)
                        card_display = CardMapper.get_card(card_num)
                    except Exception:
                        card_display = card_str
                    print(f'  [{i}] {card_display}')
                print()

            print('-' * 70)
            if state['phase'] == 'deck_cutting' and state.get('north_player_id') == self.player_id:
                cutter_pos = state.get('cutter_position', 'NORTH')
                print(f'YOU are the cutter ({cutter_pos})! Type a number (1-40) to cut the deck, or quit to exit')
            elif state['phase'] == 'waiting':
                print('Commands: position <slot|name> | bot <name> [as <type>] | bot <slot|name> [name] [as <type>] | help | quit')
                print(f'[INFO] Your player ID is: {self.player_id}')
            elif state['phase'] == 'deck_cutting':
                cutter_pos = state.get('cutter_position', 'NORTH')
                print(f"Waiting for {state['north_player']} ({cutter_pos}) to cut the deck...")
                print('Type quit to exit')
            elif state['phase'] == 'trump_selection' and state.get('west_player_id') == self.player_id:
                selector_pos = state.get('trump_selector_position', 'WEST')
                print(f'YOU are the trump selector ({selector_pos})! Type top or bottom to select trump card, or quit to exit')
            elif state['phase'] == 'trump_selection':
                selector_pos = state.get('trump_selector_position', 'WEST')
                print(f"Waiting for {state['west_player']} ({selector_pos}) to select trump...")
                print('Type quit to exit')
            elif state['phase'] == 'playing':
                if round_resolving:
                    print('Round resolving... waiting for winner update')
                    print('Type quit to exit')
                elif state.get('current_player_id') == self.player_id and self.my_hand:
                    print('YOUR TURN! Type card number to play (e.g. 1) or quit to exit')
                    if state.get('round_suit'):
                        print(f"Note: You must follow suit {state['round_suit']} if you have it!")
                elif self.my_hand:
                    print(f"Waiting for {state.get('current_player_name', '?')} to play...")
                    print('Type quit to exit')
                else:
                    print('Type quit to exit')
            elif state['phase'] == 'finished':
                team1_score = state.get('team_scores', {}).get('team1', 0)
                team2_score = state.get('team_scores', {}).get('team2', 0)
                if team1_score > team2_score:
                    print(f'TEAM 1 WINS! ({team1_score} vs {team2_score})')
                elif team2_score > team1_score:
                    print(f'TEAM 2 WINS! ({team2_score} vs {team1_score})')
                else:
                    print(f'TIE! ({team1_score} vs {team2_score})')

                match_points = state.get('match_points')
                if match_points:
                    print()
                    print('MATCH WINS (1 victory = 1 point):')
                    print(f"  Team 1 (N/S): {match_points.get('team1', 0)}")
                    print(f"  Team 2 (E/W): {match_points.get('team2', 0)}")

                print('Commands: rematch | score | quit')
            else:
                print('Type quit to exit')
            print('> ', end='', flush=True)

    def auto_update_thread(self):
        while self.running:
            if not self.pause_updates:
                if MQTT_EVENTS_ENABLED and self.mqtt_connected:
                    if self.needs_refresh:
                        self.display_game(force=False)
                        self.needs_refresh = False
                else:
                    self.display_game(force=True)
         

    def run(self):
        self.clear_screen()
        print('=' * 70)
        print('  SUECA')
        print('=' * 70)
        print()

        print('Connecting to server...')
        if not self.get_status(force=True):
            print('[ERROR] Cannot connect to server!')
            print(f'        Current gateway URL: {GATEWAY_URL}')
            print('        Start it with: PYTHONPATH=/home/goncalo/Desktop/1S_3M/PEI/Sueca/sueca_1.4 /home/goncalo/Desktop/1S_3M/PEI/venv/bin/python3 -m uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8080')
            return

        print('[OK] Connected\n')
        if MQTT_EVENTS_ENABLED:
            print('[INFO] MQTT mode enabled (strict mode: no runtime HTTP fallback).')
        else:
            print('[INFO] MQTT mode disabled; using HTTP polling.')

        self.player_name = input('Enter your name: ').strip()
        if not self.player_name:
            print('[ERROR] Name required!')
            return

        action = self._prompt_lobby_action()

        if action == '1':
            game_id, error = self.create_room()
            if error:
                print(f'[ERROR] {error}')
                return
            self.game_id = game_id
            self.set_room_mode(self.game_id, GAME_MODE)
            print(f'\n[ROOM CREATED] Game ID: {self.game_id}')
            print('Share this ID with the other players!')
        else:
            while True:
                room_id = input('\nEnter game ID: ').strip().upper()
                if not room_id:
                    print('[ERROR] Game ID required!')
                    continue
                self.game_id = room_id
                if self.get_status(force=True) is not None:
                    self.set_room_mode(self.game_id, GAME_MODE)
                    break
                print(f'[ERROR] Game {room_id} not found. Check the ID and try again.')
                self.game_id = None

        # Start MQTT before seat selection so lobby state can update in real time.
        if MQTT_EVENTS_ENABLED:
            self._start_mqtt_listener()

        while True:
            status = self.get_status(force=True)
            if not status:
                print('[ERROR] Failed to get game status.')
                return

            self.position = self._prompt_position_choice(status.get('available_slots', []))
            if self.position == POSITION_REFRESH:
                continue
            if not self.position:
                print('[ERROR] No available slots in this game.')
                return

            success, message, player_id = self.join_game(self.player_name, self.game_id, self.position)
            if success:
                self.player_id = player_id
                if MQTT_EVENTS_ENABLED:
                    self._start_mqtt_listener()

                    def _state_has_me():
                        return bool(
                            self.latest_state and any(
                                p.get('id') == self.player_id for p in self.latest_state.get('players', [])
                            )
                        )

                    # If state already arrived during the join request, keep it.
                    if not _state_has_me():
                        # Wait briefly for retained/live MQTT state that includes this player.
                        deadline = time.time() + 5
                        while time.time() < deadline:
                            if _state_has_me():
                                break
                    if not _state_has_me():
                        print('[ERROR] MQTT state not received. Strict MQTT mode does not fallback to HTTP.')
                        return
                break
            # Retry for seat conflicts and transient transport/parsing failures.
            message_text = message if isinstance(message, str) else str(message or 'Unknown error')
            message_l = message_text.lower()
            seat_conflict = (
                ('already taken' in message_l)
                or ('occupied' in message_l)
                or ('not available' in message_l)
                or ('in use' in message_l)
            )
            if ((seat_conflict and 'name' not in message_l)
                    or message_l.startswith('error:')):
                print(f'[ERROR] {message_text} — refreshing available positions...')
            else:
                print(f'[ERROR] {message_text}')
                return

        print(f'[OK] {message}')
        if action == '1':
            print(f'[ROOM] Share this game ID with other players: {self.game_id}')

        print('\nWhen 4 players join this room:')
        print('  1. NORTH player cuts the deck (choose index 1-40)')
        print('  2. WEST player selects trump (choose top or bottom)')
        print('  3. Cards are dealt and game starts!')
        print('\nYour hand will update automatically every 2 seconds.\n')

        update_thread = Thread(target=self.auto_update_thread, daemon=True)
        update_thread.start()

        try:
            while self.running:
                if MQTT_EVENTS_ENABLED:
                    state = self.latest_state
                else:
                    state = self.get_status(force=True)
                if state:
                    round_resolving = state.get('phase') == 'playing' and len(state.get('round_plays', [])) == 4
                    is_my_action = (
                        (state.get('phase') == 'deck_cutting' and state.get('north_player_id') == self.player_id)
                        or (state.get('phase') == 'trump_selection' and state.get('west_player_id') == self.player_id)
                        or (state.get('phase') == 'playing' and not round_resolving and state.get('current_player_id') == self.player_id)
                        or (state.get('phase') == 'finished')
                    )

                    if is_my_action:
                        self.pause_updates = True
                        self.display_game(force=True)

                user_input = input().strip().lower()

                if user_input == 'quit':
                    self.running = False
                    print('\nGoodbye!')
                    break

                if not state:
                    continue

                if state.get('phase') == 'waiting':
                    if self._handle_waiting_command(state, user_input):
                        continue

                if state.get('phase') == 'finished':
                    if user_input in ('rematch', 'r'):
                        success, message = self.request_rematch()
                        with self.display_lock:
                            if success:
                                print(f'\n[SUCCESS] {message}')
                                self.pause_updates = False
                            else:
                                print(f'\n[ERROR] {message}')
                            print('> ', end='', flush=True)
                    elif user_input in ('score', 's'):
                        success, data = self.get_match_points()
                        with self.display_lock:
                            if success:
                                points = data.get('points', {})
                                print('\n[MATCH SCOREBOARD]')
                                print(f"Team 1 (N/S): {points.get('team1', 0)}")
                                print(f"Team 2 (E/W): {points.get('team2', 0)}")
                                print(f"Matches played: {data.get('matches_played', 0)}")
                            else:
                                print(f"\n[ERROR] {data.get('message', 'Could not get score')}")
                            print('> ', end='', flush=True)
                    else:
                        with self.display_lock:
                            print('\n[ERROR] Use: rematch | score | quit')
                            print('> ', end='', flush=True)
                    continue

                if state.get('phase') == 'deck_cutting':
                    if state.get('north_player_id') == self.player_id:
                        if user_input.isdigit():
                            cut_index = int(user_input)
                            if 1 <= cut_index <= 40:
                                success, message = self.cut_deck(cut_index)
                                with self.display_lock:
                                    if success:
                                        print(f'\n[SUCCESS] {message}')
                                        self.pause_updates = False
                                    else:
                                        print(f'\n[ERROR] {message}')
                                    print('> ', end='', flush=True)
                            else:
                                with self.display_lock:
                                    print('\n[ERROR] Cut index must be between 1 and 40')
                                    print('> ', end='', flush=True)
                        else:
                            with self.display_lock:
                                print('\n[ERROR] Please type a number between 1 and 40')
                                print('> ', end='', flush=True)
                    continue

                if state.get('phase') == 'trump_selection':
                    if state.get('west_player_id') == self.player_id:
                        if user_input in ['top', 'bottom']:
                            success, message = self.select_trump(user_input)
                            with self.display_lock:
                                if success:
                                    print(f'\n[SUCCESS] {message}')
                                    self.pause_updates = False
                                else:
                                    print(f'\n[ERROR] {message}')
                                print('> ', end='', flush=True)
                        else:
                            with self.display_lock:
                                print('\n[ERROR] Please type top or bottom')
                                print('> ', end='', flush=True)
                    continue

                if user_input.isdigit():
                    current_state = self.get_status(force=True) or state

                    if current_state.get('phase') == 'playing' and len(current_state.get('round_plays', [])) == 4:
                        with self.display_lock:
                            print('\n[INFO] Round is being resolved, wait a moment...')
                            print('> ', end='', flush=True)
                        continue

                    idx = int(user_input) - 1
                    if 0 <= idx < len(self.my_hand):
                        card = self.my_hand[idx]
                        success, message = self.play_card(card)
                        if success:
                            self.pause_updates = False
                            self.needs_refresh = True
                        else:
                            with self.display_lock:
                                print(f'\n[ERROR] {message}')
                                print('> ', end='', flush=True)
                    else:
                        with self.display_lock:
                            print('\n[ERROR] Invalid card number!')
                            print('> ', end='', flush=True)

        except KeyboardInterrupt:
            print('\n\nGoodbye!')

        self._stop_mqtt_listener()
        self.running = False


if __name__ == '__main__':
    client = GameClient()
    client.run()

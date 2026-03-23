"""
Simple CLI client for Sueca game
Supports room creation/join by game ID and manual position selection.
"""

import requests
import os
import time
from threading import Thread, Lock
from ..card_mapper import CardMapper

SERVER_URL = os.getenv('SUECA_SERVER_URL', 'http://localhost:5001')

class GameClient:
    def __init__(self):
        self.player_name = None
        self.player_id = None
        self.token = None
        self.debug_tokens = os.getenv('SUECA_DEBUG_TOKENS', '').lower() in ('1', 'true', 'yes', 'on')
        self.game_id = None
        self.position = None
        self.running = True
        self.my_hand = []
        self.display_lock = Lock()
        self.pause_updates = False

    def clear_screen(self):
        os.system('clear' if os.name != 'nt' else 'cls')

    def get_status(self):
        try:
            params = {'game_id': self.game_id} if self.game_id else None
            response = requests.get(f'{SERVER_URL}/api/status', params=params, timeout=1)
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None

    def _auth_headers(self):
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def _debug_print_token(self, label):
        if not self.debug_tokens:
            return
        if self.token:
            print(f"[DEBUG] {label} token ({len(self.token)} chars): {self.token}")
        else:
            print(f"[DEBUG] {label} token: <missing>")

    def create_game(self, name, position):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/create_game',
                json={'name': name, 'position': position},
                timeout=2,
            )
            data = response.json()
            return data.get('success', False), data.get('message', 'Unknown error'), data.get('game_id'), data.get('player_id')
        except Exception as e:
            return False, f'Error: {e}', None, None

    def join_game(self, name, game_id, position):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/join',
                json={'name': name, 'game_id': game_id, 'position': position},
                timeout=2,
            )
            data = response.json()
            token = data.get('token')
            if token:
                self.token = token
                self._debug_print_token('join_game')
            return data.get('success', False), data.get('message', 'Unknown error'), data.get('player_id')
        except Exception as e:
            return False, f'Error: {e}', None

    def get_hand(self):
        try:
            if not self.token:
                return []
            params = {'game_id': self.game_id}
            response = requests.get(
                f'{SERVER_URL}/api/hand',
                params=params,
                headers=self._auth_headers(),
                timeout=1,
            )
            data = response.json()
            if data.get('success'):
                return data.get('hand', [])
            return []
        except Exception:
            return []

    def cut_deck(self, index):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/cut_deck',
                json={'index': index, 'game_id': self.game_id},
                headers=self._auth_headers(),
                timeout=2,
            )
            data = response.json()
            return data.get('success', False), data.get('message', 'Unknown error')
        except Exception as e:
            return False, f'Error: {e}'

    def select_trump(self, choice):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/select_trump',
                json={'choice': choice, 'game_id': self.game_id},
                headers=self._auth_headers(),
                timeout=2,
            )
            data = response.json()
            return data.get('success', False), data.get('message', 'Unknown error')
        except Exception as e:
            return False, f'Error: {e}'

    def play_card(self, card):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/play',
                json={'card': card, 'game_id': self.game_id},
                headers=self._auth_headers(),
                timeout=2,
            )
            data = response.json()
            return data.get('success', False), data.get('message', 'Unknown error')
        except Exception as e:
            return False, f'Error: {e}'

    def change_position(self, new_position):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/change_position',
                json={'position': new_position, 'game_id': self.game_id},
                headers=self._auth_headers(),
                timeout=2,
            )
            data = response.json()
            if data.get('success'):
                self.position = new_position.upper()
            return data.get('success', False), data.get('message', 'Unknown error')
        except Exception as e:
            return False, f'Error: {e}'

    def add_bot(self, bot_name, position, difficulty='random'):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/add_bot',
                json={
                    'name': bot_name,
                    'position': position,
                    'difficulty': difficulty,
                    'game_id': self.game_id
                },
                headers=self._auth_headers(),
                timeout=2,
            )
            data = response.json()
            return data.get('success', False), data.get('message', 'Unknown error'), data.get('player_id')
        except Exception as e:
            return False, f'Error: {e}', None

    def create_room(self):
        try:
            response = requests.post(f'{SERVER_URL}/api/create_room', timeout=2)
            data = response.json()
            if data.get('success'):
                return data.get('game_id'), None
            return None, data.get('message', 'Unknown error')
        except Exception as e:
            return None, f'Error: {e}'

    def get_match_points(self):
        try:
            response = requests.get(f'{SERVER_URL}/api/room/{self.game_id}/match_points', timeout=2)
            data = response.json()
            return data.get('success', False), data
        except Exception as e:
            return False, {'message': f'Error: {e}'}

    def request_rematch(self):
        try:
            response = requests.post(
                f'{SERVER_URL}/api/room/{self.game_id}/rematch',
                headers=self._auth_headers(),
                timeout=2,
            )
            data = response.json()
            return data.get('success', False), data.get('message', 'Unknown error')
        except Exception as e:
            return False, f'Error: {e}'

    def _prompt_position_choice(self, available_slots):
        if not available_slots:
            return None

        print('\nAvailable positions:')
        for i, slot in enumerate(available_slots, 1):
            print(f"  [{i}] {slot['position']:6}  (Team {slot['team'][-1]} - {slot['team_label']})")

        while True:
            choice = input('Choose position: ').strip()
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
                print('  token')
                print('  quit')
                print('> ', end='', flush=True)
            return True

        if cmd in ('token', 'showtoken'):
            with self.display_lock:
                if self.token:
                    print(f'\n[DEBUG] Current token ({len(self.token)} chars):')
                    print(self.token)
                else:
                    print('\n[DEBUG] No token stored yet.')
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
                    print('\n[ERROR] Usage: bot <bot_name> OR bot <slot_number|position_name> [bot_name]')
                    print('> ', end='', flush=True)
                return True

            available_slots = state.get('available_slots', [])
            if not available_slots:
                with self.display_lock:
                    print('\n[ERROR] No available slots for bot.')
                    print('> ', end='', flush=True)
                return True

            # Supports both:
            # - bot <name>
            # - bot <position> [name]
            candidate = parts[1]
            resolved_position = self._resolve_position_input(candidate, available_slots)
            position_names = {'north', 'south', 'east', 'west'}

            if resolved_position and (candidate.isdigit() or candidate.strip().lower() in position_names):
                # First arg is a position
                bot_name = ' '.join(parts[2:]).strip() if len(parts) > 2 else f'Bot_{resolved_position}'
            else:
                # First arg is bot name, choose first available slot
                resolved_position = available_slots[0]['position'].lower()
                bot_name = ' '.join(parts[1:]).strip()

            success, message, _ = self.add_bot(bot_name, resolved_position, 'random')
            with self.display_lock:
                if success:
                    print(f'\n[SUCCESS] {message}')
                    self.pause_updates = False
                else:
                    print(f'\n[ERROR] {message}')
                print('> ', end='', flush=True)
            return True

        return False

    def display_game(self, force=False):
        if self.pause_updates and not force:
            return

        with self.display_lock:
            state = self.get_status()
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
                print('Commands: position <slot|name> | bot <name> | bot <slot|name> [name] | help | quit')
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
            try:
                if not self.pause_updates:
                    self.display_game()
                time.sleep(2)
            except Exception:
                pass

    def run(self):
        self.clear_screen()
        print('=' * 70)
        print('  SUECA')
        print('=' * 70)
        print()

        print('Connecting to server...')
        if not self.get_status():
            print('[ERROR] Cannot connect to server!')
            print('        Make sure the server is running: python3 server.py')
            return

        print('[OK] Connected\n')

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
            print(f'\n[ROOM CREATED] Game ID: {self.game_id}')
            print('Share this ID with the other players!')
        else:
            while True:
                room_id = input('\nEnter game ID: ').strip().upper()
                if not room_id:
                    print('[ERROR] Game ID required!')
                    continue
                self.game_id = room_id
                if self.get_status() is not None:
                    break
                print(f'[ERROR] Game {room_id} not found. Check the ID and try again.')
                self.game_id = None

        while True:
            status = self.get_status()
            if not status:
                print('[ERROR] Failed to get game status.')
                return

            self.position = self._prompt_position_choice(status.get('available_slots', []))
            if not self.position:
                print('[ERROR] No available slots in this game.')
                return

            success, message, player_id = self.join_game(self.player_name, self.game_id, self.position)
            if success:
                self.player_id = player_id
                break
            # Retry for seat conflicts and transient transport/parsing failures.
            message_l = message.lower()
            if (('already taken' in message_l and 'name' not in message_l)
                    or message_l.startswith('error:')):
                print(f'[ERROR] {message} — refreshing available positions...')
            else:
                print(f'[ERROR] {message}')
                return

        print(f'[OK] {message}')
        if action == '1':
            print(f'[ROOM] Share this game ID with other players: {self.game_id}')

        print('\nWhen 4 players join this room:')
        print('  1. NORTH player cuts the deck (choose index 1-40)')
        print('  2. WEST player selects trump (choose top or bottom)')
        print('  3. Cards are dealt and game starts!')
        print('\nYour hand will update automatically every 2 seconds.\n')
        time.sleep(2)

        update_thread = Thread(target=self.auto_update_thread, daemon=True)
        update_thread.start()

        try:
            while self.running:
                state = self.get_status()
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
                        time.sleep(0.1)
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
                    if state.get('phase') == 'playing' and len(state.get('round_plays', [])) == 4:
                        with self.display_lock:
                            print('\n[INFO] Round is being resolved, wait a moment...')
                            print('> ', end='', flush=True)
                        continue

                    if state.get('current_player_id') != self.player_id:
                        with self.display_lock:
                            print(f"\n[ERROR] Not your turn! Wait for {state.get('current_player_name', '?')}")
                            print('> ', end='', flush=True)
                        continue

                    idx = int(user_input) - 1
                    if 0 <= idx < len(self.my_hand):
                        card = self.my_hand[idx]
                        success, message = self.play_card(card)
                        if success:
                            self.pause_updates = False
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

        self.running = False


if __name__ == '__main__':
    client = GameClient()
    client.run()

"""Random AI player for Sueca Flask server (HTTP endpoints)."""

import random
import time
import requests
import threading
from card_mapper import CardMapper

SERVER_URL = 'http://localhost:5000'


def create_random_bot(name, position, game_id=None):
    """
    Create a random bot and start it in a background thread.
    The bot will join and play the game through the API.
    """
    # Start agent in background to play through API
    agent = RandomFlaskAgent(player_name=name, game_id=game_id, position=position, server_url=SERVER_URL)
    agent_thread = threading.Thread(target=agent.run, daemon=True)
    agent_thread.start()
    
    return agent  # Return the agent so caller can track it if needed


class RandomFlaskAgent:
    """Random agent that joins a room and plays through the Flask API."""

    def __init__(self, player_name, game_id, position=None, server_url=SERVER_URL):
        self.player_name = player_name
        self.game_id = game_id.upper().strip() if game_id else None
        self.position = position.lower() if position else None
        self.server_url = server_url.rstrip('/')
        self.player_id = None
        self.running = True
        self._finished_announced = False

    def _get(self, path, params=None, timeout=2):
        response = requests.get(f'{self.server_url}{path}', params=params, timeout=timeout)
        return response.status_code, response.json()

    def _post(self, path, payload, timeout=2):
        response = requests.post(f'{self.server_url}{path}', json=payload, timeout=timeout)
        return response.status_code, response.json()

    def get_status(self):
        code, data = self._get('/api/status', params={'game_id': self.game_id}, timeout=1)
        return data if code == 200 else None

    def get_hand(self):
        if not self.player_id:
            return []
        code, data = self._get(
            f'/api/hand/{self.player_id}',
            params={'game_id': self.game_id},
            timeout=1,
        )
        if code == 200 and data.get('success'):
            return [int(card) for card in data.get('hand', [])]
        return []

    def join_room(self):
        code, lobby = self._get(f'/api/room/{self.game_id}/lobby', timeout=2)
        if code != 200 or not lobby.get('success'):
            msg = lobby.get('message', 'Room not found') if isinstance(lobby, dict) else 'Room not found'
            print(f'[ERROR] {msg}')
            return False

        available_slots = lobby.get('available_slots', [])
        if not available_slots:
            print('[ERROR] No available positions in this room.')
            return False

        # If a specific position was requested, try to use it
        selected_position = None
        if self.position:
            for slot in available_slots:
                if slot['position'].lower() == self.position:
                    selected_position = self.position
                    break
        
        # If position not available or not specified, pick a random one
        if not selected_position:
            selected_slot = random.choice(available_slots)
            selected_position = selected_slot['position'].lower()

        payload = {
            'name': self.player_name,
            'game_id': self.game_id,
            'position': selected_position,
        }
        code, data = self._post('/api/join', payload, timeout=2)

        if code != 200 or not data.get('success'):
            print(f"[ERROR] Could not join room: {data.get('message', 'Unknown error')}")
            return False

        self.player_id = data.get('player_id')
        self.position = selected_position.upper()
        print(f'[OK] Joined room {self.game_id} as {self.player_name} ({self.position})')
        return True

    def _choose_card(self, hand, round_suit):
        if not hand:
            return None

        if round_suit:
            suited_cards = [card for card in hand if CardMapper.get_card_suit(card) == round_suit]
            if suited_cards:
                return random.choice(suited_cards)

        return random.choice(hand)

    def _act_if_needed(self, state):
        phase = state.get('phase')

        if phase != 'finished':
            self._finished_announced = False

        if phase == 'deck_cutting' and state.get('north_player_id') == self.player_id:
            cut_index = random.randint(1, 40)
            payload = {'player_id': self.player_id, 'index': cut_index, 'game_id': self.game_id}
            _, data = self._post('/api/cut_deck', payload)
            print(f"[CUT] index={cut_index} -> {data.get('message', '')}")
            return

        if phase == 'trump_selection' and state.get('west_player_id') == self.player_id:
            choice = random.choice(['top', 'bottom'])
            payload = {'player_id': self.player_id, 'choice': choice, 'game_id': self.game_id}
            _, data = self._post('/api/select_trump', payload)
            print(f"[TRUMP] choice={choice} -> {data.get('message', '')}")
            return

        if phase == 'playing' and state.get('current_player_id') == self.player_id:
            hand = self.get_hand()
            chosen_card = self._choose_card(hand, state.get('round_suit'))
            if chosen_card is None:
                return

            payload = {'player_id': self.player_id, 'card': str(chosen_card), 'game_id': self.game_id}
            _, data = self._post('/api/play', payload)

            card_name = CardMapper.get_card(chosen_card)
            print(f"[PLAY] {card_name} -> {data.get('message', '')}")
            time.sleep(1)
            

        if phase == 'finished':
            if not self._finished_announced:
                team_scores = state.get('team_scores', {})
                print(
                    '[GAME OVER] '
                    f"Team1={team_scores.get('team1', 0)} "
                    f"Team2={team_scores.get('team2', 0)}"
                )
                self._finished_announced = True
            return

    def run(self):
        print('[INFO] Random Flask AI started.')

        # Join room first; without this the bot never gets a player_id and cannot act.
        if not self.game_id:
            print('[ERROR] Missing game_id for bot.')
            self.running = False
            return

        if not self.join_room():
            self.running = False
            return

        while self.running:
            try:
                state = self.get_status()
                if not state:
                    print('[WARN] Could not fetch room status, retrying...')
                    time.sleep(2)
                    continue

                self._act_if_needed(state)
                time.sleep(1)
            except requests.RequestException as exc:
                print(f'[WARN] Network error: {exc}')
                time.sleep(2)
            except KeyboardInterrupt:
                self.running = False
                print('\n[INFO] Stopped by user.')


def main():
    print('=' * 60)
    print('SUECA RANDOM AI (Flask)')
    print('=' * 60)

    server_url = input(f'Server URL [{SERVER_URL}]: ').strip() or SERVER_URL
    player_name = input('Player name: ').strip()
    game_id = input('Room code (game_id): ').strip().upper()

    if not player_name:
        print('[ERROR] Player name is required.')
        return
    if not game_id:
        print('[ERROR] Room code is required.')
        return

    agent = RandomFlaskAgent(player_name=player_name, game_id=game_id, server_url=server_url)

    try:
        status = agent.get_status()
    except requests.RequestException as exc:
        print(f'[ERROR] Could not connect to server: {exc}')
        return

    if not status:
        print(f'[ERROR] Room {game_id} not found or server unavailable.')
        return

    if not agent.join_room():
        return

    agent.run()


if __name__ == '__main__':
    main()

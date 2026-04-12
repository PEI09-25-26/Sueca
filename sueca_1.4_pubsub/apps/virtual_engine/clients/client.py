"""Lightweight virtual-engine client used by AI agents."""

import os
import json
import requests

try:
    from paho.mqtt import client as mqtt_client
except Exception:
    mqtt_client = None


# Bot agents run inside virtual-engine and must call its /api/* routes directly.
# Default to virtual-engine local port (5000), not gateway (8080).
SERVER_URL = os.getenv('SUECA_VIRTUAL_ENGINE_URL', 'http://127.0.0.1:5000').rstrip('/')
UNKNOWN_ERROR = 'Unknown error'
MQTT_EVENTS_ENABLED = os.getenv('SUECA_MQTT_EVENTS', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', '127.0.0.1')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_USE_AUTH = os.getenv('MQTT_USE_AUTH', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}


class GameClient:
    def __init__(self):
        self.player_name = None
        self.player_id = None
        self.game_id = None
        self.position = None
        self.token = None
        self.latest_state = None
        self.my_hand = []
        self.mqtt_client = None
        self.mqtt_connected = False

    def _get(self, path, params=None, timeout=2):
        response = requests.get(f'{SERVER_URL}{path}', params=params, timeout=timeout)
        return response.json() if response.content else {}

    def _post(self, path, payload=None, timeout=2, headers=None):
        request_headers = dict(headers or {})
        if self.token and 'Authorization' not in request_headers:
            request_headers['Authorization'] = f'Bearer {self.token}'
        response = requests.post(f'{SERVER_URL}{path}', json=payload or {}, headers=request_headers, timeout=timeout)
        return response.json() if response.content else {}

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        self.mqtt_connected = rc == 0
        if rc != 0:
            return
        if self.game_id:
            client.subscribe(f'sueca/games/{self.game_id}/state', qos=1)

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            state = payload.get('state')
            if state is not None:
                self.latest_state = state
            if self.player_id and isinstance(payload.get('hands'), dict):
                hand = payload['hands'].get(self.player_id)
                if isinstance(hand, list):
                    self.my_hand = hand
        except Exception:
            pass

    def _start_mqtt_listener(self):
        if not MQTT_EVENTS_ENABLED or mqtt_client is None or self.mqtt_client is not None:
            return
        try:
            self.mqtt_client = mqtt_client.Client(client_id=f've-bot-{os.getpid()}-{id(self)}')
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            if MQTT_USE_AUTH and MQTT_USERNAME and MQTT_PASSWORD:
                self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            self.mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            self.mqtt_client.loop_start()
        except Exception:
            self.mqtt_client = None
            self.mqtt_connected = False

    def _stop_mqtt_listener(self):
        if not self.mqtt_client:
            return
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except Exception:
            pass
        finally:
            self.mqtt_client = None
            self.mqtt_connected = False

    def get_status(self):
        if MQTT_EVENTS_ENABLED:
            return self.latest_state
        params = {'game_id': self.game_id} if self.game_id else None
        data = self._get('/api/status', params=params)
        if data.get('success') is False and data.get('error'):
            return None
        self.latest_state = data
        return data

    def join_game(self, name, game_id, position):
        self.game_id = game_id
        data = self._post('/api/join', {'name': name, 'game_id': game_id, 'position': position})
        self.token = data.get('token')
        if data.get('success'):
            self.player_id = data.get('player_id')
            self._start_mqtt_listener()
        return data.get('success', False), data.get('message', UNKNOWN_ERROR), data.get('player_id')

    def get_hand(self):
        if MQTT_EVENTS_ENABLED:
            return self.my_hand
        if not self.player_id:
            return []
        data = self._get(f'/api/hand/{self.player_id}', params={'game_id': self.game_id})
        if data.get('success'):
            self.my_hand = data.get('hand', [])
            return data.get('hand', [])
        return []

    def cut_deck(self, index):
        data = self._post('/api/cut_deck', {'player_id': self.player_id, 'index': index, 'game_id': self.game_id})
        return data.get('success', False), data.get('message', UNKNOWN_ERROR)

    def select_trump(self, choice):
        data = self._post('/api/select_trump', {'player_id': self.player_id, 'choice': choice, 'game_id': self.game_id})
        return data.get('success', False), data.get('message', UNKNOWN_ERROR)

    def play_card(self, card):
        data = self._post('/api/play', {'player_id': self.player_id, 'card': card, 'game_id': self.game_id})
        return data.get('success', False), data.get('message', UNKNOWN_ERROR)

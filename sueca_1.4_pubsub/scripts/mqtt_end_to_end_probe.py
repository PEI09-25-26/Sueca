#!/usr/bin/env python3
"""End-to-end probe for gateway + virtual engine + MQTT state flow.

This script validates that core actions work and that MQTT state updates are delivered.
"""

import argparse
import json
import sys
import time
from urllib.parse import urlparse

import requests

try:
    from paho.mqtt import client as mqtt_client
except Exception as exc:  # pragma: no cover
    print(f"[FAIL] paho-mqtt not available: {exc}")
    sys.exit(2)


class ProbeError(RuntimeError):
    pass


def gateway_command(base_url, command, payload, game_id=None):
    body = {
        "game_id": game_id,
        "mode": "virtual",
        "payload": payload,
    }
    response = requests.post(f"{base_url}/game/command/{command}", json=body, timeout=5)
    data = response.json() if response.content else {}
    if not data.get("success"):
        raise ProbeError(f"command={command} failed: {json.dumps(data)}")
    return data.get("response", {})


def gateway_query(base_url, path, game_id=None):
    params = {"mode": "virtual"}
    if game_id:
        params["game_id"] = game_id
    response = requests.get(f"{base_url}/game/query/{path}", params=params, timeout=5)
    data = response.json() if response.content else {}
    if not data.get("success"):
        raise ProbeError(f"query={path} failed: {json.dumps(data)}")
    return data.get("response", {})


def wait_for(predicate, timeout_s, step=0.1):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(step)
    return None


def main():
    parser = argparse.ArgumentParser(description="Probe Sueca MQTT game flow")
    parser.add_argument("--gateway", default="http://localhost:8080")
    parser.add_argument("--mqtt-host", default=None)
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()

    gateway = args.gateway.rstrip("/")
    mqtt_host = args.mqtt_host or (urlparse(gateway).hostname or "127.0.0.1")

    print(f"[INFO] Gateway: {gateway}")
    print(f"[INFO] MQTT: {mqtt_host}:{args.mqtt_port}")

    status = gateway_query(gateway, "status")
    print(f"[OK] Gateway query/status phase={status.get('phase')}")

    room = gateway_command(gateway, "create_room", {}, game_id=None)
    game_id = room.get("game_id")
    if not game_id:
        raise ProbeError(f"create_room did not return game_id: {room}")
    print(f"[OK] Room created: {game_id}")

    messages = []

    def on_connect(client, userdata, flags, rc):
        if rc != 0:
            print(f"[FAIL] MQTT connect rc={rc}")
            return
        topic = f"sueca/games/{game_id}/state"
        client.subscribe(topic, qos=1)
        print(f"[OK] Subscribed: {topic}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            messages.append(payload)
        except Exception:
            pass

    mqtt = mqtt_client.Client(client_id=f"probe-{int(time.time())}")
    mqtt.on_connect = on_connect
    mqtt.on_message = on_message
    mqtt.connect(mqtt_host, args.mqtt_port, keepalive=30)
    mqtt.loop_start()

    players = [
        ("PNorth", "north"),
        ("PSouth", "south"),
        ("PEast", "east"),
        ("PWest", "west"),
    ]
    ids = {}

    for name, position in players:
        joined = gateway_command(
            gateway,
            "join",
            {"name": name, "game_id": game_id, "position": position},
            game_id=game_id,
        )
        pid = joined.get("player_id")
        if not pid:
            raise ProbeError(f"join returned no player_id for {name}: {joined}")
        ids[name] = pid
        print(f"[OK] Joined {name} at {position}: {pid}")

    state_msg = wait_for(lambda: messages[-1] if messages else None, timeout_s=5)
    if not state_msg:
        raise ProbeError("No MQTT state message received after joins")
    print(f"[OK] MQTT state messages received: {len(messages)}")

    cut = gateway_command(
        gateway,
        "cut_deck",
        {"game_id": game_id, "player_id": ids["PNorth"], "index": 10},
        game_id=game_id,
    )
    if not cut.get("success"):
        raise ProbeError(f"cut_deck rejected: {cut}")
    print("[OK] Deck cut")

    trump = gateway_command(
        gateway,
        "select_trump",
        {"game_id": game_id, "player_id": ids["PWest"], "choice": "top"},
        game_id=game_id,
    )
    if not trump.get("success"):
        raise ProbeError(f"select_trump rejected: {trump}")
    print("[OK] Trump selected")

    state = gateway_query(gateway, "status", game_id=game_id)
    current_player_id = state.get("current_player_id")
    if not current_player_id:
        raise ProbeError(f"No current_player_id after trump selection: {state}")

    hand_payload = gateway_query(gateway, f"hand/{current_player_id}", game_id=game_id)
    hand = hand_payload.get("hand", []) if isinstance(hand_payload, dict) else []
    if not hand:
        raise ProbeError(f"Current player has empty hand: {hand_payload}")

    played = False
    for card in hand:
        play = gateway_command(
            gateway,
            "play",
            {"game_id": game_id, "player_id": current_player_id, "card": card},
            game_id=game_id,
        )
        if play.get("success"):
            played = True
            print(f"[OK] Played card {card}")
            break
    if not played:
        raise ProbeError("Could not play any card from current player hand")

    updated = wait_for(
        lambda: messages[-1] if messages and messages[-1].get("state", {}).get("round_plays") else None,
        timeout_s=5,
    )
    if not updated:
        latest = messages[-1] if messages else {}
        latest_event = latest.get("event_type") if isinstance(latest, dict) else None
        latest_round_plays = len((latest.get("state") or {}).get("round_plays", [])) if isinstance(latest, dict) else 0
        http_state = gateway_query(gateway, "status", game_id=game_id)
        http_round_plays = len(http_state.get("round_plays", [])) if isinstance(http_state, dict) else 0
        raise ProbeError(
            "No MQTT round_plays update received after play "
            f"(mqtt_latest_event={latest_event}, mqtt_latest_round_plays={latest_round_plays}, "
            f"http_round_plays={http_round_plays})"
        )

    round_plays = updated.get("state", {}).get("round_plays", [])
    print(f"[PASS] MQTT end-to-end probe succeeded for game {game_id}; round_plays={len(round_plays)}")

    mqtt.loop_stop()
    mqtt.disconnect()


if __name__ == "__main__":
    try:
        main()
    except ProbeError as error:
        print(f"[FAIL] {error}")
        sys.exit(1)
    except Exception as error:
        print(f"[FAIL] Unexpected error: {error}")
        sys.exit(2)

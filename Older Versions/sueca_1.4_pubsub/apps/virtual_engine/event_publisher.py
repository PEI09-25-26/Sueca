"""
MQTT event publisher for game events.
Publishes real-time game state changes to the message broker.
"""

import logging
from datetime import datetime, timezone

from apps.emqx import mqtt_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def publish_player_event(game_id: str, event_type: str, player_id: str, player_name: str, **data):
    """Publish player-related events."""
    if not mqtt_client.is_connected():
        logger.warning(f"[MQTT] Not connected, skipping event: {event_type}")
        return
    
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "game_id": game_id,
        "player_id": player_id,
        "player_name": player_name,
        **data
    }
    topic = f"sueca/games/{game_id}/players/{player_id}"
    mqtt_client.publish_json(topic, payload)
    logger.info(f"[MQTT] Published {event_type} for {player_name} in game {game_id}")


def publish_game_event(game_id: str, event_type: str, **data):
    """Publish game-wide events."""
    if not mqtt_client.is_connected():
        logger.warning(f"[MQTT] Not connected, skipping event: {event_type}")
        return
    
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "game_id": game_id,
        **data
    }
    topic = f"sueca/games/{game_id}/events"
    mqtt_client.publish_json(topic, payload)
    logger.info(f"[MQTT] Published {event_type} for game {game_id}")


def publish_room_event(event_type: str, **data):
    """Publish room/lobby events visible to all players."""
    if not mqtt_client.is_connected():
        logger.warning(f"[MQTT] Not connected, skipping event: {event_type}")
        return
    
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        **data
    }
    topic = "sueca/rooms/events"
    mqtt_client.publish_json(topic, payload)
    logger.info(f"[MQTT] Published room event: {event_type}")


# Game phase events
def publish_game_started(game_id: str, dealer_position: str, player_count: int):
    publish_game_event(game_id, "game_started", dealer_position=dealer_position, player_count=player_count)


def publish_deck_cut(game_id: str, player_name: str, cut_index: int, trump_card: str):
    publish_game_event(game_id, "deck_cut", player_name=player_name, cut_index=cut_index, trump_card=trump_card)


def publish_trump_selected(game_id: str, player_name: str, choice: str, trump_card: str):
    publish_game_event(game_id, "trump_selected", player_name=player_name, choice=choice, trump_card=trump_card)


def publish_card_played(game_id: str, player_id: str, player_name: str, card: str, round_num: int):
    publish_player_event(game_id, "card_played", player_id, player_name, card=card, round=round_num)


def publish_round_finished(game_id: str, winner_name: str, winner_team: int, round_num: int, team1_score: int, team2_score: int):
    publish_game_event(
        game_id, 
        "round_finished", 
        winner_name=winner_name, 
        winner_team=winner_team, 
        round=round_num,
        team1_score=team1_score,
        team2_score=team2_score
    )


def publish_game_finished(game_id: str, winning_team: int, team1_score: int, team2_score: int):
    publish_game_event(
        game_id, 
        "game_finished", 
        winning_team=winning_team, 
        team1_score=team1_score, 
        team2_score=team2_score
    )


def publish_player_joined(game_id: str, player_id: str, player_name: str, position: str):
    publish_player_event(game_id, "player_joined", player_id, player_name, position=position)


def publish_player_removed(game_id: str, player_id: str, player_name: str):
    publish_player_event(game_id, "player_removed", player_id, player_name)


def publish_position_changed(game_id: str, player_id: str, player_name: str, old_position: str, new_position: str):
    publish_player_event(game_id, "position_changed", player_id, player_name, old_position=old_position, new_position=new_position)


def publish_bot_added(game_id: str, bot_id: str, bot_name: str, bot_type: str, position: str):
    publish_player_event(game_id, "bot_joined", bot_id, bot_name, bot_type=bot_type, position=position)

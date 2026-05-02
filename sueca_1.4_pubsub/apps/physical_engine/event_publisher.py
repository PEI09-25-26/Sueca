"""MQTT event publisher for physical engine events."""

from datetime import datetime, timezone
import logging

from apps.emqx import mqtt_client


logger = logging.getLogger(__name__)


def publish_physical_event(game_id: str, event_type: str, **data):
    if not mqtt_client.is_connected():
        return

    payload = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event_type': event_type,
        'game_id': game_id,
        **data,
    }

    topic = f'sueca/physical/{game_id}/events'
    mqtt_client.publish_json(topic, payload)
    logger.info('[MQTT] Published physical event %s for game %s', event_type, game_id)

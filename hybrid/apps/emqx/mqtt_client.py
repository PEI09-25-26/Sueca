import json
import os
import random
import time
from paho.mqtt import client as mqtt_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Self-hosted EMQX broker configuration
# This client is used by the gateway to PUBLISH game events to the broker
# 
# IMPORTANT: This is the BROKER ADDRESS (where EMQX listens), not the bind address.
# 
# Deployment scenarios:
#   - Docker (same network): MQTT_BROKER_HOST=emqx-enterprise (container name from lifecycle.py)
#   - Local dev: MQTT_BROKER_HOST=127.0.0.1
#   - External access: External clients connect to your server's PUBLIC IP on port 1883
#
# Examples:
#   Local dev:  MQTT_BROKER_HOST=127.0.0.1
#   Docker:     MQTT_BROKER_HOST=emqx-enterprise
#   Production: export MQTT_BROKER_HOST=$(hostname -I | awk '{print $1}')  # Get server's internal IP
BROKER = os.getenv('MQTT_BROKER_HOST', '127.0.0.1')
PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
USERNAME = os.getenv('MQTT_USERNAME', '')  # Empty for no auth
PASSWORD = os.getenv('MQTT_PASSWORD', '')
USE_AUTH = os.getenv('MQTT_USE_AUTH', 'false').lower() == 'true'
CLIENT_ID = f"sueca-server-{random.randint(0, 9999)}"

client = mqtt_client.Client(client_id=CLIENT_ID)
_connected = False
_loop_started = False


def is_connected() -> bool:
    return _connected


def on_connect(c, userdata, flags, rc):
    global _connected
    if rc == 0:
        _connected = True
        logger.info(f"[MQTT] Connected to {BROKER}:{PORT}")
    else:
        _connected = False
        logger.error(f"[MQTT] Failed to connect: code {rc}")


def on_disconnect(c, userdata, rc):
    global _connected
    _connected = False
    if rc != 0:
        logger.warning(f"[MQTT] Unexpected disconnection. Code: {rc}")


def on_publish(c, userdata, mid):
    logger.debug(f"[MQTT] Message {mid} published")


def connect_mqtt(wait_seconds: float = 3.0):
    """Connect to self-hosted EMQX broker and wait briefly for handshake."""
    global _loop_started
    if _connected:
        return True

    try:
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_publish = on_publish
        
        if USE_AUTH and USERNAME and PASSWORD:
            client.username_pw_set(USERNAME, PASSWORD)
            logger.info("[MQTT] Using authentication")
        
        logger.info(f"[MQTT] Connecting to {BROKER}:{PORT}...")
        client.connect(BROKER, PORT, keepalive=60)
        if not _loop_started:
            client.loop_start()
            _loop_started = True

        deadline = time.time() + max(wait_seconds, 0)
        while not _connected and time.time() < deadline:
            time.sleep(0.05)
        return _connected
    except Exception as e:
        logger.error(f"[MQTT] Connection failed: {e}")
        return False


def publish_json(topic: str, payload: dict, retain: bool = False):
    """Publish JSON payload to topic."""
    if not _connected and not connect_mqtt(wait_seconds=1.5):
        logger.warning(f"[MQTT] Not connected. Cannot publish to {topic}")
        return False
    
    try:
        data = json.dumps(payload)
        result = client.publish(topic, data, qos=1, retain=retain)
        if result[0] == 0:
            logger.debug(f"[MQTT] Published to {topic}")
            return True
        else:
            logger.error(f"[MQTT] Failed to publish to {topic}: {result[0]}")
            return False
    except Exception as e:
        logger.error(f"[MQTT] Publish error: {e}")
        return False


def disconnect_mqtt():
    """Gracefully disconnect from MQTT broker."""
    global _connected, _loop_started
    try:
        if _loop_started:
            client.loop_stop()
        client.disconnect()
        _connected = False
        _loop_started = False
        logger.info("[MQTT] Disconnected")
    except Exception as e:
        logger.error(f"[MQTT] Disconnect error: {e}")

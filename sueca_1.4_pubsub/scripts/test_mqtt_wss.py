#!/usr/bin/env python3
import time
import sys
import ssl
from paho.mqtt import client as mqtt_client

# Configuration from your logs/code
BROKER = "mqtt.suecadaojogo.com"
PORT = 443
PATH = "/mqtt"
CLIENT_ID = f"python-tester-{int(time.time())}"

def on_connect(client, userdata, flags, rc, properties=None):
    # Support for both v1 and v2 callbacks
    code = rc if isinstance(rc, int) else rc.value
    if code == 0:
        print("[SUCCESS] Connected to MQTT via WSS!")
        client.subscribe("sueca/test")
        print("[INFO] Subscribed to sueca/test")
    else:
        print(f"[FAILED] Connection failed with code {code}")

def on_message(client, userdata, msg):
    print(f"[RECEIVED] Topic: {msg.topic} Payload: {msg.payload.decode()}")

def run_test():
    print(f"[START] Testing WSS connection to {BROKER}:{PORT}{PATH}")

    client = None

    # Attempt 1: Paho v2 style
    try:
        from paho.mqtt.enums import CallbackAPIVersion
        print("[DEBUG] Using Paho v2 API")
        client = mqtt_client.Client(CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, transport="websockets")
    except Exception as e:
        print(f"[DEBUG] Paho v2 init failed: {e}")
        pass

    # Attempt 2: Paho v1 style with "websockets" (plural)
    if client is None:
        try:
            print("[DEBUG] Trying Paho v1 with 'websockets'")
            client = mqtt_client.Client(client_id=CLIENT_ID, transport="websockets")
        except Exception as e:
            print(f"[DEBUG] Paho v1 'websockets' failed: {e}")
            pass

    # Attempt 3: Paho v1 style with "websocket" (singular)
    if client is None:
        try:
            print("[DEBUG] Trying Paho v1 with 'websocket'")
            client = mqtt_client.Client(client_id=CLIENT_ID, transport="websocket")
        except Exception as e:
            print(f"[ERROR] All client initialization attempts failed: {e}")
            return

    client.ws_set_options(path=PATH)
    context = ssl.create_default_context()
    client.tls_set_context(context)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"[INFO] Attempting connection...")
        client.connect(BROKER, PORT, keepalive=60)
    except Exception as e:
        print(f"[ERROR] Could not initiate connection: {e}")
        return

    client.loop_start()

    # Wait to see if it connects
    timeout = 10
    start = time.time()
    connected = False
    while time.time() - start < timeout:
        if client.is_connected():
            print("[INFO] Connection established and verified.")
            client.publish("sueca/test", "Hello from Python tester")
            connected = True
            time.sleep(2)
            break
        time.sleep(0.5)

    if not connected:
        print("[TIMEOUT] Failed to establish connection within 10 seconds.")

    client.loop_stop()
    client.disconnect()
    print("[END] Test finished.")

if __name__ == "__main__":
    run_test()

import requests
from typing import Optional

class FrontendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def send_state(self, latest_state) -> Optional[dict]:
        """
        Sends a the current state of the game to the frontend.
        """
        try:
            response = requests.post(
                f"{self.base_url}/game/state",
                json=latest_state,
                timeout=3
            )                
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[Middleware] Frontend communication error: {e}")
            return None

    def send_event(self, event_payload) -> Optional[dict]:
        """Sends normalized events to the frontend event endpoint."""
        try:
            response = requests.post(
                f"{self.base_url}/game/event",
                json=event_payload,
                timeout=3,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[Middleware] Frontend event communication error: {e}")
            return None
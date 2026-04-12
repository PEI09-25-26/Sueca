import requests
from typing import Optional

try:
    from ..schemas import CardDetection
except ImportError:
    from schemas import CardDetection

class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=64)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def send_card(self, detection: CardDetection) -> Optional[dict]:
        """
        Sends a detected card to the backend.
        Returns backend response as dict, or None on failure.
        """
        try:
            response = self.session.post(
                f"{self.base_url}/card",
                json={
                    "rank": detection.rank,
                    "suit": detection.suit,
                },
                timeout=3
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[Middleware] Backend communication error: {e}")
            return None

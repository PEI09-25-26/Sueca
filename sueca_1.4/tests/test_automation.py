import importlib
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    TESTCLIENT_AVAILABLE = True
except Exception:
    TestClient = None
    TESTCLIENT_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[1]
PHYSICAL_DIR = ROOT / "apps" / "physical_engine"


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PHYSICAL_DIR) not in sys.path:
    sys.path.insert(0, str(PHYSICAL_DIR))


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 400
        self.content = b"{}"

    def json(self):
        return self._payload


def _load_module_from_path(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(TESTCLIENT_AVAILABLE, "fastapi is not installed in this Python environment")
class GatewayAutomationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SUECA_AUTOSTART_SERVICES"] = "0"
        from apps.gateway import main as gateway_main

        cls.gateway_main = importlib.reload(gateway_main)
        cls.client = TestClient(cls.gateway_main.app)

    def test_room_mode_set_and_get(self):
        set_resp = self.client.post("/game/room_mode/test-room", json={"mode": "physical"})
        self.assertEqual(set_resp.status_code, 200)
        self.assertTrue(set_resp.json().get("success"))

        get_resp = self.client.get("/game/room_mode/test-room")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertEqual(data.get("mode"), "physical")

    def test_command_proxy_virtual(self):
        with patch.object(self.gateway_main.requests, "post", return_value=_FakeResponse({"success": True, "from": "virtual"})) as mock_post:
            response = self.client.post(
                "/game/command/create_game",
                json={"game_id": "g1", "mode": "virtual", "payload": {"name": "Ana", "position": "NORTH"}},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("mode"), "virtual")
        self.assertIn("/api/create_game", body.get("target", ""))
        self.assertEqual(mock_post.call_count, 1)

    def test_query_proxy_virtual(self):
        with patch.object(self.gateway_main.requests, "get", return_value=_FakeResponse({"success": True, "state": {}})) as mock_get:
            response = self.client.get("/game/query/status?game_id=g1&mode=virtual")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("mode"), "virtual")
        self.assertIn("/api/status", body.get("target", ""))
        self.assertEqual(mock_get.call_count, 1)

    def test_services_endpoint(self):
        response = self.client.get("/system/services")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("services", data)


@unittest.skipUnless(TESTCLIENT_AVAILABLE, "fastapi is not installed in this Python environment")
class VirtualEngineAutomationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from apps.virtual_engine import api as virtual_api

        cls.virtual_api = importlib.reload(virtual_api)
        cls.client = TestClient(cls.virtual_api.app)

    def test_create_game_and_status(self):
        create = self.client.post("/api/create_game", json={"name": "Alice", "position": "NORTH"})
        self.assertEqual(create.status_code, 200)
        create_data = create.json()
        self.assertTrue(create_data.get("success"))
        game_id = create_data.get("game_id")
        self.assertTrue(game_id)

        status = self.client.get(f"/api/status?game_id={game_id}")
        self.assertEqual(status.status_code, 200)
        status_data = status.json()
        self.assertEqual(status_data.get("game_id"), game_id)

    def test_room_endpoints(self):
        room = self.client.post("/api/create_room")
        self.assertEqual(room.status_code, 200)
        game_id = room.json().get("game_id")

        lobby = self.client.get(f"/api/room/{game_id}/lobby")
        self.assertEqual(lobby.status_code, 200)
        self.assertTrue(lobby.json().get("success"))

        history = self.client.get(f"/api/room/{game_id}/history")
        self.assertEqual(history.status_code, 200)
        self.assertTrue(history.json().get("success"))


@unittest.skipUnless(TESTCLIENT_AVAILABLE, "fastapi is not installed in this Python environment")
class PhysicalServicesAutomationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.game_service = _load_module_from_path("physical_game_service", PHYSICAL_DIR / "game_service.py")
            cls.cv_service = _load_module_from_path("physical_cv_service", PHYSICAL_DIR / "cv_service.py")
        except Exception as error:
            raise unittest.SkipTest(f"physical service imports unavailable: {error}")
        cls.game_client = TestClient(cls.game_service.app)
        cls.cv_client = TestClient(cls.cv_service.app)

    def test_physical_game_basic_endpoints(self):
        state = self.game_client.get("/state")
        self.assertEqual(state.status_code, 200)

        reset = self.game_client.post("/reset")
        self.assertEqual(reset.status_code, 200)
        self.assertTrue(reset.json().get("success"))

        invalid_card = self.game_client.post("/card", json={"rank": "INVALID", "suit": "X"})
        self.assertEqual(invalid_card.status_code, 200)
        self.assertFalse(invalid_card.json().get("success"))

    def test_physical_cv_health(self):
        health = self.cv_client.get("/health")
        self.assertEqual(health.status_code, 200)
        data = health.json()
        self.assertIn("status", data)
        self.assertIn("active_games", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

import requests

try:
    import redis  # type: ignore[import-not-found]
except ImportError:
    redis = None


def _is_transient_connection_error(ex):
    if not isinstance(ex, requests.exceptions.RequestException):
        return False
    msg = str(ex).lower()
    markers = [
        "connection refused",
        "failed to establish a new connection",
        "max retries exceeded",
        "read timed out",
        "connect timeout",
        "temporarily unavailable",
    ]
    return any(marker in msg for marker in markers)


def _wait_for_server(base_url, max_wait_sec=30, probe_interval_sec=1.0):
    deadline = time.time() + max(0.0, float(max_wait_sec))
    probe_url = f"{str(base_url).rstrip('/')}/api/status"
    while time.time() < deadline:
    
        # Endpoint may return non-200 when no default game exists; reachability is enough.
        requests.get(probe_url, timeout=1.5)
        return True
        
    return False


def _format_duration(seconds):
    total_seconds = max(0, int(round(float(seconds))))
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def _render_progress_line(prefix, completed, total, started_at, width=24):
    total = max(1, int(total))
    completed = max(0, min(int(completed), total))
    elapsed = max(0.0, time.monotonic() - started_at)
    pct = completed / total
    filled = int(round(width * pct))
    filled = max(0, min(filled, width))
    bar = "#" * filled + "-" * (width - filled)
    rate = completed / elapsed if completed > 0 and elapsed > 0 else 0.0
    remaining = total - completed
    eta = remaining / rate if rate > 0 else None
    eta_text = _format_duration(eta) if eta is not None else "--:--"
    return (
        f"\r{prefix} [{bar}] {completed}/{total} "
        f"({pct * 100:5.1f}%) elapsed {_format_duration(elapsed)} ETA {eta_text}"
    )


def _write_progress_line(line):
    sys.stderr.write(line)
    sys.stderr.flush()


def _finish_progress_line():
    sys.stderr.write("\n")
    sys.stderr.flush()


class DataGatherer:
    """Collect match data for bot-vs-bot games from Sueca server endpoints."""

    def __init__(
        self,
        game_number,
        agents,
        base_url="http://127.0.0.1:5000",
        poll_interval=0.05,
        capture_timeline=True,
    ):
        self.game_number = game_number
        self.agents = agents or []
        self.base_url = base_url.rstrip("/")
        self.poll_interval = float(poll_interval)
        self.capture_timeline = bool(capture_timeline)
        self.game_id = None
        self.action_data = []
        self._last_round_plays_len = 0
        self._last_hands_by_player_id = {}

        self.game_data = {
            "game_number": game_number,
            "game_id": None,
            "agent_configuration": deepcopy(self.agents),
            "agent_difficulties": {a.get("name"): a.get("difficulty") for a in self.agents if isinstance(a, dict)},
            "final_scores": None,
            "trump_card": None,
            "trump_card_suit": None,
            "cut_index": None,
            "trump_choice": None,
            "winner_team": None,
            "winner_label": None,
            "match_number": None,
            "rounds_played": None,
            "finished_at": None,
            "matches_played": 0,
            "phase": None,
            "player_names": [],
            "team_map": {},
            "timeline": [],
        }

        self.round_data = {}
        self._last_seen_round = None
        self._last_phase = None

    def _infer_rounds_played(self):
        rounds = 0
        for data in self.round_data.values():
            if not isinstance(data, dict):
                continue
            if (
                data.get("cards_played")
                or data.get("team_scores_before") is not None
                or data.get("team_scores_after") is not None
            ):
                rounds += 1

        matches_played = self.game_data.get("matches_played")
        if isinstance(matches_played, int) and matches_played > 0:
            rounds = max(rounds, matches_played)

        return rounds or None

    @staticmethod
    def _is_finished_state(state):
        if not isinstance(state, dict):
            return False
        phase = str(state.get("phase") or "").strip().lower()
        if phase == "finished":
            return True
        if bool(state.get("game_finished")):
            return True
        return False

    def _start_round(self, round_number):
        round_key = f"round_{round_number}"
        if round_key not in self.round_data:
            self.round_data[round_key] = {
                "points": None,
                "team_scores_before": None,
                "team_scores_after": None,
                "cards_played": [],
                "bot_perception": {},
                "reasoning_protocol": {},
                "round_suit": None,
                "winner_team": None,
                "winner_player": None,
                "winner_id": None,
            }
        return round_key

    @staticmethod
    def _derive_round_outcome(before_scores, after_scores):
        before_scores = before_scores or {}
        after_scores = after_scores or {}

        t1_before = int(before_scores.get("team1", 0) or 0)
        t2_before = int(before_scores.get("team2", 0) or 0)
        t1_after = int(after_scores.get("team1", 0) or 0)
        t2_after = int(after_scores.get("team2", 0) or 0)

        delta_t1 = t1_after - t1_before
        delta_t2 = t2_after - t2_before

        if delta_t1 > delta_t2:
            winner_team = "team1"
            points = delta_t1
        elif delta_t2 > delta_t1:
            winner_team = "team2"
            points = delta_t2
        else:
            winner_team = None
            points = max(delta_t1, delta_t2)

        return winner_team, points

    def _gather_round_metric(self, round_number, metric, value):
        round_key = self._start_round(round_number)
        self.round_data[round_key][metric] = value

    def _gather_bot_perception(self, round_number, agent, perception_data):
        round_key = self._start_round(round_number)
        self.round_data[round_key]["bot_perception"][agent] = perception_data

    def _gather_bot_reasoning(self, round_number, agent, reasoning_prot):
        round_key = self._start_round(round_number)
        self.round_data[round_key]["reasoning_protocol"][agent] = reasoning_prot

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        response = requests.request(method=method, url=url, timeout=5, **kwargs)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _to_int_card(card):
        try:
            return int(card)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _card_suit(card):
        card_id = DataGatherer._to_int_card(card)
        if card_id is None or card_id < 0:
            return None
        suits = ["♣", "♦", "♥", "♠"]
        suit_index = card_id // 10
        if 0 <= suit_index < len(suits):
            return suits[suit_index]
        return None

    @staticmethod
    def _compute_legal_moves(hand_before, lead_suit):
        hand_before = list(hand_before or [])
        if not hand_before or not lead_suit:
            return hand_before

        suited_cards = [card for card in hand_before if DataGatherer._card_suit(card) == lead_suit]
        return suited_cards if suited_cards else hand_before

    def _fetch_hands_snapshot(self, state):
        players = state.get("players") or []
        game_id = self.game_id
        if not game_id:
            return {}

        snapshot = {}
        for player in players:
            player_id = player.get("id") if isinstance(player, dict) else None
            if not player_id:
                continue
            try:
                payload = self._request("GET", f"/api/hand/{player_id}?game_id={game_id}")
                hand = payload.get("hand") or []
                snapshot[player_id] = [
                    card_id
                    for card_id in (self._to_int_card(card) for card in hand)
                    if card_id is not None
                ]
            except Exception:
                # Keep batch collection resilient when hand endpoint is unavailable.
                continue
        return snapshot

    def create_bot_match(self, bots=None, join_timeout_sec=8.0, fast_mode=False):
        payload = {"join_timeout_sec": join_timeout_sec}
        if bots is not None:
            payload["bots"] = bots
        if fast_mode:
            payload["fast_mode"] = True

        data = self._request("POST", "/api/create_bot_match", json=payload)
        if not data.get("game_id"):
            raise RuntimeError(f"create_bot_match failed: {data}")

        self.game_id = data["game_id"]
        self.game_data["game_id"] = self.game_id

        bots_payload = data.get("bots") or bots or []
        if bots_payload:
            self.agents = bots_payload
            self.game_data["agent_configuration"] = deepcopy(bots_payload)
            self.game_data["agent_difficulties"] = {
                b.get("name"): b.get("difficulty")
                for b in bots_payload
                if isinstance(b, dict)
            }

        return data

    def get_status(self, game_id=None):
        target_game_id = game_id or self.game_id
        if not target_game_id:
            raise ValueError("game_id is required")
        return self._request("GET", f"/api/status?game_id={target_game_id}")

    def get_history(self, game_id=None):
        target_game_id = game_id or self.game_id
        if not target_game_id:
            raise ValueError("game_id is required")
        return self._request("GET", f"/api/room/{target_game_id}/history")

    def _append_timeline(self, state):
        if not self.capture_timeline:
            return
        self.game_data["timeline"].append(
            {
                "ts": time.time(),
                "phase": state.get("phase"),
                "current_round": state.get("current_round"),
                "team_scores": deepcopy(state.get("team_scores")),
                "round_plays": deepcopy(state.get("round_plays", [])),
            }
        )

    def save_actions_csv(self, output_path):
        if not self.action_data:
            return None

        fieldnames = list(self.action_data[0].keys())

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.action_data)

        return output_path
    
    def _extract_action(self, state, play, position_in_trick, hand_before=None, legal_moves=None, lead_suit=None):
        try:
            cards = deepcopy(state.get("round_plays", []))

            # remove the last play (current one)
            cards_before = cards[:-1] if cards else []
            return {
                "game_id": self.game_id,
                "round": state.get("current_round"),

                "player": play.get("player_name"),
                "position": play.get("position"),
                "card_played": play.get("card"),

                # 🔥 CONTEXT
                "cards_in_trick": cards_before,
                "position_in_trick": position_in_trick,

                "lead_suit": lead_suit if lead_suit is not None else state.get("round_suit"),
                "trump": state.get("trump_suit"),

                "team_scores": deepcopy(state.get("team_scores")),

                "hand_before": deepcopy(hand_before) if hand_before is not None else None,
                "legal_moves": deepcopy(legal_moves) if legal_moves is not None else None,
            }
        except Exception:
            return None

    def _ingest_state(self, state, current_hands_by_player_id=None):
        phase = state.get("phase")
        round_number = state.get("current_round")
        team_scores = deepcopy(state.get("team_scores", {}))
        round_plays = deepcopy(state.get("round_plays", []))
        players = state.get("players") or []
        id_by_name = {
            p.get("name"): p.get("id")
            for p in players
            if isinstance(p, dict) and p.get("name") and p.get("id")
        }
        hands_working = {
            player_id: list(hand)
            for player_id, hand in (self._last_hands_by_player_id or {}).items()
        }

        if isinstance(round_number, int) and round_number > 0:
            new_plays = round_plays[self._last_round_plays_len:]
            trick_offset = len(round_plays) - len(new_plays)

            for idx, play in enumerate(new_plays):
                position_in_trick = trick_offset + idx
                lead_suit = None
                if position_in_trick > 0 and round_plays:
                    lead_suit = self._card_suit(round_plays[0].get("card"))

                player_id = play.get("player_id") or id_by_name.get(play.get("player_name"))
                hand_before = None
                legal_moves = None
                if player_id in hands_working:
                    hand_before = list(hands_working[player_id])
                    legal_moves = self._compute_legal_moves(hand_before, lead_suit)
                    played_card_id = self._to_int_card(play.get("card"))
                    if played_card_id in hands_working[player_id]:
                        hands_working[player_id].remove(played_card_id)

                action = self._extract_action(
                    state,
                    play,
                    position_in_trick,
                    hand_before=hand_before,
                    legal_moves=legal_moves,
                    lead_suit=lead_suit,
                )
                if action:
                    self.action_data.append(action)

            self._last_round_plays_len = len(round_plays)

        if current_hands_by_player_id:
            self._last_hands_by_player_id = {
                player_id: list(hand)
                for player_id, hand in current_hands_by_player_id.items()
            }
        elif hands_working:
            self._last_hands_by_player_id = hands_working

        self.game_data["phase"] = phase
        self.game_data["matches_played"] = state.get("matches_played", 0)
        self.game_data["player_names"] = [p.get("name") for p in players]
        self.game_data["team_map"] = deepcopy(state.get("teams", {}))
        self.game_data["trump_card"] = state.get("trump")
        self.game_data["trump_card_suit"] = state.get("trump_suit")
        self.game_data["cut_index"] = state.get("cut_index")
        self.game_data["trump_choice"] = state.get("trump_choice")

        if isinstance(round_number, int) and round_number > 0:
            active_round = min(round_number, 10)
            round_key = self._start_round(active_round)
            if self.round_data[round_key]["team_scores_before"] is None:
                self.round_data[round_key]["team_scores_before"] = deepcopy(team_scores)

            # Preserve latest non-empty trick cards and avoid wiping round 10 at finished phase.
            if round_plays:
                self.round_data[round_key]["cards_played"] = round_plays

            round_suit = state.get("round_suit")
            if round_suit is not None:
                self.round_data[round_key]["round_suit"] = round_suit

        if (
            isinstance(self._last_seen_round, int)
            and isinstance(round_number, int)
            and round_number > self._last_seen_round
            and self._last_seen_round <= 10
        ):
            prev_key = self._start_round(self._last_seen_round)
            self.round_data[prev_key]["team_scores_after"] = deepcopy(team_scores)
            winner_team, points = self._derive_round_outcome(
                self.round_data[prev_key].get("team_scores_before"),
                self.round_data[prev_key].get("team_scores_after"),
            )
            self.round_data[prev_key]["winner_team"] = winner_team
            self.round_data[prev_key]["points"] = points

        self._last_seen_round = round_number if isinstance(round_number, int) else self._last_seen_round
        self._last_phase = phase
        self._append_timeline(state)

    def _finalize_from_history(self, history_payload):
        history = history_payload.get("history") or []
        if not history:
            return

        last_match = history[-1]
        self.game_data["final_scores"] = deepcopy(last_match.get("team_scores"))
        self.game_data["winner_team"] = last_match.get("winner_team")
        self.game_data["winner_label"] = last_match.get("winner_label")
        self.game_data["match_number"] = last_match.get("match_number")
        self.game_data["finished_at"] = last_match.get("finished_at")
        if self.game_data.get("cut_index") is None:
            self.game_data["cut_index"] = last_match.get("cut_index")
        if self.game_data.get("trump_choice") is None:
            self.game_data["trump_choice"] = last_match.get("trump_choice")
        if self.game_data.get("trump_card") is None:
            self.game_data["trump_card"] = last_match.get("trump_card")
        if self.game_data.get("trump_card_suit") is None:
            self.game_data["trump_card_suit"] = last_match.get("trump_suit")

        # Ensure last round derived metrics exist when match has just ended.
        if self._last_seen_round and self._last_seen_round <= 10:
            last_round_key = self._start_round(self._last_seen_round)
            if self.round_data[last_round_key].get("team_scores_after") is None:
                self.round_data[last_round_key]["team_scores_after"] = deepcopy(last_match.get("team_scores", {}))
            winner_team, points = self._derive_round_outcome(
                self.round_data[last_round_key].get("team_scores_before"),
                self.round_data[last_round_key].get("team_scores_after"),
            )
            self.round_data[last_round_key]["winner_team"] = winner_team
            self.round_data[last_round_key]["points"] = points

        self.game_data["rounds_played"] = self._infer_rounds_played()

    def collect_until_finished(self, game_id=None, timeout_sec=180):
        target_game_id = game_id or self.game_id
        if not target_game_id:
            raise ValueError("game_id is required")
        self.game_id = target_game_id
        self.game_data["game_id"] = target_game_id

        timeout_val = float(timeout_sec)
        deadline = None if timeout_val <= 0 else (time.time() + timeout_val)
        last_state = None
        finished = False

        while True:
            if deadline is not None and time.time() >= deadline:
                break
            state = self.get_status(target_game_id)
            last_state = state
            hands_snapshot = self._fetch_hands_snapshot(state)
            self._ingest_state(state, current_hands_by_player_id=hands_snapshot)

            if self._is_finished_state(state):
                history_payload = self.get_history(target_game_id)
                self._finalize_from_history(history_payload)
                finished = True
                break

            phase = str(state.get("phase") or "").strip().lower()
            effective_interval = self.poll_interval
            if phase in {"waiting", "deck_cutting", "trump_selection"}:
                effective_interval = min(self.poll_interval, 0.1)
            time.sleep(max(0.01, float(effective_interval)))

        if last_state is None:
            raise RuntimeError("No state collected")

        if not self.game_data.get("final_scores"):
            # Fallback finalization for states where phase changed but history already has result.
            history_payload = self.get_history(target_game_id)
            self._finalize_from_history(history_payload)

        if not self.game_data.get("final_scores"):
            if deadline is None:
                raise RuntimeError(
                    f"Game {target_game_id} ended without final_scores while timeout was disabled"
                )
            raise TimeoutError(
                f"Game {target_game_id} did not finish within {timeout_sec}s; no final_scores available"
            )

        # Some server states may not set a finished phase consistently; final scores are authoritative.
        if not finished and self.game_data.get("final_scores"):
            self.game_data["phase"] = "finished"

        return self.to_dict()

    def to_dict(self):
        return {
            "game_data": deepcopy(self.game_data),
            "round_data": deepcopy(self.round_data),
        }

    def save_json(self, output_path):
        payload = self.to_dict()
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return output_path

    def _csv_rows(self):
        rows = []
        final_scores = self.game_data.get("final_scores") or {}
        summary_row = {
            "game_number": self.game_data.get("game_number"),
            "game_id": self.game_data.get("game_id"),
            "row_type": "summary",
            "round_number": "",
            "phase": self.game_data.get("phase"),
            "match_number": self.game_data.get("match_number"),
            "rounds_played": self.game_data.get("rounds_played"),
            "winner_team": self.game_data.get("winner_team"),
            "winner_label": self.game_data.get("winner_label"),
            "team1_score": final_scores.get("team1"),
            "team2_score": final_scores.get("team2"),
            "trump_card": self.game_data.get("trump_card"),
            "trump_suit": self.game_data.get("trump_card_suit"),
            "cut_index": self.game_data.get("cut_index"),
            "trump_choice": self.game_data.get("trump_choice"),
            "finished_at": self.game_data.get("finished_at"),
            "round_points": "",
            "round_winner_team": "",
            "winner_player": "",
            "winner_id": "",
            "cards_played_json": "",
            "team_scores_before_json": "",
            "team_scores_after_json": "",
        }
        rows.append(summary_row)

        def _round_sort_key(k):
            try:
                return int(k.split("_")[1])
            except Exception:
                return 0

        for round_key in sorted(self.round_data.keys(), key=_round_sort_key):
            round_number = _round_sort_key(round_key)
            data = self.round_data[round_key]
            rows.append(
                {
                    "game_number": self.game_data.get("game_number"),
                    "game_id": self.game_data.get("game_id"),
                    "row_type": "round",
                    "round_number": round_number,
                    "phase": "",
                    "match_number": self.game_data.get("match_number"),
                    "rounds_played": "",
                    "winner_team": "",
                    "winner_label": "",
                    "team1_score": "",
                    "team2_score": "",
                    "trump_card": self.game_data.get("trump_card"),
                    "trump_suit": self.game_data.get("trump_card_suit"),
                    "cut_index": self.game_data.get("cut_index"),
                    "trump_choice": self.game_data.get("trump_choice"),
                    "finished_at": "",
                    "round_points": data.get("points"),
                    "round_winner_team": data.get("winner_team"),
                    "winner_player": data.get("winner_player"),
                    "winner_id": data.get("winner_id"),
                    "cards_played_json": json.dumps(data.get("cards_played", []), ensure_ascii=False),
                    "team_scores_before_json": json.dumps(data.get("team_scores_before", {}), ensure_ascii=False),
                    "team_scores_after_json": json.dumps(data.get("team_scores_after", {}), ensure_ascii=False),
                }
            )

        return rows

    def redis_document(self):
        summary = None
        rounds = []
        rows = self._csv_rows()
        if rows:
            summary = rows[0]
            rounds = rows[1:]
        return {
            "game_number": self.game_data.get("game_number"),
            "game_id": self.game_data.get("game_id"),
            "summary": summary,
            "rounds": rounds,
            "game_data": deepcopy(self.game_data),
            "round_data": deepcopy(self.round_data),
            "saved_at_epoch": time.time(),
        }

    def save_to_redis(self, redis_client, key_prefix="sueca:game"):
        game_id = self.game_data.get("game_id") or f"unknown_{self.game_data.get('game_number', 0)}"
        redis_key = f"{key_prefix}:{game_id}"
        redis_client.set(redis_key, json.dumps(self.redis_document(), ensure_ascii=False))
        return redis_key

    def save_csv(self, output_path):
        rows = self._csv_rows()
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        fieldnames = [
            "game_number",
            "game_id",
            "row_type",
            "round_number",
            "phase",
            "match_number",
            "rounds_played",
            "winner_team",
            "winner_label",
            "team1_score",
            "team2_score",
            "trump_card",
            "trump_suit",
            "cut_index",
            "trump_choice",
            "finished_at",
            "round_points",
            "round_winner_team",
            "winner_player",
            "winner_id",
            "cards_played_json",
            "team_scores_before_json",
            "team_scores_after_json",
        ]

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return output_path

    @staticmethod
    def _safe_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _compact_cards(cards):
        if not cards:
            return ""
        compact = []
        for play in cards:
            name = play.get("player_name", "?")
            position = play.get("position", "?")
            card = play.get("card", "?")
            compact.append(f"{name}:{position}:{card}")
        return " | ".join(compact)

    def _summary_row_compact(self):
        final_scores = self.game_data.get("final_scores") or {}
        return {
            "game_number": self.game_data.get("game_number"),
            "game_id": self.game_data.get("game_id"),
            "match_number": self.game_data.get("match_number"),
            "rounds_played": self.game_data.get("rounds_played"),
            "winner_team": self.game_data.get("winner_team"),
            "winner_label": self.game_data.get("winner_label"),
            "team1_score": final_scores.get("team1"),
            "team2_score": final_scores.get("team2"),
            "trump_card": self.game_data.get("trump_card"),
            "trump_suit": self.game_data.get("trump_card_suit"),
            "phase": self.game_data.get("phase"),
            "finished_at": self.game_data.get("finished_at"),
        }

    def _round_rows_compact(self):
        rows = []

        def _round_sort_key(k):
            try:
                return int(k.split("_")[1])
            except Exception:
                return 0

        for round_key in sorted(self.round_data.keys(), key=_round_sort_key):
            round_number = _round_sort_key(round_key)
            data = self.round_data[round_key]
            before = data.get("team_scores_before") or {}
            after = data.get("team_scores_after") or {}
            cards = data.get("cards_played") or []
            rows.append(
                {
                    "game_number": self.game_data.get("game_number"),
                    "game_id": self.game_data.get("game_id"),
                    "round_number": round_number,
                    "round_points": data.get("points"),
                    "round_winner_team": data.get("winner_team"),
                    "team1_before": before.get("team1"),
                    "team2_before": before.get("team2"),
                    "team1_after": after.get("team1"),
                    "team2_after": after.get("team2"),
                    "cards_played_count": len(cards),
                    "cards_played": self._compact_cards(cards),
                }
            )

        return rows

    @staticmethod
    def _write_csv(path, fieldnames, rows):
        output_dir = os.path.dirname(path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def save_split_csv(self, output_base_path):
        base, ext = os.path.splitext(output_base_path)
        if ext.lower() == ".csv":
            output_base_path = base

        summary_path = f"{output_base_path}_summary.csv"
        rounds_path = f"{output_base_path}_rounds.csv"

        summary_fields = [
            "game_number",
            "game_id",
            "match_number",
            "rounds_played",
            "winner_team",
            "winner_label",
            "team1_score",
            "team2_score",
            "trump_card",
            "trump_suit",
            "phase",
            "finished_at",
        ]
        rounds_fields = [
            "game_number",
            "game_id",
            "round_number",
            "round_points",
            "round_winner_team",
            "team1_before",
            "team2_before",
            "team1_after",
            "team2_after",
            "cards_played_count",
            "cards_played",
        ]

        self._write_csv(summary_path, summary_fields, [self._summary_row_compact()])
        self._write_csv(rounds_path, rounds_fields, self._round_rows_compact())

        return summary_path, rounds_path

    @staticmethod
    def run_batch(
        match_count,
        output_dir,
        base_url="http://127.0.0.1:5000",
        timeout_sec=180,
        poll_interval=0.25,
        join_timeout_sec=2.0,
        bots=None,
        split_csv=False,
        redis_client=None,
        redis_key_prefix="sueca:game",
        workers=1,
        continue_on_error=True,
        match_retries=2,
        retry_backoff_sec=1.0,
        max_consecutive_connection_errors=10,
        server_recovery_wait_sec=30.0,
        save_game_files=True,
        run_metadata=None,
    ):
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        tables_dir = output_root / "tables"
        manifests_dir = output_root / "manifests"
        metadata_dir = output_root / "metadata"
        games_dir = output_root / "games"

        tables_dir.mkdir(parents=True, exist_ok=True)
        manifests_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        if save_game_files:
            games_dir.mkdir(parents=True, exist_ok=True)

        if run_metadata is not None:
            run_metadata_path = metadata_dir / "run_config.json"
            with open(run_metadata_path, "w", encoding="utf-8") as f:
                json.dump(run_metadata, f, indent=2, ensure_ascii=False)

        bots_payload = bots or _default_bots()
        manifest = []
        batch_summary_rows = []
        batch_round_rows = []
        interrupted = False
        progress_enabled = True
        progress_inline = sys.stderr.isatty()
        progress_last_logged = -1
        progress_started_at = time.monotonic()
        progress_completed = 0

        def _update_progress():
            nonlocal progress_last_logged
            if not progress_enabled:
                return
            if progress_inline:
                _write_progress_line(_render_progress_line("Progress", progress_completed, total_matches, progress_started_at))
                return

            # In non-interactive terminals, emit discrete progress checkpoints.
            step = max(1, total_matches // 100)
            should_log = (progress_completed == total_matches) or (progress_completed % step == 0)
            if not should_log or progress_completed == progress_last_logged:
                return
            progress_last_logged = progress_completed
            sys.stderr.write(
                _render_progress_line("Progress", progress_completed, total_matches, progress_started_at).lstrip("\r")
                + "\n"
            )
            sys.stderr.flush()

        def _mark_progress_step():
            nonlocal progress_completed
            progress_completed += 1
            _update_progress()

        def _run_single_match(i):
            gatherer = DataGatherer(
                game_number=i,
                agents=deepcopy(bots_payload),
                base_url=base_url,
                poll_interval=poll_interval,
                capture_timeline=save_game_files,
            )
            create_resp = gatherer.create_bot_match(
                bots=deepcopy(bots_payload),
                join_timeout_sec=join_timeout_sec,
                fast_mode=True,
            )
            game_id = create_resp.get("game_id") or f"match_{i}"
            gatherer.collect_until_finished(timeout_sec=timeout_sec)

            json_path = None
            if save_game_files:
                json_path = games_dir / f"game_data_{i:03d}_{game_id}.json"
                gatherer.save_json(str(json_path))

            csv_path = None
            if save_game_files and not split_csv:
                csv_path = games_dir / f"game_data_{i:03d}_{game_id}.csv"
                gatherer.save_csv(str(csv_path))

            redis_key = None
            if redis_client is not None:
                redis_key = gatherer.save_to_redis(redis_client, key_prefix=redis_key_prefix)

            actions_csv_path = None
            if save_game_files:
                actions_csv_path = games_dir / f"actions_{i:03d}_{game_id}.csv"
                gatherer.save_actions_csv(str(actions_csv_path))

            return {
                "game_number": i,
                "game_id": game_id,
                "json_path": str(json_path) if json_path else None,
                "csv_path": str(csv_path) if csv_path else None,
                "winner_team": gatherer.game_data.get("winner_team"),
                "winner_label": gatherer.game_data.get("winner_label"),
                "final_scores": gatherer.game_data.get("final_scores"),
                "redis_key": redis_key,
                "summary_row": gatherer._summary_row_compact(),
                "round_rows": gatherer._round_rows_compact(),
                "actions_csv": str(actions_csv_path) if actions_csv_path else None,
            }

        def _run_single_match_with_retries(i):
            total_attempts = max(1, int(match_retries))
            last_ex = None
            for attempt in range(1, total_attempts + 1):
                try:
                    return _run_single_match(i)
                except Exception as ex:
                    last_ex = ex
                    if _is_transient_connection_error(ex) and attempt < total_attempts:
                        time.sleep(max(0.1, float(retry_backoff_sec)) * attempt)
                        continue
                    raise
            if last_ex is not None:
                raise last_ex
            raise RuntimeError(f"Unknown error while running match {i}")

        total_matches = int(match_count)
        max_workers = max(1, int(workers))
        if max_workers == 1:
            consecutive_connection_errors = 0
            for i in range(1, total_matches + 1):
                try:
                    result = _run_single_match_with_retries(i)
                    manifest.append({k: v for k, v in result.items() if k not in {"summary_row", "round_rows"}})
                    if split_csv:
                        batch_summary_rows.append(result["summary_row"])
                        batch_round_rows.extend(result["round_rows"])
                    consecutive_connection_errors = 0
                    _mark_progress_step()
                except KeyboardInterrupt:
                    interrupted = True
                    manifest.append(
                        {
                            "batch_aborted": True,
                            "reason": "user_interrupt",
                            "stopped_after_game": i,
                        }
                    )
                    _mark_progress_step()
                    break
                except Exception as ex:
                    is_connection_error = _is_transient_connection_error(ex)

                    if is_connection_error and server_recovery_wait_sec > 0:
                        recovered = _wait_for_server(base_url, max_wait_sec=server_recovery_wait_sec)
                        if recovered:
                            try:
                                result = _run_single_match_with_retries(i)
                                manifest.append({k: v for k, v in result.items() if k not in {"summary_row", "round_rows"}})
                                if split_csv:
                                    batch_summary_rows.append(result["summary_row"])
                                    batch_round_rows.extend(result["round_rows"])
                                consecutive_connection_errors = 0
                                _mark_progress_step()
                                continue
                            except Exception as retry_ex:
                                ex = retry_ex
                                is_connection_error = _is_transient_connection_error(ex)

                    error_record = {
                        "game_number": i,
                        "error": str(ex),
                    }
                    if is_connection_error:
                        error_record["error_type"] = "server_connection"
                    manifest.append(error_record)

                    if is_connection_error:
                        consecutive_connection_errors += 1
                    else:
                        consecutive_connection_errors = 0

                    _mark_progress_step()

                    if is_connection_error and consecutive_connection_errors >= max(1, int(max_consecutive_connection_errors)):
                        manifest.append(
                            {
                                "batch_aborted": True,
                                "reason": "server_unreachable",
                                "stopped_after_game": i,
                                "consecutive_connection_errors": consecutive_connection_errors,
                            }
                        )
                        break

                    if not continue_on_error:
                        raise
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(_run_single_match_with_retries, i): i
                    for i in range(1, total_matches + 1)
                }
                for future in as_completed(future_map):
                    i = future_map[future]
                    try:
                        result = future.result()
                        manifest.append({k: v for k, v in result.items() if k not in {"summary_row", "round_rows"}})
                        if split_csv:
                            batch_summary_rows.append(result["summary_row"])
                            batch_round_rows.extend(result["round_rows"])
                        _mark_progress_step()
                    except KeyboardInterrupt:
                        interrupted = True
                        manifest.append(
                            {
                                "batch_aborted": True,
                                "reason": "user_interrupt",
                                "stopped_after_game": i,
                            }
                        )
                        _mark_progress_step()
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    except Exception as ex:
                        error_record = {
                            "game_number": i,
                            "error": str(ex),
                        }
                        if _is_transient_connection_error(ex):
                            error_record["error_type"] = "server_connection"
                        manifest.append(error_record)
                        _mark_progress_step()
                        if not continue_on_error:
                            raise

            manifest.sort(
                key=lambda r: (
                    1 if r.get("batch_aborted") else 0,
                    int(r.get("game_number", 0) or 0),
                )
            )

        if split_csv:
            summary_path = tables_dir / "batch_summary.csv"
            rounds_path = tables_dir / "batch_rounds.csv"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            rounds_path.parent.mkdir(parents=True, exist_ok=True)
            DataGatherer._write_csv(
                str(summary_path),
                [
                    "game_number",
                    "game_id",
                    "match_number",
                    "rounds_played",
                    "winner_team",
                    "winner_label",
                    "team1_score",
                    "team2_score",
                    "trump_card",
                    "trump_suit",
                    "phase",
                    "finished_at",
                ],
                batch_summary_rows,
            )
            DataGatherer._write_csv(
                str(rounds_path),
                [
                    "game_number",
                    "game_id",
                    "round_number",
                    "round_points",
                    "round_winner_team",
                    "team1_before",
                    "team2_before",
                    "team1_after",
                    "team2_after",
                    "cards_played_count",
                    "cards_played",
                ],
                batch_round_rows,
            )

        manifest_path = manifests_dir / "batch_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        if interrupted:
            print("Batch interrupted. Partial outputs were saved.")

        if progress_enabled and progress_inline:
            _finish_progress_line()

        return manifest, str(manifest_path)


def _load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_single_bot_spec(index, spec):
    if not isinstance(spec, dict):
        raise ValueError(f"Bot entry #{index} must be an object")
    name = str(spec.get("name") or f"Bot{index}").strip()
    position = str(spec.get("position") or "").strip().upper()
    difficulty = str(spec.get("difficulty") or "random").strip().lower()
    if not name:
        raise ValueError(f"Bot entry #{index} has empty name")
    if position not in {"NORTH", "EAST", "SOUTH", "WEST"}:
        raise ValueError(f"Invalid position for {name}: {position}")
    return {
        "name": name,
        "position": position,
        "difficulty": difficulty,
    }


def _normalize_bots_payload(bots):
    if not isinstance(bots, list) or len(bots) != 4:
        raise ValueError("bots must be a list with exactly 4 entries")

    normalized = []
    seen_positions = set()
    seen_names = set()
    for i, spec in enumerate(bots, start=1):
        bot = _normalize_single_bot_spec(i, spec)
        if bot["position"] in seen_positions:
            raise ValueError(f"Duplicate position: {bot['position']}")
        if bot["name"] in seen_names:
            raise ValueError(f"Duplicate bot name: {bot['name']}")
        seen_positions.add(bot["position"])
        seen_names.add(bot["name"])
        normalized.append(bot)

    required_positions = {"NORTH", "EAST", "SOUTH", "WEST"}
    if seen_positions != required_positions:
        missing = sorted(required_positions - seen_positions)
        raise ValueError(f"Missing positions: {', '.join(missing)}")
    return normalized


def _parse_bots_from_args(args):
    if args.bots_file:
        return _normalize_bots_payload(_load_json_file(args.bots_file))
    if args.bots_json:
        return _normalize_bots_payload(json.loads(args.bots_json))
    return _default_bots()


def _difficulty_distribution_label(bots):
    order = ["NORTH", "EAST", "SOUTH", "WEST"]
    by_pos = {str(b.get("position", "")).upper(): str(b.get("difficulty", "random")).lower() for b in (bots or [])}
    parts = [by_pos.get(pos, "random") for pos in order]
    return "-".join(parts)


def _dedupe_labels(combinations):
    seen = {}
    result = []
    for combo in combinations:
        base = str(combo.get("label") or "combo").strip() or "combo"
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count == 1:
            combo["label"] = base
        else:
            combo["label"] = f"{base}-{count}"
        result.append(combo)
    return result


def _parse_combinations_from_args(args):
    payloads = []
    if args.combinations_files:
        for path in args.combinations_files:
            payloads.append(_load_json_file(path))
    elif args.combinations_file:
        payloads.append(_load_json_file(args.combinations_file))
    elif args.combinations_json:
        payloads.append(json.loads(args.combinations_json))
    else:
        return None

    combinations = []
    seq = 0
    for payload in payloads:
        if not isinstance(payload, list) or not payload:
            raise ValueError("Combinations payload must be a non-empty list")

        for combo in payload:
            seq += 1
            if isinstance(combo, dict) and "bots" in combo:
                bots = combo.get("bots")
                games = int(args.games_per_combination)
                normalized_bots = _normalize_bots_payload(bots)
                if args.name_by_difficulty:
                    label = _difficulty_distribution_label(normalized_bots)
                else:
                    label = str(combo.get("label") or f"combo_{seq:03d}")
            else:
                normalized_bots = _normalize_bots_payload(combo)
                games = int(args.games_per_combination)
                if args.name_by_difficulty:
                    label = _difficulty_distribution_label(normalized_bots)
                else:
                    label = f"combo_{seq:03d}"

            combinations.append(
                {
                    "label": label,
                    "games": max(1, games),
                    "bots": normalized_bots,
                }
            )

    return _dedupe_labels(combinations)


def _make_redis_client(args):
    if not args.save_to_redis:
        return None
    if redis is None:
        raise RuntimeError("redis package is not installed. Install with: pip install redis")

    client = redis.Redis(
        host=args.redis_host,
        port=int(args.redis_port),
        db=int(args.redis_db),
        password=args.redis_password,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    client.ping()
    return client


def _resolve_output_dir_with_generation(output_dir, generation):
    base = Path(output_dir)
    if not generation:
        return str(base)
    generation = str(generation).strip()
    if not generation:
        return str(base)
    if base.name == generation:
        return str(base)
    return str(base / generation)


def _resolve_generation_names(args):
    count = max(1, int(getattr(args, "generation_count", 1) or 1))
    if count == 1:
        generation = str(getattr(args, "generation", "Gen1") or "Gen1").strip() or "Gen1"
        return [generation]

    prefix = str(getattr(args, "generation_prefix", "Gen") or "Gen").strip() or "Gen"
    start = max(1, int(getattr(args, "generation_start", 1) or 1))
    return [f"{prefix}{idx}" for idx in range(start, start + count)]


def _should_split_by_generation(args):
    # Keep legacy combinations layout unless generation args were explicitly customized.
    if int(getattr(args, "generation_count", 1) or 1) > 1:
        return True
    generation = str(getattr(args, "generation", "Gen1") or "Gen1").strip() or "Gen1"
    if generation != "Gen1":
        return True
    prefix = str(getattr(args, "generation_prefix", "Gen") or "Gen").strip() or "Gen"
    if prefix != "Gen":
        return True
    start = int(getattr(args, "generation_start", 1) or 1)
    if start != 1:
        return True
    return False


def _default_bots():
    return [
        {"name": "Rita", "position": "NORTH", "difficulty": "random"},
        {"name": "Alyssa", "position": "EAST", "difficulty": "weak"},
        {"name": "Ava", "position": "SOUTH", "difficulty": "average"},
        {"name": "Serana", "position": "WEST", "difficulty": "random"},
    ]


def main():
    parser = argparse.ArgumentParser(description="Collect bot match metrics from Sueca server")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--game-id", default=None, help="Existing game id to observe")
    parser.add_argument("--create-match", action="store_true", help="Create a new 4-bot match first")
    parser.add_argument("--matches", type=int, default=1, help="Run N bot matches (batch mode)")
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=0,
        help="Per-game timeout in seconds. Use 0 to disable timeout and wait until game finishes.",
    )
    parser.add_argument("--poll-interval", type=float, default=0.03)
    parser.add_argument("--join-timeout-sec", type=float, default=2.0, help="Max wait for bots joining a match")
    parser.add_argument("--output", default="statistic-analysis/game_data.json")
    parser.add_argument("--csv-output", default=None, help="CSV output path for single-match mode")
    parser.add_argument("--output-dir", default="statistic-analysis/batch_output", help="Directory for batch outputs")
    parser.add_argument("--generation", default="Gen1", help="Generation folder name for batch outputs (e.g., Gen1, Gen2)")
    parser.add_argument("--generation-count", type=int, default=1, help="How many generations to run in one command")
    parser.add_argument("--generation-start", type=int, default=1, help="Start index when generation-count > 1")
    parser.add_argument("--generation-prefix", default="Gen", help="Generation prefix when generation-count > 1")
    parser.add_argument("--split-csv", action="store_true", help="Write cleaner summary/round CSV files")
    parser.add_argument(
        "--no-game-files",
        action="store_true",
        help="Batch mode: skip per-game JSON/CSV files; keep only batch manifest/CSVs and optional Redis",
    )
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers for batch mode")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue batch when a game fails")
    parser.add_argument("--match-retries", type=int, default=2, help="Retries per match for transient connection errors")
    parser.add_argument("--retry-backoff-sec", type=float, default=1.0, help="Backoff base in seconds between retries")
    parser.add_argument(
        "--max-consecutive-connection-errors",
        type=int,
        default=10,
        help="Abort sequential batch after N consecutive server connection errors",
    )
    parser.add_argument(
        "--server-recovery-wait-sec",
        type=float,
        default=30.0,
        help="Wait up to N seconds for server recovery after connection errors",
    )
    parser.add_argument("--bots-json", default=None, help="JSON string with 4 bot specs")
    parser.add_argument("--bots-file", default=None, help="Path to JSON file with 4 bot specs")
    parser.add_argument("--combinations-json", default=None, help="JSON list of bot combinations")
    parser.add_argument("--combinations-file", default=None, help="Path to JSON file with bot combinations")
    parser.add_argument("--combinations-files", nargs="+", default=None, help="Multiple combination files to merge and run")
    parser.add_argument("--name-by-difficulty", action="store_true", help="Use difficulty distribution as folder label")
    parser.add_argument("--games-per-combination", type=int, default=1000, help="Games per lineup in combinations mode")
    parser.add_argument("--save-to-redis", action="store_true", help="Persist each game in Redis")
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--redis-db", type=int, default=0)
    parser.add_argument("--redis-password", default=None)
    parser.add_argument("--redis-key-prefix", default="sueca:game")
    args = parser.parse_args()

    redis_client = _make_redis_client(args)
    combinations = _parse_combinations_from_args(args)
    selected_bots = _parse_bots_from_args(args)

    if combinations:
        root_output = Path(args.output_dir)
        root_output.mkdir(parents=True, exist_ok=True)
        all_manifests = []
        generation_names = _resolve_generation_names(args)
        split_by_generation = _should_split_by_generation(args)

        for generation_name in generation_names:
            for combo in combinations:
                if split_by_generation:
                    combo_dir = root_output / generation_name / combo["label"]
                else:
                    combo_dir = root_output / combo["label"]

                combo_manifest, combo_manifest_path = DataGatherer.run_batch(
                    match_count=combo["games"],
                    output_dir=str(combo_dir),
                    base_url=args.base_url,
                    timeout_sec=args.timeout_sec,
                    poll_interval=args.poll_interval,
                    join_timeout_sec=args.join_timeout_sec,
                    bots=combo["bots"],
                    split_csv=args.split_csv,
                    redis_client=redis_client,
                    redis_key_prefix=args.redis_key_prefix,
                    workers=args.workers,
                    continue_on_error=args.continue_on_error,
                    match_retries=args.match_retries,
                    retry_backoff_sec=args.retry_backoff_sec,
                    max_consecutive_connection_errors=args.max_consecutive_connection_errors,
                    server_recovery_wait_sec=args.server_recovery_wait_sec,
                    save_game_files=not args.no_game_files,
                    run_metadata={
                        "mode": "combinations",
                        "generation": generation_name,
                        "split_by_generation": split_by_generation,
                        "combination_label": combo.get("label"),
                        "games": combo.get("games"),
                        "base_url": args.base_url,
                        "timeout_sec": args.timeout_sec,
                        "poll_interval": args.poll_interval,
                        "join_timeout_sec": args.join_timeout_sec,
                        "split_csv": args.split_csv,
                        "save_game_files": (not args.no_game_files),
                        "save_to_redis": args.save_to_redis,
                        "redis_key_prefix": args.redis_key_prefix,
                        "bots": combo.get("bots"),
                        "fast_mode": True,
                    },
                )
                all_manifests.append(
                    {
                        "generation": generation_name,
                        "label": combo["label"],
                        "games": combo["games"],
                        "manifest_path": combo_manifest_path,
                        "manifest": combo_manifest,
                        "bots": combo["bots"],
                    }
                )

        root_manifest_path = root_output / "all_combinations_manifest.json"
        with open(root_manifest_path, "w", encoding="utf-8") as f:
            json.dump(all_manifests, f, indent=2, ensure_ascii=False)

        print(f"Combinations batch complete. Manifest saved to: {root_manifest_path}")
        return

    if args.matches > 1:
        generation_names = _resolve_generation_names(args)
        generation_reports = []
        difficulty_label = _difficulty_distribution_label(selected_bots)
        for generation_name in generation_names:
            resolved_output_dir = _resolve_output_dir_with_generation(args.output_dir, generation_name)
            if args.name_by_difficulty:
                resolved_output_dir = str(Path(args.output_dir) / difficulty_label / generation_name)
            manifest, manifest_path = DataGatherer.run_batch(
                match_count=args.matches,
                output_dir=resolved_output_dir,
                base_url=args.base_url,
                timeout_sec=args.timeout_sec,
                poll_interval=args.poll_interval,
                join_timeout_sec=args.join_timeout_sec,
                bots=selected_bots,
                split_csv=args.split_csv,
                redis_client=redis_client,
                redis_key_prefix=args.redis_key_prefix,
                workers=args.workers,
                continue_on_error=args.continue_on_error,
                match_retries=args.match_retries,
                retry_backoff_sec=args.retry_backoff_sec,
                max_consecutive_connection_errors=args.max_consecutive_connection_errors,
                server_recovery_wait_sec=args.server_recovery_wait_sec,
                save_game_files=not args.no_game_files,
                run_metadata={
                    "mode": "batch",
                    "generation": generation_name,
                    "matches": args.matches,
                    "base_url": args.base_url,
                    "timeout_sec": args.timeout_sec,
                    "poll_interval": args.poll_interval,
                    "join_timeout_sec": args.join_timeout_sec,
                    "split_csv": args.split_csv,
                    "save_game_files": (not args.no_game_files),
                    "save_to_redis": args.save_to_redis,
                    "redis_key_prefix": args.redis_key_prefix,
                    "bots": selected_bots,
                    "fast_mode": True,
                },
            )
            generation_reports.append(
                {
                    "generation": generation_name,
                    "manifest_path": manifest_path,
                    "manifest_records": len(manifest),
                }
            )

        if len(generation_reports) > 1:
            multi_manifest_path = Path(args.output_dir) / "multi_generation_batch_manifest.json"
            multi_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(multi_manifest_path, "w", encoding="utf-8") as f:
                json.dump(generation_reports, f, indent=2, ensure_ascii=False)
            print(f"Multi-generation batch complete. Manifest saved to: {multi_manifest_path}")
            print(json.dumps(generation_reports, indent=2, ensure_ascii=False))
        else:
            print(f"Batch complete. Manifest saved to: {generation_reports[0]['manifest_path']}")
        return

    gatherer = DataGatherer(
        game_number=1,
        agents=selected_bots,
        base_url=args.base_url,
        poll_interval=args.poll_interval,
    )

    if args.create_match:
        create_resp = gatherer.create_bot_match(bots=selected_bots)
        print(f"Created game: {create_resp.get('game_id')}")

    if args.game_id and not gatherer.game_id:
        gatherer.game_id = args.game_id

    payload = gatherer.collect_until_finished(timeout_sec=args.timeout_sec)
    gatherer.save_json(args.output)
    redis_key = None
    if redis_client is not None:
        redis_key = gatherer.save_to_redis(redis_client, key_prefix=args.redis_key_prefix)
    csv_output = args.csv_output
    if not csv_output:
        base, _ = os.path.splitext(args.output)
        csv_output = f"{base}.csv"
    if args.split_csv:
        summary_path, rounds_path = gatherer.save_split_csv(csv_output)
    else:
        gatherer.save_csv(csv_output)

    print(f"Saved data to: {args.output}")
    if args.split_csv:
        print(f"Saved summary CSV to: {summary_path}")
        print(f"Saved rounds CSV to: {rounds_path}")
    else:
        print(f"Saved CSV to: {csv_output}")
    if redis_key:
        print(f"Saved Redis key: {redis_key}")
    print(json.dumps(payload["game_data"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
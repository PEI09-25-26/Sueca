"""Normalization helpers to map engine-specific payloads into canonical contracts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import EventEnvelope, PlayerState, RoomState, TeamScoreState, TeamState


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def normalize_room_state(payload: Dict[str, Any], source: str = "unknown", mode: str = "virtual") -> RoomState:
    payload = payload or {}

    players_raw = payload.get("players") or []
    players: List[PlayerState] = []
    for player in players_raw:
        if not isinstance(player, dict):
            continue
        players.append(
            PlayerState(
                player_id=player.get("id") or player.get("player_id"),
                name=player.get("name") or player.get("player_name") or "",
                position=player.get("position"),
                cards_left=player.get("cards_left"),
            )
        )

    teams_raw = payload.get("teams") or {}
    team_scores_raw = payload.get("team_scores") or payload.get("scores") or {}

    metadata = {
        "match_points": payload.get("match_points"),
        "matches_played": payload.get("matches_played"),
        "current_match_number": payload.get("current_match_number"),
        "available_slots": payload.get("available_slots", []),
        "roles": {
            "cutter_player": payload.get("cutter_player"),
            "cutter_player_id": payload.get("cutter_player_id"),
            "cutter_position": payload.get("cutter_position"),
            "trump_selector_player": payload.get("trump_selector_player"),
            "trump_selector_player_id": payload.get("trump_selector_player_id"),
            "trump_selector_position": payload.get("trump_selector_position"),
        },
        "legacy": {
            "north_player": payload.get("north_player"),
            "north_player_id": payload.get("north_player_id"),
            "west_player": payload.get("west_player"),
            "west_player_id": payload.get("west_player_id"),
        },
    }

    return RoomState(
        source=source,
        mode=payload.get("mode") or mode,
        game_id=payload.get("game_id") or payload.get("room_id"),
        phase=payload.get("phase") or "unknown",
        game_started=bool(payload.get("game_started", False)),
        player_count=_to_int(payload.get("player_count", len(players))),
        players=players,
        teams=TeamState(
            team1=list(teams_raw.get("team1", [])) if isinstance(teams_raw, dict) else [],
            team2=list(teams_raw.get("team2", [])) if isinstance(teams_raw, dict) else [],
        ),
        team_scores=TeamScoreState(
            team1=_to_int(team_scores_raw.get("team1", 0)) if isinstance(team_scores_raw, dict) else 0,
            team2=_to_int(team_scores_raw.get("team2", 0)) if isinstance(team_scores_raw, dict) else 0,
        ),
        current_player_id=payload.get("current_player_id"),
        current_player_name=payload.get("current_player_name") or payload.get("current_player"),
        current_round=payload.get("current_round"),
        trump=payload.get("trump"),
        trump_suit=payload.get("trump_suit"),
        round_suit=payload.get("round_suit"),
        round_plays=list(payload.get("round_plays", [])),
        metadata=metadata,
    )


def normalize_event(payload: Dict[str, Any], source: str = "unknown", mode: str = "virtual") -> EventEnvelope:
    payload = payload or {}

    state_payload = payload.get("state") if isinstance(payload.get("state"), dict) else None
    room_state: Optional[RoomState] = None
    if state_payload is not None:
        room_state = normalize_room_state(state_payload, source=source, mode=mode)

    event_type = payload.get("type") or payload.get("event_type") or "unknown_event"
    game_id = payload.get("game_id")
    if not game_id and room_state:
        game_id = room_state.game_id

    envelope = EventEnvelope(
        event_type=event_type,
        source=source,
        game_id=game_id,
        player_id=payload.get("player_id") or payload.get("winner_id"),
        room_state=room_state,
        payload=payload,
    )
    return envelope


def to_dict(model: Any) -> Dict[str, Any]:
    return _as_dict(model)

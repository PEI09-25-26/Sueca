"""Canonical contracts shared across virtual and physical runtimes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlayerState(BaseModel):
    player_id: Optional[str] = None
    name: str = ""
    position: Optional[str] = None
    cards_left: Optional[int] = None


class TeamState(BaseModel):
    team1: List[str] = Field(default_factory=list)
    team2: List[str] = Field(default_factory=list)


class TeamScoreState(BaseModel):
    team1: int = 0
    team2: int = 0


class RoomState(BaseModel):
    contract: str = "sueca.room_state.v1"
    source: str = "unknown"
    mode: str = "virtual"
    game_id: Optional[str] = None
    phase: str = "waiting"
    game_started: bool = False
    player_count: int = 0
    players: List[PlayerState] = Field(default_factory=list)
    teams: TeamState = Field(default_factory=TeamState)
    team_scores: TeamScoreState = Field(default_factory=TeamScoreState)
    current_player_id: Optional[str] = None
    current_player_name: Optional[str] = None
    current_round: Optional[int] = None
    trump: Optional[str] = None
    trump_suit: Optional[str] = None
    round_suit: Optional[str] = None
    round_plays: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HandState(BaseModel):
    contract: str = "sueca.hand_state.v1"
    game_id: Optional[str] = None
    player_id: Optional[str] = None
    cards: List[str] = Field(default_factory=list)
    cards_left: Optional[int] = None


class EventEnvelope(BaseModel):
    contract: str = "sueca.event.v1"
    event_type: str
    source: str = "unknown"
    game_id: Optional[str] = None
    player_id: Optional[str] = None
    room_state: Optional[RoomState] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class CommandAck(BaseModel):
    contract: str = "sueca.command_ack.v1"
    success: bool
    message: str = ""
    command: Optional[str] = None
    game_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

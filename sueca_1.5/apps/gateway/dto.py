from pydantic import BaseModel
from typing import Any, Optional


class CardDetectionDTO(BaseModel):
    rank: str
    suit: str
    confidence: float


class ScanEventDTO(BaseModel):
    source: str
    success: bool
    message: str
    detection: Optional[CardDetectionDTO] = None


class StartGameRequest(BaseModel):
    playerName: str
    roomId: Optional[str] = None


class StartGameResponse(BaseModel):
    success: bool
    message: str
    gameId: str


class RoundEndData(BaseModel):
    round_number: int
    winner_team: int
    winner_points: int
    team1_points: int
    team2_points: int
    game_ended: bool


class RoomModeDTO(BaseModel):
    mode: str


class CommandRequestDTO(BaseModel):
    game_id: Optional[str] = None
    mode: Optional[str] = None
    payload: dict[str, Any] = {}

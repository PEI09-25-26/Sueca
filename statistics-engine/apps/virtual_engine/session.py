"""Session and token management for player-room binding."""

import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = "your-secret-key-change-in-production"
TOKEN_EXPIRY_MINUTES = 30


class Session:
    """Represents a player's session in a game room."""
    
    def __init__(self, game_id: str, player_id: str, player_name: str):
        self.game_id = game_id
        self.player_id = player_id
        self.player_name = player_name
        self.token = self._generate_token()
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
    
    def _generate_token(self) -> str:
        """Generate JWT token."""
        payload = {
            'game_id': self.game_id,
            'player_id': self.player_id,
            'player_name': self.player_name,
            'exp': datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
            'iat': datetime.now(timezone.utc),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    def is_valid(self) -> bool:
        """Check if session is still active."""
        try:
            jwt.decode(self.token, SECRET_KEY, algorithms=['HS256'])
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)


class SessionManager:
    """Manages player sessions across all rooms."""
    
    def __init__(self):
        self.sessions: dict[str, Session] = {}  # key: token
        self.player_sessions: dict[str, dict[str, str]] = {}  # game_id:player_id -> token
    
    def create_session(self, game_id: str, player_id: str, player_name: str) -> str:
        """Create new session and return token."""
        session = Session(game_id, player_id, player_name)
        self.sessions[session.token] = session
        
        # Track by game+player
        key = f"{game_id}:{player_id}"
        self.player_sessions[key] = session.token
        
        return session.token
    
    def validate_token(self, token: str) -> Optional[dict]:
        """Validate token and return session data."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            session = self.sessions.get(token)
            if session and session.is_valid():
                session.update_activity()
                return {
                    'game_id': payload['game_id'],
                    'player_id': payload['player_id'],
                    'player_name': payload['player_name'],
                }
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_session(self, token: str):
        """Revoke a session."""
        if token in self.sessions:
            session = self.sessions[token]
            key = f"{session.game_id}:{session.player_id}"
            del self.sessions[token]
            if key in self.player_sessions:
                del self.player_sessions[key]
    
    def get_session(self, game_id: str, player_id: str) -> Optional[str]:
        """Get token for a player in a game."""
        key = f"{game_id}:{player_id}"
        return self.player_sessions.get(key)


# Global session manager
session_manager = SessionManager()
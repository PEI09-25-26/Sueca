"""Session and token management for player-room binding."""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import logging
from shared.redis_client import revoke_jti, is_jti_revoked

SECRET_KEY = os.getenv("SUECA_PLAYER_SESSION_SECRET") or os.getenv("SUECA_JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("SUECA_JWT_SECRET or SUECA_PLAYER_SESSION_SECRET must be set")

logger = logging.getLogger(__name__)
TOKEN_EXPIRY_MINUTES = 30


def decode_session_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])


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
        jti = uuid.uuid4().hex
        exp_time = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
        payload = {
            'game_id': self.game_id,
            'player_id': self.player_id,
            'player_name': self.player_name,
            'exp': int(exp_time.timestamp()),
            'iat': int(datetime.now(timezone.utc).timestamp()),
            'jti': jti,
        }
        self.jti = jti
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    def is_valid(self) -> bool:
        """Check if session is still active."""
        try:
            payload = decode_session_token(self.token)
            jti = payload.get('jti')
            if jti and is_jti_revoked(jti):
                return False
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

        try:
            jti = getattr(session, 'jti', None)
            if jti:
                logger.info("Created session game=%s player=%s jti=%s", game_id, player_id, jti)
        except Exception:
            pass
        
        return session.token
    
    def validate_token(self, token: str) -> Optional[dict]:
        """Validate token and return session data."""
        try:
            payload = decode_session_token(token)
            session = self.sessions.get(token)
            if not session or not session.is_valid():
                return None
            session.update_activity()
            return {
                'game_id': payload['game_id'],
                'player_id': payload['player_id'],
                'player_name': payload['player_name'],
            }
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
            # Add JTI to denylist so the token can't be used until expiry
            try:
                # decode to get exp and jti
                payload = decode_session_token(token)
                jti = payload.get('jti')
                exp = int(payload.get('exp') or 0)
                if jti and exp:
                    ttl = max(0, exp - int(datetime.now(timezone.utc).timestamp()))
                    if ttl > 0:
                        revoke_jti(jti, ttl)
                        logger.info("Revoked session jti=%s ttl=%s", jti, ttl)
            except Exception:
                # best-effort; if we cannot decode, ignore
                pass
    
    def get_session(self, game_id: str, player_id: str) -> Optional[str]:
        """Get token for a player in a game."""
        key = f"{game_id}:{player_id}"
        return self.player_sessions.get(key)

    def delete_sessions_for_player(self, player_id: str):
        """Delete every active session for a player across rooms."""
        tokens_to_remove = [
            token
            for key, token in self.player_sessions.items()
            if key.split(":", 1)[-1] == player_id
        ]
        for token in tokens_to_remove:
            self.revoke_session(token)
        logger.info("Deleted sessions for player=%s tokens_removed=%s", player_id, len(tokens_to_remove))


# Global session manager
session_manager = SessionManager()

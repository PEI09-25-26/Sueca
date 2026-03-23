import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict

SECRET_KEY = "your-secret-key-change-in-production"
TOKEN_EXPIRY_MINUTES = 30


class Session:
    """Represents a player session with JWT token"""
    
    def __init__(self, game_id: str, player_id: str, player_name: str):
        self.game_id = game_id
        self.player_id = player_id
        self.player_name = player_name
        self.created_at = datetime.utcnow()
        self.token = self._generate_token()
    
    def _generate_token(self) -> str:
        """Generate JWT token for this session"""
        payload = {
            "game_id": self.game_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    
    def is_valid(self) -> bool:
        """Check if session token is still valid"""
        try:
            jwt.decode(self.token, SECRET_KEY, algorithms=["HS256"])
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False


class SessionManager:
    """Manages all active player sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}  # token -> Session
        self.player_sessions: Dict[str, str] = {}  # "game_id:player_id" -> token
    
    def create_session(self, game_id: str, player_id: str, player_name: str) -> str:
        """Create new session and return token"""
        session = Session(game_id, player_id, player_name)
        token = session.token
        
        # Store by token
        self.sessions[token] = session
        
        # Store by composite key for quick player lookup
        player_key = f"{game_id}:{player_id}"
        self.player_sessions[player_key] = token
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate token and return session data, or None if invalid"""
        if token not in self.sessions:
            return None
        
        session = self.sessions[token]
        if not session.is_valid():
            return None
        
        return {
            "game_id": session.game_id,
            "player_id": session.player_id,
            "player_name": session.player_name,
        }
    
    def revoke_session(self, token: str) -> bool:
        """Revoke (delete) a session"""
        if token not in self.sessions:
            return False
        
        session = self.sessions[token]
        player_key = f"{session.game_id}:{session.player_id}"
        
        del self.sessions[token]
        if player_key in self.player_sessions:
            del self.player_sessions[player_key]
        
        return True
    
    def get_session(self, token: str) -> Optional[Session]:
        """Get session object by token"""
        return self.sessions.get(token)


# Global session manager instance
session_manager = SessionManager()

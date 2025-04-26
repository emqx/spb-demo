from typing import Dict, Optional
from llama_index.core.memory import ChatMemoryBuffer
import time

class SessionStore:
    def __init__(self, session_timeout: int = 3600):  # 1 hour default timeout
        self.sessions: Dict[str, tuple[ChatMemoryBuffer, float]] = {}
        self.session_timeout = session_timeout
    
    def get_memory(self, session_id: str) -> Optional[ChatMemoryBuffer]:
        """Get memory for a session, return None if session expired or doesn't exist"""
        if session_id not in self.sessions:
            return None
        
        memory, last_access = self.sessions[session_id]
        if time.time() - last_access > self.session_timeout:
            # Session expired
            del self.sessions[session_id]
            return None
            
        # Update last access time
        self.sessions[session_id] = (memory, time.time())
        return memory
    
    def save_memory(self, session_id: str, memory: ChatMemoryBuffer):
        """Save or update memory for a session"""
        self.sessions[session_id] = (memory, time.time())
    
    def cleanup_expired(self):
        """Remove expired sessions"""
        current_time = time.time()
        expired = [
            sid for sid, (_, last_access) in self.sessions.items() 
            if current_time - last_access > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid] 
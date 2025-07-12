"""Redis service for session and chat history management"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage, MessageRole


class RedisService:
    """Service for managing chat sessions in Redis"""

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"

    async def connect(self):
        """Connect to Redis"""
        self.redis_client = await redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
        )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        key = f"{self.session_prefix}{session_id}"
        data = await self.redis_client.get(key)

        if data:
            session_data = json.loads(data)
            return ChatSession(**session_data)
        return None

    async def save_session(self, session: ChatSession) -> bool:
        """Save or update a chat session"""
        key = f"{self.session_prefix}{session.session_id}"

        # Update last activity
        session.last_activity = datetime.utcnow()

        # Convert to JSON
        session_data = session.model_dump(mode="json")

        # Save with TTL
        await self.redis_client.setex(
            key, settings.session_ttl, json.dumps(session_data, default=str)
        )

        # Also track session for user if user_id is provided
        if session.user_id:
            user_key = f"{self.user_sessions_prefix}{session.user_id}"
            await self.redis_client.sadd(user_key, session.session_id)
            await self.redis_client.expire(user_key, settings.session_ttl)

        return True

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a message to a session"""
        session = await self.get_session(session_id)

        if not session:
            # Create new session
            session = ChatSession(session_id=session_id)

        # Add message
        message = ChatMessage(role=role, content=content, metadata=metadata or {})
        session.messages.append(message)

        # Save session
        return await self.save_session(session)

    async def get_session_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages from a session"""
        session = await self.get_session(session_id)

        if not session:
            return []

        messages = session.messages
        if limit:
            messages = messages[-limit:]

        return messages

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        key = f"{self.session_prefix}{session_id}"

        # Get session to check for user_id
        session = await self.get_session(session_id)

        # Delete session
        result = await self.redis_client.delete(key)

        # Remove from user's session set if applicable
        if session and session.user_id:
            user_key = f"{self.user_sessions_prefix}{session.user_id}"
            await self.redis_client.srem(user_key, session_id)

        return result > 0

    async def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all session IDs for a user"""
        key = f"{self.user_sessions_prefix}{user_id}"
        session_ids = await self.redis_client.smembers(key)
        return list(session_ids) if session_ids else []

    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user"""
        session_ids = await self.get_user_sessions(user_id)

        deleted_count = 0
        for session_id in session_ids:
            if await self.delete_session(session_id):
                deleted_count += 1

        # Delete user's session set
        user_key = f"{self.user_sessions_prefix}{user_id}"
        await self.redis_client.delete(user_key)

        return deleted_count

    async def extend_session_ttl(self, session_id: str) -> bool:
        """Extend the TTL of a session"""
        key = f"{self.session_prefix}{session_id}"
        return await self.redis_client.expire(key, settings.session_ttl)

    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        pattern = f"{self.session_prefix}*"
        cursor = 0
        count = 0

        while True:
            cursor, keys = await self.redis_client.scan(
                cursor, match=pattern, count=100
            )
            count += len(keys)
            if cursor == 0:
                break

        return count

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (Redis handles this automatically with TTL)"""
        # This is a placeholder for any additional cleanup logic
        # Redis automatically removes expired keys
        return 0


# Create a singleton instance
_redis_service: Optional[RedisService] = None


async def get_redis_service() -> RedisService:
    """Get or create Redis service instance"""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
        await _redis_service.connect()
    return _redis_service

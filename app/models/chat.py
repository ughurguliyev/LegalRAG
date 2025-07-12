"""Chat models for request/response handling"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Individual chat message"""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Chat request model"""

    message: str = Field(..., description="User's question in Azerbaijani or English")
    session_id: str = Field(..., description="Unique session identifier")
    stream: bool = Field(default=True, description="Enable streaming response")
    language: str = Field(default="az", description="Response language (az/en)")
    include_sources: bool = Field(default=True, description="Include source references")


class SourceReference(BaseModel):
    """Source reference for a legal document"""

    law_code: str
    law_name_az: str
    law_name_en: str
    article_reference: Optional[str] = None
    relevance_score: float
    content_preview: str = Field(..., max_length=500)


class ChatResponse(BaseModel):
    """Chat response model (for non-streaming)"""

    answer: str
    session_id: str
    sources: List[SourceReference] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time: float = Field(..., description="Processing time in seconds")


class StreamChunk(BaseModel):
    """Streaming response chunk"""

    type: str = Field(..., description="Chunk type: content/sources/error/done")
    content: Optional[str] = None
    sources: Optional[List[SourceReference]] = None
    error: Optional[str] = None
    done: bool = False


class ChatSession(BaseModel):
    """Chat session model for Redis storage"""

    session_id: str
    user_id: Optional[str] = None
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

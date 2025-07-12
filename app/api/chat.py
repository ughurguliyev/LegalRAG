"""Chat API endpoints with streaming support"""

import json
import time
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    StreamChunk,
    SourceReference,
    MessageRole,
)
from app.rag import get_rag_service
from app.services.redis_service import get_redis_service, RedisService
from app.core.config import settings


router = APIRouter(prefix="/chat", tags=["chat"])


async def stream_response(
    question: str,
    session_id: str,
    rag_service,
    redis_service: RedisService,
    include_sources: bool = True,
) -> AsyncGenerator[str, None]:
    """Generate streaming response for chat"""
    try:
        start_time = time.time()

        # Save user message to history
        await redis_service.add_message(
            session_id=session_id, role=MessageRole.USER, content=question
        )

        # Get chat history for context
        messages = await redis_service.get_session_messages(
            session_id=session_id, limit=10
        )

        # Perform RAG search with streaming
        result = rag_service.query_stream(question, k=settings.retrieval_k)

        # Prepare sources
        sources = []
        if include_sources and result.get("sources"):
            for source in result["sources"][:3]:  # Top 3 sources
                sources.append(
                    SourceReference(
                        law_code=source.get("law_code", ""),
                        law_name_az=source.get("law_name", ""),
                        law_name_en=source.get("law_code", ""),
                        article_reference=source.get("article_ref"),
                        relevance_score=source.get("relevance_score", 0),
                        content_preview=source.get("content", "")[:500],
                    )
                )

        # Stream the answer
        full_answer = ""
        if "answer_stream" in result:
            # Stream the LLM response in real-time
            for text_chunk in result["answer_stream"]:
                if text_chunk:
                    full_answer += text_chunk
                    chunk = StreamChunk(type="content", content=text_chunk, done=False)
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    # Small delay for streaming effect
                    await asyncio.sleep(0.01)
        else:
            # Fallback to non-streaming
            answer = result.get("answer", "")
            sentences = answer.split(". ")

            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    # Add period back if not the last sentence
                    if i < len(sentences) - 1:
                        sentence += "."

                    full_answer += sentence + " "
                    chunk = StreamChunk(
                        type="content", content=sentence + " ", done=False
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    await asyncio.sleep(0.05)

        # Send sources if requested
        if sources:
            sources_chunk = StreamChunk(type="sources", sources=sources, done=False)
            yield f"data: {sources_chunk.model_dump_json()}\n\n"

        # Save assistant message to history
        await redis_service.add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=full_answer,
            metadata={
                "sources": [s.model_dump() for s in sources],
                "processing_time": time.time() - start_time,
            },
        )

        # Send completion signal
        done_chunk = StreamChunk(type="done", done=True)
        yield f"data: {done_chunk.model_dump_json()}\n\n"

    except Exception as e:
        error_chunk = StreamChunk(type="error", error=str(e), done=True)
        yield f"data: {error_chunk.model_dump_json()}\n\n"


@router.post("/stream")
async def chat_stream(
    request: ChatRequest, redis_service: RedisService = Depends(get_redis_service)
):
    """Stream chat responses using Server-Sent Events"""
    try:
        # Get RAG service
        rag_service = get_rag_service()

        # Extend session TTL
        await redis_service.extend_session_ttl(request.session_id)

        # Create streaming response
        return EventSourceResponse(
            stream_response(
                question=request.message,
                session_id=request.session_id,
                rag_service=rag_service,
                redis_service=redis_service,
                include_sources=request.include_sources,
            )
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest, redis_service: RedisService = Depends(get_redis_service)
):
    """Non-streaming chat endpoint"""
    try:
        start_time = time.time()

        # Get RAG service
        rag_service = get_rag_service()

        # Save user message
        await redis_service.add_message(
            session_id=request.session_id,
            role=MessageRole.USER,
            content=request.message,
        )

        # Extend session TTL
        await redis_service.extend_session_ttl(request.session_id)

        # Query RAG
        result = rag_service.query(request.message, k=settings.retrieval_k)

        # Prepare sources
        sources = []
        if request.include_sources and result.get("sources"):
            for source in result["sources"][:3]:
                sources.append(
                    SourceReference(
                        law_code=source.get("law_code", ""),
                        law_name_az=source.get("law_name", ""),
                        law_name_en=source.get("law_code", ""),
                        article_reference=source.get("article_ref"),
                        relevance_score=source.get("relevance_score", 0),
                        content_preview=source.get("content", "")[:500],
                    )
                )

        answer = result.get("answer", "")
        processing_time = time.time() - start_time

        # Save assistant message
        await redis_service.add_message(
            session_id=request.session_id,
            role=MessageRole.ASSISTANT,
            content=answer,
            metadata={
                "sources": [s.model_dump() for s in sources],
                "processing_time": processing_time,
            },
        )

        return ChatResponse(
            answer=answer,
            session_id=request.session_id,
            sources=sources,
            processing_time=processing_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    redis_service: RedisService = Depends(get_redis_service),
):
    """Get chat history for a session"""
    try:
        messages = await redis_service.get_session_messages(
            session_id=session_id, limit=limit
        )

        return {
            "session_id": session_id,
            "messages": [msg.model_dump() for msg in messages],
            "count": len(messages),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str, redis_service: RedisService = Depends(get_redis_service)
):
    """Delete a chat session"""
    try:
        success = await redis_service.delete_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": "Session deleted successfully", "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

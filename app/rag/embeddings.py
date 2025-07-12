"""Embeddings module with caching support"""

from typing import List, Optional
from sentence_transformers import SentenceTransformer
import hashlib
import json
import redis
import numpy as np
from app.core.config import settings


class HuggingFaceEmbedding:
    """Custom HuggingFace embedding wrapper with caching support"""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.redis_client = self._init_redis()
        self.cache_enabled = self.redis_client is not None

    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection for caching"""
        try:
            redis_kwargs = {"decode_responses": False}

            if settings.redis_password:
                redis_kwargs["password"] = settings.redis_password
            if settings.redis_db is not None:
                redis_kwargs["db"] = settings.redis_db

            client = redis.Redis.from_url(settings.redis_url, **redis_kwargs)
            client.ping()
            return client
        except Exception:
            return None

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{self.model_name}:{text_hash}"

    def _get_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """Try to get embedding from cache"""
        if not self.cache_enabled:
            return None

        try:
            cached = self.redis_client.get(cache_key)
            return json.loads(cached) if cached else None
        except Exception:
            return None

    def _save_to_cache(self, cache_key: str, embedding: List[float]) -> None:
        """Save embedding to cache"""
        if not self.cache_enabled:
            return

        try:
            self.redis_client.setex(
                cache_key, 86400, json.dumps(embedding)  # 24 hours TTL
            )
        except Exception:
            pass

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        batch_size = 32
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self.model.encode(batch, convert_to_tensor=False)
            embeddings.extend(batch_embeddings.tolist())

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a query text with caching"""
        cache_key = self._get_cache_key(text)

        # Try cache first
        cached_embedding = self._get_from_cache(cache_key)
        if cached_embedding:
            return cached_embedding

        # Generate new embedding
        embedding = self.model.encode([text], convert_to_tensor=False)[0].tolist()

        # Cache for future use
        self._save_to_cache(cache_key, embedding)

        return embedding

"""Embeddings module for multilingual support"""

from typing import List
from sentence_transformers import SentenceTransformer


class HuggingFaceEmbedding:
    """Custom HuggingFace embedding wrapper for multilingual support"""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        self.model_name = model_name
        self.model = None  # Lazy load the model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

        batch_size = 32
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self.model.encode(batch, convert_to_tensor=False)
            embeddings.extend(batch_embeddings.tolist())

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a query text"""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
        return self.model.encode([text], convert_to_tensor=False)[0].tolist()

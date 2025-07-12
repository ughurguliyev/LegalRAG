"""Retriever module for semantic search in legal documents"""

from typing import List
from langchain.schema import Document


class SemanticRetriever:
    """Semantic retriever for legal documents"""

    def __init__(self, collection, embeddings):
        self.collection = collection
        self.embeddings = embeddings

    def search(self, query: str, k: int = 5) -> List[Document]:
        """Perform semantic search"""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Search in vector database
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        # Convert to Document objects
        documents = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            # Add relevance score
            metadata["relevance_score"] = 1 - distance

            documents.append(Document(page_content=doc, metadata=metadata))

        return documents

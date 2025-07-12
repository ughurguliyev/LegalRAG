"""Main RAG service for Azerbaijan Legal System"""

from typing import Dict, Any
import chromadb
import openai

from app.core.config import settings
from app.rag.chunking import LegalChunker
from app.rag.embeddings import HuggingFaceEmbedding
from app.rag.law_mapper import LawCodeMapper
from app.rag.pdf_extractor import PDFExtractor
from app.rag.retriever import SemanticRetriever
from app.rag.llm_generator import LLMGenerator


class AzerbaijanLegalRAG:
    """Complete RAG system for all Azerbaijan Law Codes"""

    def __init__(self):
        # Initialize OpenAI client
        self.llm_client = openai.OpenAI(api_key=settings.openai_api_key)

        # Initialize components
        self.chunker = LegalChunker(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )
        self.law_mapper = LawCodeMapper()
        self.pdf_extractor = PDFExtractor()
        self.llm_generator = LLMGenerator(
            client=self.llm_client,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )

        # Initialize HuggingFace embeddings
        self.embeddings = HuggingFaceEmbedding(settings.embedding_model)

        # Initialize Chroma Cloud client
        self.chroma_client = chromadb.CloudClient(
            tenant=settings.chroma_tenant_id,
            database=settings.chroma_database,
            api_key=settings.chroma_api_key,
        )
        self.collection_name = settings.chroma_collection

        # Initialize collection
        self.collection = None
        self.retriever = None
        self._initialize_collection()

    def _initialize_collection(self):
        """Initialize or get existing collection"""
        try:
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name
            )
            self.setup_retriever()
        except:
            # Collection doesn't exist - this is expected for API usage
            # The collection should be pre-populated
            raise ValueError(
                f"Collection '{self.collection_name}' not found. "
                "Please ensure the vector database is properly initialized."
            )

    def setup_retriever(self):
        """Set up the retriever for semantic search"""
        self.retriever = SemanticRetriever(self.collection, self.embeddings)

    def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """Query the legal system"""
        if not self.retriever:
            raise ValueError("System not initialized. Retriever not available.")

        try:
            # Perform semantic search
            relevant_docs = self.retriever.search(question, k=k)

            # Extract and organize results
            article_references = []
            relevant_contexts = []
            law_codes_found = set()

            for doc in relevant_docs:
                # Extract law code info
                law_code = doc.metadata.get("law_code", "unknown")
                law_name_az = doc.metadata.get("law_name_az", "")
                law_codes_found.add(f"{law_name_az} ({law_code})")

                # Extract article reference
                article_ref = self.llm_generator.extract_article_reference(doc)
                if article_ref:
                    article_references.append(f"{law_name_az} - {article_ref}")

                # Collect context
                relevant_contexts.append(
                    {
                        "content": doc.page_content,
                        "law_code": law_code,
                        "law_name": law_name_az,
                        "article_ref": article_ref,
                        "relevance_score": doc.metadata.get("relevance_score", 0),
                    }
                )

            # Generate answer using LLM
            answer = self.llm_generator.generate_answer(question, relevant_contexts)

            # Create references summary
            unique_refs = list(set(article_references))
            references_summary = (
                f"İstifadə olunan mənbələr: {', '.join(unique_refs)}"
                if unique_refs
                else "Maddə referansları tapılmadı"
            )

            return {
                "question": question,
                "answer": answer,
                "references": references_summary,
                "law_codes": list(law_codes_found),
                "sources": relevant_contexts,
                "total_sources": len(relevant_contexts),
            }

        except Exception as e:
            return {
                "question": question,
                "answer": f"Sorğu zamanı xəta baş verdi: {str(e)}",
                "references": "",
                "law_codes": [],
                "sources": [],
                "total_sources": 0,
                "error": str(e),
            }


# Create a singleton instance
_rag_instance = None


def get_rag_service() -> AzerbaijanLegalRAG:
    """Get or create RAG service instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = AzerbaijanLegalRAG()
    return _rag_instance

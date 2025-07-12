"""Data models for the RAG system"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LegalChunk:
    """Represents a hierarchical legal text chunk"""

    content: str
    law_code: str
    chapter: Optional[str] = None  # Fəsil
    article: Optional[str] = None  # Maddə
    sub_article: Optional[str] = None  # e.g., 127.1, 127.1.1
    section: Optional[str] = None  # Bölüm
    chunk_type: str = "content"  # "chapter", "article", "section", "content"
    is_valid: bool = True  # False if text is crossed out/invalidated
    metadata: Dict[str, Any] = field(default_factory=dict)

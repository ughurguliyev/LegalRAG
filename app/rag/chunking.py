"""Legal document chunking with hierarchical structure preservation"""

import re
from typing import List, Dict, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.rag.models import LegalChunk
from app.rag.text_processing import TextNormalizer
from app.rag.law_mapper import LawCodeMapper


class LegalChunker:
    """Enhanced hierarchical chunker for all Azerbaijani legal documents"""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            length_function=len,
        )
        self.normalizer = TextNormalizer()

    def extract_legal_structure(self, text: str, law_code: str) -> List[LegalChunk]:
        """Extract hierarchical legal structure from text"""
        chunks = []

        # Patterns for legal structure
        chapter_patterns = [  # Fəsil
            r"(F[əƏ]s[iİ]l\s+[IVXLCDM]+)",
            r"(F[əƏ]s[iİ]l\s+\d+)",
            r"(FASIL\s+[IVXLCDM]+)",
            r"(FASIL\s+\d+)",
            r"(\d+\s*[-–—]\s*c[iüıə]\s+f[əƏ]s[iİ]l)",
        ]

        section_patterns = [  # Bölüm, Hissə
            r"(B[öÖ]l[üÜ]m\s+[IVXLCDM]+)",
            r"(B[öÖ]l[üÜ]m\s+\d+)",
            r"(BÖLÜM\s+[IVXLCDM]+)",
            r"(BÖLÜM\s+\d+)",
            r"(H[iİ]ss[əƏ]\s+[IVXLCDM]+)",
            r"(H[iİ]ss[əƏ]\s+\d+)",
            r"(HİSSƏ\s+[IVXLCDM]+)",
            r"(HİSSƏ\s+\d+)",
        ]

        article_patterns = [  # Maddə
            r"(M[aA]dd[əeE]\s+(\d+(?:\.\d+)*))",
            r"(MADDƏ\s+(\d+(?:\.\d+)*))",
            r"((\d+(?:\.\d+)*)\s*[-–—]\s*c[iüıə]\s+m[aA]dd[əeE])",
            r"((\d+(?:\.\d+)*)\.\s*[A-ZÇƏĞIƏÖŞÜ])",
            r"((\d+(?:\.\d+)*)\)\s*[A-ZÇƏĞIƏÖŞÜ])",
            r"(B[əeE]nd\s+(\d+(?:\.\d+)*))",
            r"(BƏND\s+(\d+(?:\.\d+)*))",
        ]

        # Normalize text first
        text, _ = self.normalizer.normalize_text(text)

        # Find all structural elements
        all_patterns = chapter_patterns + section_patterns + article_patterns
        split_positions = []

        for pattern in all_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                split_positions.append(match.start())

        split_positions = sorted(list(set(split_positions)))

        # Split text at structural positions
        if len(split_positions) > 1:
            sections = []
            for i in range(len(split_positions)):
                start = split_positions[i]
                end = (
                    split_positions[i + 1]
                    if i + 1 < len(split_positions)
                    else len(text)
                )
                section = text[start:end].strip()
                if section and len(section) > 20:
                    sections.append(section)
        else:
            # Fallback splitting
            sections = self._fallback_split(text)

        # Process sections
        current_chapter = None
        current_section = None
        current_article = None
        content_buffer = []

        for section_text in sections:
            section_text = section_text.strip()
            if not section_text or len(section_text) < 20:
                continue

            # Normalize and check validity
            section_text, is_valid = self.normalizer.normalize_text(section_text)

            # Skip invalid sections (crossed out text)
            if not is_valid:
                continue

            # Check for chapter (Fəsil)
            chapter_match = self._match_patterns(section_text, chapter_patterns)
            if chapter_match:
                # Process accumulated content
                if content_buffer:
                    self._process_content_buffer(
                        chunks,
                        content_buffer,
                        law_code,
                        current_chapter,
                        current_section,
                        current_article,
                    )
                    content_buffer = []

                current_chapter = chapter_match
                current_article = None

                chunks.append(
                    LegalChunk(
                        content=section_text,
                        law_code=law_code,
                        chapter=current_chapter,
                        section=current_section,
                        chunk_type="chapter",
                        is_valid=is_valid,
                        metadata=self._create_metadata(
                            "chapter", law_code, current_chapter, current_section
                        ),
                    )
                )
                continue

            # Check for section (Bölüm/Hissə)
            section_match = self._match_patterns(section_text, section_patterns)
            if section_match:
                if content_buffer:
                    self._process_content_buffer(
                        chunks,
                        content_buffer,
                        law_code,
                        current_chapter,
                        current_section,
                        current_article,
                    )
                    content_buffer = []

                current_section = section_match
                current_article = None

                chunks.append(
                    LegalChunk(
                        content=section_text,
                        law_code=law_code,
                        chapter=current_chapter,
                        section=current_section,
                        chunk_type="section",
                        is_valid=is_valid,
                        metadata=self._create_metadata(
                            "section", law_code, current_chapter, current_section
                        ),
                    )
                )
                continue

            # Check for article (Maddə)
            article_match = self._match_patterns(section_text, article_patterns)
            if article_match:
                if content_buffer:
                    self._process_content_buffer(
                        chunks,
                        content_buffer,
                        law_code,
                        current_chapter,
                        current_section,
                        current_article,
                    )
                    content_buffer = []

                current_article = article_match

                # Extract article number
                article_num = self._extract_article_number(article_match)

                chunks.append(
                    LegalChunk(
                        content=section_text,
                        law_code=law_code,
                        chapter=current_chapter,
                        section=current_section,
                        article=current_article,
                        sub_article=article_num,
                        chunk_type="article",
                        is_valid=is_valid,
                        metadata=self._create_metadata(
                            "article",
                            law_code,
                            current_chapter,
                            current_section,
                            current_article,
                            article_num,
                        ),
                    )
                )
                continue

            # Regular content
            content_buffer.append(section_text)

        # Process remaining content
        if content_buffer:
            self._process_content_buffer(
                chunks,
                content_buffer,
                law_code,
                current_chapter,
                current_section,
                current_article,
            )

        # Filter out invalid chunks
        valid_chunks = [chunk for chunk in chunks if chunk.is_valid]
        return valid_chunks

    def _fallback_split(self, text: str) -> List[str]:
        """Fallback splitting strategy"""
        sections = re.split(r"\n\s*\n", text)
        if len(sections) < 5:
            sections = re.split(r"\n", text)
        if len(sections) < 5:
            # Force split into chunks
            sections = []
            for i in range(0, len(text), self.chunk_size):
                chunk = text[i : i + self.chunk_size]
                if chunk.strip():
                    sections.append(chunk)
        return sections

    def _match_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """Match text against patterns and return first match"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_article_number(self, article_text: str) -> Optional[str]:
        """Extract article number from text"""
        # Try different patterns to extract article number
        patterns = [
            r"(\d+(?:\.\d+)*)",  # 127.1.1
            r"Maddə\s+(\d+(?:\.\d+)*)",
            r"(\d+(?:\.\d+)*)\s*[-–—]\s*c[iüıə]\s+maddə",
        ]

        for pattern in patterns:
            match = re.search(pattern, article_text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _process_content_buffer(
        self,
        chunks: List[LegalChunk],
        content_buffer: List[str],
        law_code: str,
        chapter: str,
        section: str,
        article: str,
    ):
        """Process accumulated content buffer"""
        if not content_buffer:
            return

        content_text = "\n".join(content_buffer)
        content_text, is_valid = self.normalizer.normalize_text(content_text)

        if not is_valid or len(content_text) < 50:
            return

        # Split long content
        if len(content_text) > self.chunk_size:
            sub_chunks = self.text_splitter.split_text(content_text)
            for sub_chunk in sub_chunks:
                sub_chunk, sub_is_valid = self.normalizer.normalize_text(sub_chunk)
                if sub_is_valid and len(sub_chunk) > 50:
                    chunks.append(
                        LegalChunk(
                            content=sub_chunk,
                            law_code=law_code,
                            chapter=chapter,
                            section=section,
                            article=article,
                            chunk_type="content",
                            is_valid=sub_is_valid,
                            metadata=self._create_metadata(
                                "content", law_code, chapter, section, article
                            ),
                        )
                    )
        else:
            chunks.append(
                LegalChunk(
                    content=content_text,
                    law_code=law_code,
                    chapter=chapter,
                    section=section,
                    article=article,
                    chunk_type="content",
                    is_valid=is_valid,
                    metadata=self._create_metadata(
                        "content", law_code, chapter, section, article
                    ),
                )
            )

    def _create_metadata(
        self,
        chunk_type: str,
        law_code: str,
        chapter: str = None,
        section: str = None,
        article: str = None,
        article_num: str = None,
    ) -> Dict[str, str]:
        """Create metadata dict with no None values for ChromaDB"""
        # Get law info - law_code is already just the code, not filename
        law_info = {"code": law_code, "name_az": "Unknown", "name_en": "Unknown"}

        # Find matching law info
        for filename, info in LawCodeMapper.LAW_CODES.items():
            if info["code"] == law_code:
                law_info = info
                break

        metadata = {
            "law_code": law_code,
            "law_name_az": law_info["name_az"],
            "law_name_en": law_info["name_en"],
            "chunk_type": chunk_type,
        }

        # Only add non-None values
        if chapter:
            metadata["chapter"] = str(chapter)
            metadata["chapter_context"] = str(chapter)

        if section:
            metadata["section"] = str(section)
            metadata["section_context"] = str(section)

        if article:
            metadata["article"] = str(article)
            metadata["article_context"] = str(article)

        if article_num:
            metadata["article_number"] = str(article_num)
            metadata["article_reference"] = f"Maddə {article_num}"

        return metadata

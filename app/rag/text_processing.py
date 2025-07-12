"""Text processing utilities for legal documents"""

import re
from typing import Tuple


class TextNormalizer:
    """Handles text normalization and invalid text detection"""

    @staticmethod
    def fix_spaced_text(text: str) -> str:
        """Fix spaced text like 'M a d d ə' to 'Maddə'"""
        patterns = [
            (r"M\s+a\s+d\s+d\s+ə", "Maddə"),
            (r"M\s+A\s+D\s+D\s+Ə", "MADDƏ"),
            (r"F\s+ə\s+s\s+i\s+l", "Fəsil"),
            (r"F\s+Ə\s+S\s+İ\s+L", "FƏSİL"),
            (r"B\s+ə\s+n\s+d", "Bənd"),
            (r"B\s+Ə\s+N\s+D", "BƏND"),
            (r"H\s+i\s+s\s+s\s+ə", "Hissə"),
            (r"H\s+İ\s+S\s+S\s+Ə", "HİSSƏ"),
            (r"B\s+ö\s+l\s+ü\s+m", "Bölüm"),
            (r"B\s+Ö\s+L\s+Ü\s+M", "BÖLÜM"),
        ]

        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    @staticmethod
    def detect_invalidated_text(text: str) -> Tuple[str, bool]:
        """
        Detect and handle invalidated (crossed out) text
        Returns: (clean_text, is_valid)
        """
        # Patterns that indicate invalidated/crossed out text
        invalidation_patterns = [
            # Unicode strikethrough characters
            r"[\u0336\u0337\u0338\u0353\u0354\u0488\u0489]",
            # Common strikethrough representations
            r"~~[^~]+~~",
            r"--[^-]+--",
            r"<strike>.*?</strike>",
            r"<s>.*?</s>",
            r"<del>.*?</del>",
            # Azerbaijani invalidation markers
            r"\[ləğv edilib\]",
            r"\[mətn ləğv edilib\]",
            r"\(ləğv edilib\)",
            r"qüvvədən düşüb",
            r"qüvvədən düşmüşdür",
            r"qüvvədən çıxarılıb",
            r"ləğv olunub",
            # Line-through patterns (common in PDFs)
            r"[─━═]+",  # Horizontal lines through text
        ]

        # Check if text contains invalidation markers
        is_valid = True
        for pattern in invalidation_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                is_valid = False
                break

        # Additional check for specific article invalidations
        # e.g., "17.2.3" mentioned as having line through it
        if re.search(r"17\.2\.3", text) and any(char in text for char in "─━═"):
            is_valid = False

        # Clean the text (remove strikethrough characters)
        clean_text = text
        for pattern in invalidation_patterns:
            clean_text = re.sub(
                pattern, "", clean_text, flags=re.IGNORECASE | re.UNICODE
            )

        # Remove any remaining strikethrough Unicode characters
        clean_text = "".join(
            char for char in clean_text if ord(char) not in range(0x0336, 0x0338)
        )

        return clean_text.strip(), is_valid

    @staticmethod
    def normalize_text(text: str) -> Tuple[str, bool]:
        """Complete text normalization"""
        # Fix spaced text
        text = TextNormalizer.fix_spaced_text(text)

        # Detect and handle invalidated text
        text, is_valid = TextNormalizer.detect_invalidated_text(text)

        # General cleanup
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n+", "\n", text)
        text = text.strip()

        return text, is_valid

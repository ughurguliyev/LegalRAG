"""PDF text extraction utilities"""

from pathlib import Path
import pdfplumber
import PyPDF2


class PDFExtractor:
    """Extract text from PDF files using multiple methods"""

    @staticmethod
    def extract_text(pdf_path: Path) -> str:
        """Extract text from PDF with multiple fallback methods"""
        text = ""

        # Try pdfplumber first (better for complex layouts)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            if text and len(text) > 1000:
                return text
        except Exception:
            pass

        # Fallback to PyPDF2
        try:
            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            if text and len(text) > 1000:
                return text
        except Exception:
            pass

        return text

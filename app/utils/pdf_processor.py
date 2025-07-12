"""PDF Processing Utility for Azerbaijan Legal Documents

This module provides functionality to extract text from PDF files and
populate the Chroma vector database with legal document chunks.
"""

from pathlib import Path
from typing import List
import chromadb
from langchain.schema import Document

from app.core.config import settings
from app.rag.pdf_extractor import PDFExtractor
from app.rag.law_mapper import LawCodeMapper
from app.rag.chunking import LegalChunker
from app.rag.embeddings import HuggingFaceEmbedding


class PDFProcessor:
    """Process PDF files and populate vector database"""

    def __init__(self, pdf_directory: str = "pdfs"):
        self.pdf_directory = Path(pdf_directory)
        self.pdf_extractor = PDFExtractor()
        self.law_mapper = LawCodeMapper()
        self.chunker = LegalChunker(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )
        self.embeddings = HuggingFaceEmbedding(settings.embedding_model)

        # Initialize Chroma client
        self.chroma_client = chromadb.CloudClient(
            tenant=settings.chroma_tenant_id,
            database=settings.chroma_database,
            api_key=settings.chroma_api_key,
        )
        self.collection_name = settings.chroma_collection

    def get_pdf_files(self) -> List[Path]:
        """Get all PDF files from the directory"""
        if not self.pdf_directory.exists():
            raise ValueError(f"PDF directory not found: {self.pdf_directory}")

        pdf_files = list(self.pdf_directory.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files in {self.pdf_directory}")
        return pdf_files

    def process_single_pdf(self, pdf_path: Path) -> List[Document]:
        """Process a single PDF file and return documents"""
        print(f"\n📄 Processing {pdf_path.name}...")

        # Get law info
        law_info = self.law_mapper.get_law_info(pdf_path.name)
        law_code = law_info["code"]
        law_name_az = law_info["name_az"]
        law_name_en = law_info["name_en"]

        print(f"   📋 Law Code: {law_name_az} ({law_name_en})")

        # Extract text
        text = self.pdf_extractor.extract_text(pdf_path)
        if not text or len(text) < 1000:
            print(f"   ❌ Insufficient text extracted from {pdf_path.name}")
            return []

        print(f"   ✅ Extracted {len(text)} characters")

        # Create hierarchical chunks
        legal_chunks = self.chunker.extract_legal_structure(text, law_code)
        print(f"   📊 Created {len(legal_chunks)} chunks")

        # Convert to LangChain Documents
        documents = []
        for chunk in legal_chunks:
            # Ensure all metadata values are strings
            metadata = chunk.metadata.copy()
            metadata["source"] = str(pdf_path)
            metadata["is_valid"] = str(chunk.is_valid)

            doc = Document(page_content=chunk.content, metadata=metadata)
            documents.append(doc)

        return documents

    def process_all_pdfs(self) -> List[Document]:
        """Process all PDF files and return documents"""
        print("🚀 Processing all Azerbaijan law codes...")

        all_documents = []
        pdf_files = self.get_pdf_files()

        for pdf_path in pdf_files:
            try:
                documents = self.process_single_pdf(pdf_path)
                all_documents.extend(documents)
            except Exception as e:
                print(f"   ❌ Error processing {pdf_path.name}: {str(e)}")
                continue

        print(f"\n✅ Total documents created: {len(all_documents)}")
        return all_documents

    def populate_vector_store(self, documents: List[Document], recreate: bool = False):
        """Populate Chroma vector store with documents"""
        print(f"\n🔧 Setting up vector store...")

        try:
            if recreate:
                # Delete existing collection if recreate is True
                try:
                    self.chroma_client.delete_collection(name=self.collection_name)
                    print("   🗑️  Deleted existing collection")
                except:
                    pass

            # Create or get collection
            try:
                collection = self.chroma_client.get_collection(
                    name=self.collection_name
                )
                print(f"   ✅ Using existing collection: {self.collection_name}")
            except:
                collection = self.chroma_client.create_collection(
                    name=self.collection_name, metadata={"hnsw:space": "cosine"}
                )
                print(f"   ✅ Created new collection: {self.collection_name}")

            # Add documents in batches
            batch_size = 50
            total_batches = (len(documents) - 1) // batch_size + 1

            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                batch_num = i // batch_size + 1
                print(f"   📥 Processing batch {batch_num}/{total_batches}")

                # Extract texts and metadata
                texts = [doc.page_content for doc in batch]
                metadatas = [doc.metadata for doc in batch]

                # Generate embeddings
                embeddings = self.embeddings.embed_documents(texts)

                # Generate IDs
                ids = [f"doc_{i}_{j}" for j in range(len(batch))]

                # Add to collection
                collection.add(
                    documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids
                )

            print(f"✅ Vector store populated with {len(documents)} documents")

        except Exception as e:
            print(f"❌ Error populating vector store: {str(e)}")
            raise

    def run(self, recreate: bool = False):
        """Main method to process PDFs and populate vector store"""
        print("🇦🇿 Azerbaijan Legal RAG - PDF Processing Utility")
        print("=" * 60)

        # Process all PDFs
        documents = self.process_all_pdfs()

        if not documents:
            print("❌ No documents were processed. Check PDF files.")
            return

        # Populate vector store
        self.populate_vector_store(documents, recreate=recreate)

        print("\n🎉 PDF processing completed successfully!")
        print(f"   📚 Total documents in database: {len(documents)}")


def main():
    """Command-line interface for PDF processing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process Azerbaijan legal PDFs and populate vector database"
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="pdfs",
        help="Directory containing PDF files (default: pdfs)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the vector database (delete existing data)",
    )

    args = parser.parse_args()

    # Check environment variables
    if not settings.openai_api_key:
        print("❌ OPENAI_API_KEY is not set")
        return

    if not settings.chroma_api_key:
        print("❌ CHROMA_API_KEY is not set")
        return

    # Run processor
    processor = PDFProcessor(pdf_directory=args.pdf_dir)
    processor.run(recreate=args.recreate)


if __name__ == "__main__":
    main()

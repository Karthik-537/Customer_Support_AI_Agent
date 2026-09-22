"""Ingestion script for loading documents into Qdrant.

This script can be run with: python -m app.rag.ingest
"""

import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.rag.chunker import chunk_documents
from app.rag.embeddings import embed_documents, get_embedding_dimension
from app.rag.loader import load_pdf_directory
from app.rag.qdrant_store import COLLECTION_NAME, create_collection, get_collection_info, upload_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("RAG Knowledge Base Ingestion")
    print("=" * 60)
    print()

    # Step 1: Load PDFs
    print("Step 1: Loading PDF documents...")
    try:
        documents = load_pdf_directory(KNOWLEDGE_BASE_DIR)
        print(f"Loaded {len(documents)} pages from PDFs")
        print()
    except Exception as e:
        print(f"Error loading PDFs: {e}")
        return False

    # Step 2: Chunk documents
    print("Step 2: Chunking documents...")
    chunks = chunk_documents(documents, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    print(f"Created {len(chunks)} chunks")
    print(f"Chunk size: {CHUNK_SIZE} characters")
    print(f"Chunk overlap: {CHUNK_OVERLAP} characters")
    print()

    # Step 3: Generate embeddings
    print("Step 3: Generating embeddings...")
    print(f"Using model: {EMBEDDING_MODEL}")

    try:
        embedding_dim = get_embedding_dimension(EMBEDDING_MODEL)
        print(f"Embedding dimension: {embedding_dim}")

        texts = [chunk["text"] for chunk in chunks]
        embeddings = embed_documents(texts, EMBEDDING_MODEL)
        print(f"Generated {len(embeddings)} embeddings")
        print()
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return False

    # Step 4: Create/update Qdrant collection
    print("Step 4: Setting up Qdrant collection...")
    try:
        create_collection(
            collection_name=COLLECTION_NAME,
            vector_size=embedding_dim,
            recreate=False  # Set to True to force recreation
        )
        print(f"Collection '{COLLECTION_NAME}' ready")
        print()
    except Exception as e:
        print(f"Error setting up Qdrant collection: {e}")
        return False

    # Step 5: Upload chunks
    print("Step 5: Uploading chunks to Qdrant...")
    try:
        uploaded_count = upload_chunks(chunks, embeddings, COLLECTION_NAME)
        print(f"Uploaded {uploaded_count} chunks to Qdrant")
        print()
    except Exception as e:
        print(f"Error uploading chunks: {e}")
        return False

    # Step 6: Verify
    print("Step 6: Verifying collection...")
    try:
        collection_info = get_collection_info(COLLECTION_NAME)
        if "error" not in collection_info:
            print(f"Collection info:")
            print(f"  Name: {collection_info['name']}")
            print(f"  Points count: {collection_info['points_count']}")
            print(f"  Vectors count: {collection_info['vectors_count']}")
            print()
        else:
            print(f"Error getting collection info: {collection_info['error']}")
    except Exception as e:
        print(f"Error verifying collection: {e}")

    print("=" * 60)
    print("Ingestion completed successfully!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

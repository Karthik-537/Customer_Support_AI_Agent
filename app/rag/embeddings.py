"""Local embedding generation with Sentence Transformers.

This module converts text chunks into vectors for Qdrant using a local model.
"""

import logging
from typing import List, Optional

from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instance to avoid reloading
_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """Get or create the embedding model instance.

    Uses a lightweight model suitable for local execution.
    all-MiniLM-L6-v2 is a good balance of speed and quality (384 dimensions).

    Args:
        model_name: Name of the Sentence Transformers model to use.

    Returns:
        SentenceTransformer model instance.
    """
    global _embedding_model

    if _embedding_model is None:
        logger.info(f"Loading embedding model: {model_name}")
        _embedding_model = SentenceTransformer(model_name)
        logger.info(f"Model loaded. Embedding dimension: {_embedding_model.get_embedding_dimension()}")

    return _embedding_model


def embed_text(text: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    """Generate embedding for a single text.

    Args:
        text: The text to embed.
        model_name: Name of the Sentence Transformers model to use.

    Returns:
        List of float values representing the embedding vector.
    """
    model = get_embedding_model(model_name)
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_documents(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> List[List[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed.
        model_name: Name of the Sentence Transformers model to use.

    Returns:
        List of embedding vectors (each is a list of floats).
    """
    model = get_embedding_model(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    return embeddings.tolist()


def get_embedding_dimension(model_name: str = "all-MiniLM-L6-v2") -> int:
    """Get the dimension of the embedding vectors.

    Args:
        model_name: Name of the Sentence Transformers model to use.

    Returns:
        The dimension of the embedding vectors.
    """
    model = get_embedding_model(model_name)
    return model.get_embedding_dimension()


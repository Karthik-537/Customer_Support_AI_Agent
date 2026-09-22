"""Knowledge-base document loader.

This module parses company documents including PDFs using PyMuPDF.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import pymupdf  # PyMuPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Clean extracted text by removing excessive whitespace and formatting issues.

    Args:
        text: Raw text extracted from PDF.

    Returns:
        Cleaned text with normalized whitespace and line breaks.
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = " ".join(text.split())

    # Remove multiple consecutive newlines (but keep single newlines for paragraph structure)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:  # Keep non-empty lines
            cleaned_lines.append(stripped)

    # Join with single spaces for more natural text flow
    cleaned_text = " ".join(cleaned_lines)

    return cleaned_text


def load_pdf(file_path: str | Path) -> List[Dict[str, Any]]:
    """Load and extract text from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of dictionaries containing extracted text with metadata:
        [
            {
                "text": str,
                "page": int,
                "source": str
            }
        ]

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        Exception: For other PDF processing errors.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if not file_path.suffix.lower() == ".pdf":
        raise ValueError(f"File is not a PDF: {file_path}")

    logger.info(f"Loading PDF: {file_path}")

    try:
        doc = pymupdf.open(file_path)
        pages_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            if text.strip():  # Only add pages with content
                cleaned_text = clean_text(text)
                pages_data.append({
                    "text": cleaned_text,
                    "page": page_num + 1,  # 1-based page numbering
                    "source": file_path.name
                })

        doc.close()

        logger.info(f"Extracted {len(pages_data)} pages from {file_path.name}")
        return pages_data

    except Exception as e:
        logger.error(f"Error loading PDF {file_path}: {e}")
        raise


def load_pdf_directory(directory_path: str | Path) -> List[Dict[str, Any]]:
    """Load all PDF files from a directory.

    Args:
        directory_path: Path to the directory containing PDF files.

    Returns:
        List of dictionaries containing extracted text from all PDFs.
    """
    directory_path = Path(directory_path)

    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    if not directory_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")

    pdf_files = list(directory_path.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {directory_path}")

    all_pages_data = []

    for pdf_file in pdf_files:
        try:
            pages_data = load_pdf(pdf_file)
            all_pages_data.extend(pages_data)
        except Exception as e:
            logger.warning(f"Failed to load {pdf_file.name}: {e}")
            continue

    logger.info(f"Total pages extracted from all PDFs: {len(all_pages_data)}")
    return all_pages_data

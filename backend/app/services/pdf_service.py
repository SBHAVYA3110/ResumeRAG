"""
PDF Extraction Service.
Safely extracts text and page-level metadata from PDF documents using PyPDF.
"""

import io
import re
from pathlib import Path
from typing import BinaryIO, Union

import pypdf
from pypdf.errors import PdfReadError

from backend.app.models.document import (
    EmptyPDFError,
    EncryptedPDFError,
    ExtractedDocument,
    ExtractedPage,
    PDFExtractionError,
)


def clean_extracted_text(text: str) -> str:
    """
    Cleans raw text extracted from a PDF.
    
    Operations:
    1. Removes non-printable control characters (while keeping newlines and tabs).
    2. Strips whitespace at the ends of individual lines.
    3. Collapses 3 or more consecutive newlines into standard double newlines (paragraphs).
    """
    if not text:
        return ""

    # Normalize line breaks to standard \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove non-printable control characters except \n and \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Strip trailing whitespace on each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse multiple consecutive empty lines (3+ newlines -> 2 newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_text_from_pdf(
    source: Union[str, Path, BinaryIO, bytes],
    filename: str = "document.pdf",
) -> ExtractedDocument:
    """
    Extracts text page-by-page from a PDF file or binary stream.
    
    Args:
        source: File path (str or Path), in-memory binary stream (BinaryIO),
                or raw bytes.
        filename: Optional display name for the document (useful for web uploads).
        
    Returns:
        ExtractedDocument: Structured object with total page count and individual pages.
        
    Raises:
        FileNotFoundError: If a file path is provided but does not exist.
        EncryptedPDFError: If the PDF is password protected.
        EmptyPDFError: If the PDF has no readable text across all pages.
        PDFExtractionError: For corrupt or unreadable PDF streams.
    """
    stream = None
    should_close = False

    try:
        # Step 1: Normalize source into a readable binary stream
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"PDF file not found at: {path}")
            stream = open(path, "rb")
            should_close = True
            filename = filename if filename != "document.pdf" else path.name
        elif isinstance(source, bytes):
            stream = io.BytesIO(source)
        elif hasattr(source, "read"):
            stream = source
        else:
            raise PDFExtractionError(f"Unsupported PDF source type: {type(source)}")

        # Step 2: Initialize PyPDF Reader
        try:
            reader = pypdf.PdfReader(stream)
        except PdfReadError as e:
            raise PDFExtractionError(f"Corrupt or invalid PDF format: {str(e)}") from e
        except Exception as e:
            raise PDFExtractionError(f"Failed to parse PDF: {str(e)}") from e

        # Step 3: Handle Password Protection
        if reader.is_encrypted:
            # Try decrypting with empty password in case of blank/default encryption
            try:
                decrypted = reader.decrypt("")
                if decrypted == 0:  # 0 indicates decryption failed
                    raise EncryptedPDFError(
                        f"The PDF '{filename}' is password-protected and cannot be read."
                    )
            except Exception as e:
                raise EncryptedPDFError(
                    f"The PDF '{filename}' is password-protected and cannot be read."
                ) from e

        # Step 4: Extract text page by page
        total_pages = len(reader.pages)
        if total_pages == 0:
            raise EmptyPDFError(f"The PDF '{filename}' contains 0 pages.")

        extracted_pages: list[ExtractedPage] = []
        has_any_text = False

        for index, page in enumerate(reader.pages):
            page_number = index + 1  # 1-indexed for human readability
            raw_text = page.extract_text() or ""
            cleaned = clean_extracted_text(raw_text)

            if cleaned:
                has_any_text = True

            extracted_pages.append(
                ExtractedPage(
                    page_number=page_number,
                    text=cleaned,
                    char_count=len(cleaned),
                )
            )

        # Step 5: Verify if document has extractable text
        if not has_any_text:
            raise EmptyPDFError(
                f"The PDF '{filename}' contains no extractable text. "
                "It may be a scanned image or empty document."
            )

        return ExtractedDocument(
            filename=filename,
            total_pages=total_pages,
            pages=extracted_pages,
        )

    finally:
        # Always close the file handle if we opened it ourselves
        if should_close and stream is not None:
            stream.close()

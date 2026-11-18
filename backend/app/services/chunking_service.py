"""
Text Chunking Service.
Splits extracted document text into semantically coherent chunks with configurable size and overlap.
"""

from typing import List, Optional

from backend.app.models.chunk import ChunkedDocument, TextChunk
from backend.app.models.document import ExtractedDocument, ExtractedPage


# Default standard separators for recursive character splitting
DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def recursive_split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """
    Recursively splits text into chunks no larger than chunk_size,
    attempting to split along natural semantic boundaries (paragraphs, lines, sentences, words).
    
    Args:
        text: Input string to chunk.
        chunk_size: Maximum character length for each chunk.
        chunk_overlap: Number of characters to overlap between adjacent chunks.
        separators: Priority list of separators to try.
        
    Returns:
        List of text chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be strictly less than chunk_size.")

    if separators is None:
        separators = DEFAULT_SEPARATORS

    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    # Step 1: Find the most significant separator that exists in the text
    chosen_sep = ""
    next_separators: List[str] = []
    for index, sep in enumerate(separators):
        if sep == "":
            chosen_sep = ""
            next_separators = []
            break
        if sep in text:
            chosen_sep = sep
            next_separators = separators[index + 1 :]
            break

    # Step 2: Split text by chosen separator
    if chosen_sep:
        raw_splits = text.split(chosen_sep)
    else:
        # Fallback: character-level split
        raw_splits = list(text)

    # Step 3: Check each piece. If a piece exceeds chunk_size, recursively subdivide it
    splits: List[str] = []
    for piece in raw_splits:
        piece_clean = piece.strip()
        if not piece_clean:
            continue
        if len(piece_clean) > chunk_size and next_separators:
            sub_splits = recursive_split_text(
                piece_clean,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=next_separators,
            )
            splits.extend(sub_splits)
        else:
            splits.append(piece_clean)

    # Step 4: Merge splits into chunks respecting chunk_size and chunk_overlap
    return _merge_splits_with_overlap(
        splits=splits,
        separator=chosen_sep,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def _merge_splits_with_overlap(
    splits: List[str],
    separator: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    """
    Combines small text pieces into chunks up to chunk_size,
    retaining trailing pieces to maintain chunk_overlap between successive chunks.
    """
    chunks: List[str] = []
    current_doc: List[str] = []
    total = 0
    sep_len = len(separator)

    for piece in splits:
        piece_len = len(piece)
        extra_len = sep_len if len(current_doc) > 0 else 0

        # If adding this piece exceeds chunk_size, emit the current chunk
        if total + piece_len + extra_len > chunk_size:
            if total > 0:
                doc_text = separator.join(current_doc).strip()
                if doc_text:
                    chunks.append(doc_text)

                # Shrink current_doc from the front until remaining text fits overlap
                # and room is made for the new piece
                while total > chunk_overlap or (
                    total + piece_len + (sep_len if len(current_doc) > 0 else 0) > chunk_size
                    and total > 0
                ):
                    first_item_len = len(current_doc[0]) + (sep_len if len(current_doc) > 1 else 0)
                    total -= first_item_len
                    current_doc = current_doc[1:]

        current_doc.append(piece)
        total += piece_len + (sep_len if len(current_doc) > 1 else 0)

    # Emit the final remaining chunk
    if current_doc:
        doc_text = separator.join(current_doc).strip()
        if doc_text:
            chunks.append(doc_text)

    return chunks


def chunk_page(
    page: ExtractedPage,
    source_doc: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> List[TextChunk]:
    """
    Chunks a single ExtractedPage into TextChunk objects carrying page-level metadata.
    """
    raw_chunks = recursive_split_text(
        text=page.text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: List[TextChunk] = []
    for idx, chunk_text in enumerate(raw_chunks):
        chunk_id = f"{source_doc}_p{page.page_number}_c{idx}"
        chunks.append(
            TextChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                source_doc=source_doc,
                page_number=page.page_number,
                chunk_index=idx,
                char_count=len(chunk_text),
            )
        )

    return chunks


def chunk_document(
    document: ExtractedDocument,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> ChunkedDocument:
    """
    Chunks an entire ExtractedDocument across all pages,
    preserving exact page numbers and generating unique deterministic IDs.
    """
    all_chunks: List[TextChunk] = []

    for page in document.pages:
        page_chunks = chunk_page(
            page=page,
            source_doc=document.filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(page_chunks)

    return ChunkedDocument(
        filename=document.filename,
        total_chunks=len(all_chunks),
        chunks=all_chunks,
    )

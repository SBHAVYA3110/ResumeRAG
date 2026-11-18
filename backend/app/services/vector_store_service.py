"""
Vector Store Service.
Manages ChromaDB collections, vector storage, and semantic retrieval for resume and job chunks.
"""

from typing import Any, Dict, List, Optional
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from backend.app.core.config import get_settings
from backend.app.models.chunk import ChunkedDocument, SearchResult, TextChunk
from backend.app.services.embedding_service import EmbeddingService, get_embedding_service


class VectorStoreService:
    """
    Service for storing and retrieving document chunk vectors using ChromaDB.
    Supports persistent disk storage for application runtime and ephemeral in-memory
    clients for isolated testing.
    """

    def __init__(
        self,
        client: Optional[ClientAPI] = None,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        settings = get_settings()
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        self.embedding_service = embedding_service or get_embedding_service()

        # Step 1: Initialize ChromaDB Client
        if client is not None:
            self._client = client
        else:
            # Production: Persist vectors to disk in the configured directory
            self._client = chromadb.PersistentClient(path=self.persist_directory)

        # Step 2: Initialize Collection with Cosine Similarity space
        # 'hnsw:space': 'cosine' instructs ChromaDB to use cosine distance:
        # distance = 1 - cosine_similarity
        self._collection: Collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self) -> Collection:
        """Direct access to the underlying ChromaDB Collection."""
        return self._collection

    def add_chunks(self, chunks: List[TextChunk]) -> int:
        """
        Stores a list of TextChunk objects in ChromaDB.
        Generates 768-dim embeddings in batch and uses upsert to ensure idempotency.
        
        Returns:
            int: The number of chunks successfully stored.
        """
        if not chunks:
            return 0

        ids: List[str] = [c.chunk_id for c in chunks]
        documents: List[str] = [c.text for c in chunks]
        metadatas: List[Dict[str, Any]] = [c.metadata for c in chunks]

        # Generate embeddings in batch for all text chunks
        embeddings: List[List[float]] = self.embedding_service.embed_batch(documents)

        # upsert() inserts new chunk IDs or safely updates existing ones
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    def upsert_document(self, chunked_doc: ChunkedDocument) -> int:
        """Convenience method to store all chunks from a ChunkedDocument."""
        return self.add_chunks(chunked_doc.chunks)

    def query_similar(
        self,
        query_text: str,
        n_results: int = 3,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Searches ChromaDB for the top-n most semantically relevant chunks.
        
        Args:
            query_text: The user's question or job requirement string.
            n_results: Maximum number of chunks to retrieve.
            where_filter: Optional metadata filter, e.g. {"source": "sample_resume.pdf"}.
            
        Returns:
            List[SearchResult]: Structured results sorted from most to least relevant.
        """
        query_text = query_text.strip()
        total_items = self._collection.count()
        if not query_text or total_items == 0:
            return []

        # Cap n_results to the total number of items in the collection
        safe_n = max(1, min(n_results, total_items))

        # Generate query vector
        query_vector = self.embedding_service.embed_text(query_text)

        # Perform query in ChromaDB
        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": safe_n,
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        results = self._collection.query(**query_kwargs)

        search_results: List[SearchResult] = []
        if not results["ids"] or not results["ids"][0]:
            return search_results

        ids = results["ids"][0]
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        for i in range(len(ids)):
            dist = float(distances[i]) if i < len(distances) else 1.0
            # In cosine space, similarity = 1.0 - distance
            similarity = max(0.0, min(1.0, 1.0 - dist))
            meta = metas[i] if i < len(metas) else {}

            search_results.append(
                SearchResult(
                    chunk_id=ids[i],
                    text=docs[i] if i < len(docs) else "",
                    source_doc=str(meta.get("source", "unknown")),
                    page_number=int(meta.get("page_number", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    distance=dist,
                    similarity_score=similarity,
                )
            )

        return search_results

    def delete_document(self, filename: str) -> None:
        """Deletes all chunks originating from a specific file."""
        self._collection.delete(where={"source": filename})

    def count(self) -> int:
        """Returns the total number of chunks currently stored in the collection."""
        return self._collection.count()

    def reset(self) -> None:
        """Clears the collection entirely. Useful between test runs."""
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )


# Singleton helper
_default_vector_store: Optional[VectorStoreService] = None


def get_vector_store_service() -> VectorStoreService:
    """Returns a shared singleton instance of the VectorStoreService."""
    global _default_vector_store
    if _default_vector_store is None:
        _default_vector_store = VectorStoreService()
    return _default_vector_store

"""
Unit Tests for Embedding Service & Semantic Similarity (Phase 4).
Tests cosine similarity math, vector normalization, 768-dim embedding output, and semantic matching.
"""

import math
import pytest

from backend.app.services.embedding_service import (
    EmbeddingService,
    cosine_similarity,
    get_embedding_service,
    normalize_vector,
)


# ==============================================================================
# Pure Vector Math Tests
# ==============================================================================

def test_cosine_similarity_identical_vectors():
    """Verify that identical vectors yield a cosine similarity of exactly 1.0."""
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    assert pytest.approx(cosine_similarity(v1, v2), 1e-6) == 1.0


def test_cosine_similarity_opposite_vectors():
    """Verify that opposite vectors yield a cosine similarity of -1.0."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [-1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 1e-6) == -1.0


def test_cosine_similarity_orthogonal_vectors():
    """Verify that perpendicular (orthogonal) vectors yield a cosine similarity of 0.0."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 1e-6) == 0.0


def test_cosine_similarity_dimension_mismatch():
    """Verify that vectors of differing lengths raise a ValueError."""
    v1 = [1.0, 2.0]
    v2 = [1.0, 2.0, 3.0]
    with pytest.raises(ValueError, match="Vector dimensions must match"):
        cosine_similarity(v1, v2)


def test_cosine_similarity_zero_vector():
    """Verify that a zero-magnitude vector returns 0.0 without a ZeroDivisionError."""
    v1 = [0.0, 0.0, 0.0]
    v2 = [1.0, 2.0, 3.0]
    assert cosine_similarity(v1, v2) == 0.0


def test_normalize_vector():
    """Verify that a normalized vector has a Euclidean norm (magnitude) of 1.0."""
    v = [3.0, 4.0]  # Length: sqrt(9 + 16) = 5.0
    norm_v = normalize_vector(v)
    magnitude = math.sqrt(sum(x * x for x in norm_v))
    assert pytest.approx(magnitude, 1e-6) == 1.0
    assert pytest.approx(norm_v[0], 1e-6) == 0.6
    assert pytest.approx(norm_v[1], 1e-6) == 0.8


# ==============================================================================
# Embedding Generation & Semantic Matching Tests
# ==============================================================================

def test_embed_text_dimensions():
    """Verify that generated embeddings are exactly 768 dimensions."""
    service = get_embedding_service()
    vec = service.embed_text("FastAPI backend developer")

    assert len(vec) == 768
    assert all(isinstance(val, float) for val in vec)
    # Check that vector is normalized (magnitude is approximately 1.0)
    mag = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(mag, 1e-4) == 1.0


def test_embed_batch():
    """Verify that batch embedding returns matching count of 768-dim vectors."""
    service = get_embedding_service()
    texts = [
        "Senior Python Engineer",
        "FastAPI REST APIs",
        "ChromaDB Vector Retrieval",
    ]
    vectors = service.embed_batch(texts)

    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 768


def test_semantic_similarity_ranking():
    """
    Core RAG test:
    Verify that a job requirement vector is significantly more similar to a matching
    resume skill snippet than to an unrelated snippet (e.g. baking).
    """
    service = get_embedding_service()

    query = "Looking for a Senior Python developer with FastAPI and ChromaDB vector search skills"
    matching_resume = (
        "Staff AI Engineer with 6+ years in Python backend development. "
        "Built enterprise RAG pipelines using FastAPI and ChromaDB vector search."
    )
    unrelated_text = (
        "Experienced French baker specializing in artisan sourdough baguettes, "
        "croissants, strawberry pastries, and morning bakery operations."
    )

    vec_query = service.embed_text(query)
    vec_match = service.embed_text(matching_resume)
    vec_unrelated = service.embed_text(unrelated_text)

    score_match = cosine_similarity(vec_query, vec_match)
    score_unrelated = cosine_similarity(vec_query, vec_unrelated)

    # The matching resume must have a much higher similarity score than the bakery text
    assert score_match > score_unrelated
    assert score_match >= 0.25
    assert score_unrelated <= 0.05

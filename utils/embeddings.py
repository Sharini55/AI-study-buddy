"""
Embedding generation for study material chunks.

Chunks produced by utils.chunking are converted to vectors here so
utils.persistence can store them in material_chunks.embedding, enabling
pgvector similarity search instead of the coarse topic_tags LIKE scan.

EMBEDDING_MODEL uses Matryoshka Representation Learning, so the same model
serves both document and query embeddings — only the task_type differs.
EMBEDDING_DIM lives in utils.persistence since it also fixes the pgvector
column width; both sides must agree on it.
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

from google.genai import types

from utils.gemini import get_gemini_client
from utils.persistence import EMBEDDING_DIM

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"


def _embed_one(client, text: str, task_type: str, retries: int = 4) -> list[float] | None:
    """Embed a single text with exponential backoff on quota errors.

    The Gemini API's embedding endpoint only accepts one text per request
    (unlike Vertex AI's batch embedding), so batches are parallelized across
    threads by the callers below rather than sent as one multi-text request.
    Returns None on unrecoverable failure so one bad chunk never blocks the
    rest of the batch or the calling upload flow.
    """
    config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIM)
    for attempt in range(retries):
        try:
            response = client.models.embed_content(model=EMBEDDING_MODEL, contents=text, config=config)
            return list(response.embeddings[0].values)
        except Exception as exc:
            err = str(exc)
            delay_match = re.search(r"retry[^\d]*(\d+)s", err, re.I)
            suggested = int(delay_match.group(1)) if delay_match else 0
            wait = max(suggested, 2 ** attempt)
            is_quota = "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()
            if is_quota and attempt < retries - 1:
                time.sleep(wait)
                continue
            logger.error("Embedding request failed for a chunk", exc_info=True)
            return None


def embed_chunks(api_key: str, chunk_texts: list[str]) -> list[list[float] | None]:
    """Embed chunk texts for storage (RETRIEVAL_DOCUMENT task type).

    Runs requests in parallel via a thread pool, capped the same way the
    existing Gemini call-sites cap concurrency to stay within RPM limits.
    Returns one vector (or None on failure) per input text, in order.
    """
    if not chunk_texts:
        return []
    client = get_gemini_client(api_key)
    max_workers = min(len(chunk_texts), 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(
            lambda t: _embed_one(client, t, task_type="RETRIEVAL_DOCUMENT"),
            chunk_texts,
        ))


def embed_query(api_key: str, query_text: str) -> list[float] | None:
    """Embed a single search query (RETRIEVAL_QUERY task type) for similarity search."""
    client = get_gemini_client(api_key)
    return _embed_one(client, query_text, task_type="RETRIEVAL_QUERY")

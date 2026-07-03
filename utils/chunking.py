"""
Text chunking for study materials.

Splits cleaned markdown content into overlapping chunks that are small
enough to embed individually and targeted enough for topic-level retrieval.
No vectors are generated here — this layer is purely structural, storing
chunk text + metadata so the quiz-feedback loop can pull only the relevant
passages when a student answers questions incorrectly.

Tuning constants
────────────────
CHUNK_SIZE    – target character count per chunk.  1 000 chars ≈ 200 tokens,
                which fits comfortably inside all common embedding model
                limits (512 tokens) while leaving room for the prompt
                template when the chunk is later fed to an LLM.

CHUNK_OVERLAP – characters repeated at the start of the next chunk.
                200 chars ≈ 20 % of CHUNK_SIZE.  This means a full sentence
                that straddles two chunk boundaries appears in full in at
                least one of them, preventing the retriever from finding
                half-answers that look like they match but lack the
                concluding clause.
"""

import json
import logging
import re
import uuid
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ── Tunable constants ────────────────────────────────────────────────────────
CHUNK_SIZE    = 1_000   # characters per chunk
CHUNK_OVERLAP = 200     # characters shared between adjacent chunks

# Separators tried in order by RecursiveCharacterTextSplitter.
# Markdown headings are promoted to the front so the splitter always prefers
# to break at a section boundary before falling back to paragraph → sentence
# → word → character splits.
_SEPARATORS = [
    "\n## ",    # Markdown h2 — our primary structural unit (clean_to_markdown adds these)
    "\n### ",   # Markdown h3
    "\n\n",     # Blank line / paragraph break
    "\n",       # Single newline
    ". ",       # Sentence boundary
    " ",        # Word boundary (last resort before character split)
    "",         # Character split (absolute fallback — never cuts a UTF-8 sequence)
]

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=_SEPARATORS,
    keep_separator=True,   # keeps the "## Heading" marker at the start of each chunk
    add_start_index=True,  # each Document.metadata["start_index"] records its byte offset
)


# ── Topic-tag extraction ─────────────────────────────────────────────────────

def _extract_topic_tags(chunk_text: str, source_name: str) -> list[str]:
    """Return structural topic tags from the chunk's markdown headings.

    These are simple string labels derived from ## / ### headings present in
    the chunk.  They are intentionally coarse — a future embedding pass will
    add semantic tags without changing the storage schema.
    """
    tags: list[str] = []
    for match in re.finditer(r"^#{1,3}\s+(.+?)\s*$", chunk_text, re.MULTILINE):
        tag = match.group(1).strip()
        if tag:
            tags.append(tag)
    # Fall back to the document name so there is always at least one tag.
    if not tags:
        tags.append(source_name)
    return tags


# ── Public API ───────────────────────────────────────────────────────────────

def chunk_document(
    content_text: str,
    source_file_id: str,
    workspace_id: str,
    source_name: str,
) -> list[dict]:
    """Split *content_text* into overlapping chunks and return a list of dicts.

    Each dict maps directly onto the columns of the ``MaterialChunk`` table:

        {
            "id":             str (uuid4 hex),
            "source_file_id": str,
            "workspace_id":   str,
            "chunk_index":    int,
            "chunk_text":     str,
            "topic_tags":     str  (JSON-encoded list[str]),
            "char_start":     int,
            "created_at":     datetime,
        }

    Returns an empty list if *content_text* is blank.
    """
    if not content_text or not content_text.strip():
        return []

    try:
        documents = _splitter.create_documents(
            texts=[content_text],
            metadatas=[{"source": source_name, "source_file_id": source_file_id}],
        )
    except Exception:
        logger.error(
            "RecursiveCharacterTextSplitter failed for source_file_id='%s'",
            source_file_id,
            exc_info=True,
        )
        return []

    chunks = []
    for idx, doc in enumerate(documents):
        tags = _extract_topic_tags(doc.page_content, source_name)
        chunks.append({
            "id":             uuid.uuid4().hex,
            "source_file_id": source_file_id,
            "workspace_id":   workspace_id,
            "chunk_index":    idx,
            "chunk_text":     doc.page_content,
            "topic_tags":     json.dumps(tags),
            "char_start":     doc.metadata.get("start_index", 0),
            "created_at":     datetime.utcnow(),
        })

    logger.info(
        "Chunked '%s': %d chunk(s) from %d chars",
        source_name, len(chunks), len(content_text),
    )
    return chunks


def retrieve_chunks_by_topics(
    db_session,
    workspace_id: str,
    topic_tags: list[str],
    *,
    MaterialChunk,
) -> list[str]:
    """Return chunk texts whose topic_tags overlap with *topic_tags*.

    Uses a simple JSON-substring match that works on both SQLite and
    PostgreSQL without extensions.  Replace with a proper GIN index query
    when you migrate to PostgreSQL full-time.

    Returns a deduplicated list of chunk texts ordered by (source_file_id,
    chunk_index) so the LLM receives material in reading order.
    """
    if not topic_tags:
        return []

    from sqlalchemy import or_

    # Build one LIKE filter per tag — matches if the serialised JSON list
    # contains the tag string anywhere inside it.
    filters = [
        MaterialChunk.topic_tags.like(f'%"{tag}"%')
        for tag in topic_tags
    ]
    rows = (
        db_session.query(MaterialChunk)
        .filter(MaterialChunk.workspace_id == workspace_id)
        .filter(or_(*filters))
        .order_by(MaterialChunk.source_file_id, MaterialChunk.chunk_index)
        .all()
    )

    seen: set[str] = set()
    result: list[str] = []
    for row in rows:
        if row.id not in seen:
            seen.add(row.id)
            result.append(row.chunk_text)
    return result

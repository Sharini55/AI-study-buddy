import hmac
import json
import logging
import os
import hashlib
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey, DateTime, Boolean, text, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.types import TypeDecorator

DB_FILE    = "sundevil_ai.db"
STORAGE_DIR = "./.storage/images"

# Width of the embedding vectors stored per chunk. gemini-embedding-001 defaults
# to 3072 dims but supports Matryoshka truncation via output_dimensionality —
# 768 keeps pgvector index size reasonable while staying well within the
# accuracy Google recommends for the truncated tiers (3072 / 1536 / 768).
EMBEDDING_DIM = 768

# OWASP recommended minimum for PBKDF2-SHA256 (2024).  Stored in every new hash
# so verify_password can handle hashes created with different iteration counts.
_PBKDF2_ITERATIONS = 260_000

os.makedirs(STORAGE_DIR, exist_ok=True)

# Use Azure PostgreSQL when DATABASE_URL is set; fall back to local SQLite for dev.
_DATABASE_URL = os.getenv("DATABASE_URL")
if _DATABASE_URL:
    logger.info("Connecting to PostgreSQL via DATABASE_URL")
    engine = create_engine(_DATABASE_URL)
else:
    logger.info("DATABASE_URL not set — using local SQLite (%s)", DB_FILE)
    engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_pgvector_extension() -> None:
    """Enable pgvector so the ``vector`` column type exists before table creation.

    No-op on SQLite (local dev fallback). Must run before Base.metadata.create_all().
    """
    if engine.dialect.name != "postgresql":
        return
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        except Exception:
            conn.rollback()
            logger.warning(
                "Could not enable the pgvector extension. On Azure Database for "
                "PostgreSQL Flexible Server, allow-list 'VECTOR' under the server's "
                "azure.extensions parameter before this will succeed.",
                exc_info=True,
            )


_ensure_pgvector_extension()


class EmbeddingType(TypeDecorator):
    """Cross-dialect vector column.

    Uses pgvector's native ``vector`` type on PostgreSQL so similarity search
    can use an ANN index. Falls back to a JSON-encoded float list on SQLite,
    which has no vector type but is only used for local dev.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector
            return dialect.type_descriptor(Vector(EMBEDDING_DIM))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)
        return json.loads(value)


# ---------------------------------------------------------------------------
# Database Tables (Schemas)
# ---------------------------------------------------------------------------

class User(Base):
    """Stores student login credentials and secure salted password hashes."""
    __tablename__ = "users"
    
    username = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Cascade deletes: If a user profile is deleted, delete all their workspaces
    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    """Subject container (e.g., CSE 230) belonging to a specific student profile."""
    __tablename__ = "workspaces"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.username"), nullable=False)
    subject_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="workspaces")
    files = relationship("SourceFile", back_populates="workspace", cascade="all, delete-orphan")
    guides = relationship("StudyGuide", back_populates="workspace", cascade="all, delete-orphan")
    quizzes = relationship("QuizAttempt", back_populates="workspace", cascade="all, delete-orphan")


class SourceFile(Base):
    """Extracted text and metadata from PDF, PPTX, or pasted slides/textbooks."""
    __tablename__ = "source_files"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'pdf', 'pptx', 'text'
    content_text = Column(Text, nullable=False)
    file_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="files")
    images = relationship("SourceImage", back_populates="source_file", cascade="all, delete-orphan")
    chunks = relationship("MaterialChunk", back_populates="source_file", cascade="all, delete-orphan")


class SourceImage(Base):
    """Tracks slide diagram locations on disk (Faux Object Storage)."""
    __tablename__ = "source_images"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_file_id = Column(String, ForeignKey("source_files.id"), nullable=False)
    label = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)  # e.g., "./.storage/images/xyz.png"
    mime_type = Column(String, nullable=False)
    
    source_file = relationship("SourceFile", back_populates="images")


class MaterialChunk(Base):
    """One semantically coherent slice of a SourceFile's extracted text.

    Chunks are created at index time by ``utils.chunking.chunk_document`` and
    stored here so the quiz-feedback loop can retrieve only the passages that
    are relevant to the topics a student answered incorrectly — without
    scanning the entire document.

    topic_tags  – JSON-encoded list[str] of heading-derived labels, e.g.
                  '["Binary Search Trees", "AVL Rotations"]'.
                  Queried with LIKE '%"<tag>"%' as a coarse pre-filter.
    char_start  – byte offset of this chunk inside the original content_text,
                  useful for debugging and future highlight-in-source features.
    embedding   – EMBEDDING_DIM-length vector from utils.embeddings, generated
                  at ingest time. NULL if embedding generation failed or was
                  skipped (e.g. no API key configured yet).
    """
    __tablename__ = "material_chunks"

    id             = Column(String,  primary_key=True, default=lambda: uuid.uuid4().hex)
    source_file_id = Column(String,  ForeignKey("source_files.id"), nullable=False)
    workspace_id   = Column(String,  ForeignKey("workspaces.id"),   nullable=False)
    chunk_index    = Column(Integer, nullable=False)
    chunk_text     = Column(Text,    nullable=False)
    topic_tags     = Column(Text,    nullable=True)   # JSON list of strings
    char_start     = Column(Integer, nullable=True)   # byte offset in source
    embedding      = Column(EmbeddingType, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    source_file = relationship("SourceFile", back_populates="chunks")

    # Composite index: workspace_id first so per-workspace tag scans are fast.
    __table_args__ = (
        Index("ix_material_chunks_ws_tags", "workspace_id", "topic_tags"),
    )


class StudyGuide(Base):
    """Stores generated active recall guides formatted with the Physics Method."""
    __tablename__ = "study_guides"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    title = Column(String, nullable=False)
    content_md = Column(Text, nullable=False)
    guide_hash = Column(String, nullable=True)   # sha-256[:12] of content; dedup key
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="guides")


class QuizAttempt(Base):
    """Keeps records of student quiz attempts and performance telemetry."""
    __tablename__ = "quiz_attempts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    score = Column(Integer, nullable=False)
    quiz_json = Column(Text, nullable=False)     # Serialized JSON string of questions
    answers_json = Column(Text, nullable=False)  # Serialized JSON string of student choices
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="quizzes")


# Build all local SQL tables on script initialization
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    logger.error(
        "Database schema creation failed. If the error mentions the 'vector' "
        "type, the pgvector extension isn't enabled — run CREATE EXTENSION "
        "vector; on the database (Azure Flexible Server also requires "
        "allow-listing 'VECTOR' under azure.extensions first).",
        exc_info=True,
    )
    raise


def _migrate_and_seed_admin() -> None:
    # Add is_admin to existing DBs that predate this column.
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
            conn.commit()
        except Exception:
            pass  # Column already exists — nothing to do.

    # Grant admin flag to the account named in the env var.
    admin_username = os.environ.get("ADMIN_USERNAME")
    if not admin_username:
        logger.warning(
            "ADMIN_USERNAME environment variable not configured. "
            "Skipping admin account seeding."
        )
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == admin_username).first()
        if user and not user.is_admin:
            user.is_admin = True
            db.commit()
    finally:
        db.close()


_migrate_and_seed_admin()


def _migrate_study_guide_hash() -> None:
    # Add guide_hash to existing DBs that predate this column.
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE study_guides ADD COLUMN guide_hash VARCHAR"))
            conn.commit()
        except Exception:
            pass  # Column already exists — nothing to do.


_migrate_study_guide_hash()


def _migrate_material_chunks() -> None:
    """Create the material_chunks table on databases that predate this column."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS material_chunks (
                    id             VARCHAR PRIMARY KEY,
                    source_file_id VARCHAR NOT NULL REFERENCES source_files(id),
                    workspace_id   VARCHAR NOT NULL REFERENCES workspaces(id),
                    chunk_index    INTEGER NOT NULL,
                    chunk_text     TEXT    NOT NULL,
                    topic_tags     TEXT,
                    char_start     INTEGER,
                    created_at     DATETIME
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_material_chunks_ws_tags "
                "ON material_chunks (workspace_id, topic_tags)"
            ))
            conn.commit()
        except Exception:
            pass  # Table already exists — nothing to do.


_migrate_material_chunks()


def _migrate_material_chunks_embedding() -> None:
    """Add the embedding column (and its ANN index) to DBs that predate vector storage."""
    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            try:
                conn.execute(text(
                    f"ALTER TABLE material_chunks ADD COLUMN embedding vector({EMBEDDING_DIM})"
                ))
                conn.commit()
            except Exception:
                conn.rollback()  # Column already exists, or extension unavailable.
            try:
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_material_chunks_embedding_cosine "
                    "ON material_chunks USING hnsw (embedding vector_cosine_ops)"
                ))
                conn.commit()
            except Exception:
                conn.rollback()  # pgvector too old for HNSW, or column missing.
        else:
            try:
                conn.execute(text("ALTER TABLE material_chunks ADD COLUMN embedding TEXT"))
                conn.commit()
            except Exception:
                conn.rollback()  # Column already exists — nothing to do.


_migrate_material_chunks_embedding()

# ---------------------------------------------------------------------------
# Salted Password Security (Security Hardening)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256.

    Format: ``{iterations}:{salt_hex}:{hash_hex}``  — storing the iteration
    count lets us raise it in future without breaking existing accounts.
    """
    salt = os.urandom(16)
    db_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{_PBKDF2_ITERATIONS}:{salt.hex()}:{db_hash.hex()}"


def verify_password(stored_signature: str, provided_password: str) -> bool:
    """Verify a password against its stored hash.

    Handles both the current 3-part format ``{iterations}:{salt}:{hash}`` and
    the legacy 2-part format ``{salt}:{hash}`` (which assumed 100 000 iterations).
    """
    try:
        parts = stored_signature.split(":")
        if len(parts) == 3:
            iterations = int(parts[0])
            salt      = bytes.fromhex(parts[1])
            db_hash   = bytes.fromhex(parts[2])
        elif len(parts) == 2:
            # Legacy hashes pre-date iteration storage — assume original count.
            iterations = 100_000
            salt      = bytes.fromhex(parts[0])
            db_hash   = bytes.fromhex(parts[1])
        else:
            return False
        test_hash = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(test_hash, db_hash)
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Faux Object Storage Helpers
# ---------------------------------------------------------------------------

def save_uploaded_image_locally(image_bytes: bytes, file_hash: str, index: int) -> str:
    """Writes heavy raw slide images directly to disk instead of bloating database rows."""
    filename = f"{file_hash}_{index}.png"
    destination_path = os.path.join(STORAGE_DIR, filename)
    
    if not os.path.exists(destination_path):
        with open(destination_path, "wb") as f:
            f.write(image_bytes)
            
    return destination_path


def load_local_image_bytes(storage_path: str) -> bytes:
    """Retrieves original image bytes from file storage during generation runs."""
    if os.path.exists(storage_path):
        with open(storage_path, "rb") as f:
            return f.read()
    return b""


def delete_workspace_from_db(workspace_id: str, owner_username: str | None = None) -> None:
    """Delete a workspace row, all its DB children, and physical image files.

    owner_username: when supplied the function verifies ownership before
    deleting — any mismatch is logged and the call is a no-op.
    """
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not ws:
            return
        if owner_username and ws.user_id != owner_username:
            logger.warning(
                "Unauthorized workspace delete: user '%s' attempted to delete "
                "workspace '%s' owned by '%s'",
                owner_username, workspace_id, ws.user_id,
            )
            return
        # Collect paths before cascade-delete removes SourceImage rows.
        paths = [
            img.storage_path
            for f in db.query(SourceFile).filter(SourceFile.workspace_id == workspace_id).all()
            for img in f.images
        ]
        db.delete(ws)  # cascade removes SourceFile → SourceImage rows
        db.commit()
    finally:
        db.close()
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass  # Already gone — nothing to clean up.


def delete_workspace_storage(workspace_id: str) -> None:
    """Delete all SourceFile rows for a workspace and remove their physical image files.

    Safe to call before or after a workspace reset — silently skips missing files.
    """
    db = SessionLocal()
    try:
        files = db.query(SourceFile).filter(SourceFile.workspace_id == workspace_id).all()
        paths = [img.storage_path for f in files for img in f.images]
        for f in files:
            db.delete(f)  # cascade removes SourceImage rows
        db.commit()
    finally:
        db.close()
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass  # Already gone — nothing to clean up.

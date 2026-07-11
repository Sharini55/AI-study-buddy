import os
import hashlib
import hmac
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey, DateTime, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Storage directory for slide images (disk-based, never in DB rows)
STORAGE_DIR = "./.storage/images"
os.makedirs(STORAGE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Database URL — read from environment so prod credentials never touch code.
# Falls back to local SQLite for development when DATABASE_URL is not set.
# ---------------------------------------------------------------------------
_DATABASE_URL = os.environ.get("DATABASE_URL", "")

if _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not _DATABASE_URL:
    _DATABASE_URL = "sqlite:///sundevil_ai.db"

_connect_args = {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------------------------------------------------------
# Database Tables (Schemas)
# ---------------------------------------------------------------------------

class User(Base):
    """Stores student login credentials and secure salted password hashes."""
    __tablename__ = "users"

    username     = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=True)   # real first name, set at signup step 2
    email        = Column(String, nullable=True)   # reserved for future email auth
    is_admin     = Column(Boolean, default=False, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    """Subject container (e.g., CSE 230) belonging to a specific student profile."""
    __tablename__ = "workspaces"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.username"), nullable=False)
    subject_name = Column(String, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    user    = relationship("User", back_populates="workspaces")
    files   = relationship("SourceFile",  back_populates="workspace", cascade="all, delete-orphan")
    guides  = relationship("StudyGuide",  back_populates="workspace", cascade="all, delete-orphan")
    quizzes = relationship("QuizAttempt", back_populates="workspace", cascade="all, delete-orphan")


class SourceFile(Base):
    """Extracted text and metadata from PDF, PPTX, or pasted slides/textbooks."""
    __tablename__ = "source_files"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    name         = Column(String, nullable=False)
    file_type    = Column(String, nullable=False)
    content_text = Column(Text,   nullable=False)
    file_hash    = Column(String, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace",   back_populates="files")
    images    = relationship("SourceImage", back_populates="source_file", cascade="all, delete-orphan")


class SourceImage(Base):
    """Tracks slide diagram locations on disk."""
    __tablename__ = "source_images"

    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_file_id = Column(String, ForeignKey("source_files.id"), nullable=False)
    label          = Column(String, nullable=False)
    storage_path   = Column(String, nullable=False)
    mime_type      = Column(String, nullable=False)

    source_file = relationship("SourceFile", back_populates="images")


class StudyGuide(Base):
    """Stores generated active recall guides."""
    __tablename__ = "study_guides"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    title        = Column(String, nullable=False)
    content_md   = Column(Text,   nullable=False)
    guide_hash   = Column(String, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="guides")


class QuizAttempt(Base):
    """Keeps records of student quiz attempts."""
    __tablename__ = "quiz_attempts"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    score        = Column(Integer, nullable=False)
    quiz_json    = Column(Text, nullable=False)
    answers_json = Column(Text, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="quizzes")


# Create any missing tables on startup (safe to run repeatedly)
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Safe column migrations — each in its own connection so one failure
# doesn't abort the others (PostgreSQL aborts the whole transaction on error)
# ---------------------------------------------------------------------------

def _safe_add_column(ddl: str) -> None:
    """Run a single DDL statement, silently ignore 'column already exists'."""
    try:
        with engine.connect() as conn:
            conn.execute(text(ddl))
            conn.commit()
    except Exception:
        pass   # column already exists or SQLite no-op — both fine


# Add columns introduced after initial deploy
_safe_add_column("ALTER TABLE users ADD COLUMN display_name VARCHAR(100)")
_safe_add_column("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
_safe_add_column("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
_safe_add_column("ALTER TABLE study_guides ADD COLUMN guide_hash VARCHAR(64)")


# ---------------------------------------------------------------------------
# Salted Password Security
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt     = os.urandom(16)
    db_hash  = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + db_hash.hex()


def verify_password(stored_signature: str, provided_password: str) -> bool:
    if not stored_signature or provided_password is None:
        return False

    try:
        password_bytes = provided_password.encode("utf-8")

        if ":" in stored_signature:
            salt_hex, hash_hex = stored_signature.split(":", 1)
            salt    = bytes.fromhex(salt_hex)
            db_hash = bytes.fromhex(hash_hex)
            test    = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, 100000)
            return hmac.compare_digest(test, db_hash)

        # Backward compatibility for early local accounts that were stored as
        # unsalted SHA-256 hex digests before PBKDF2 was introduced.
        if len(stored_signature) == 64:
            legacy_hash = hashlib.sha256(password_bytes).hexdigest()
            return hmac.compare_digest(legacy_hash, stored_signature.lower())
    except (TypeError, ValueError):
        return False

    return False


# ---------------------------------------------------------------------------
# Faux Object Storage Helpers
# ---------------------------------------------------------------------------

def save_uploaded_image_locally(image_bytes: bytes, file_hash: str, index: int) -> str:
    filename         = f"{file_hash}_{index}.png"
    destination_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(destination_path):
        with open(destination_path, "wb") as f:
            f.write(image_bytes)
    return destination_path


def load_local_image_bytes(storage_path: str) -> bytes:
    if os.path.exists(storage_path):
        with open(storage_path, "rb") as f:
            return f.read()
    return b""


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

def delete_workspace_from_db(username: str, workspace_id: str) -> None:
    """Permanently deletes a workspace and all its children (files, guides, quizzes)."""
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == username
        ).first()
        if ws:
            db.delete(ws)
            db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

import os
import hashlib
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

STORAGE_DIR = "./.storage/images"
os.makedirs(STORAGE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Database URL — reads from environment; falls back to local SQLite
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
# Database Tables
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"
    username      = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    is_admin      = Column(Boolean, default=False, nullable=False)
    workspaces    = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
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
    __tablename__ = "source_images"
    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_file_id = Column(String, ForeignKey("source_files.id"), nullable=False)
    label          = Column(String, nullable=False)
    storage_path   = Column(String, nullable=False)
    mime_type      = Column(String, nullable=False)
    source_file = relationship("SourceFile", back_populates="images")


class StudyGuide(Base):
    __tablename__ = "study_guides"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    title        = Column(String, nullable=False)
    content_md   = Column(Text,   nullable=False)
    guide_hash   = Column(String, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    workspace = relationship("Workspace", back_populates="guides")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    score        = Column(Integer, nullable=False)
    quiz_json    = Column(Text,    nullable=False)
    answers_json = Column(Text,    nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    workspace = relationship("Workspace", back_populates="quizzes")


class MetricEvent(Base):
    """One row per tracked event — persists to Postgres so data survives restarts."""
    __tablename__ = "metric_events"
    id         = Column(String,   primary_key=True, default=lambda: str(uuid.uuid4()))
    username   = Column(String,   nullable=False, index=True)
    event_name = Column(String,   nullable=False, index=True)
    subject    = Column(String,   nullable=True)
    properties = Column(Text,     nullable=True)   # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# Create tables (safe on existing DBs)
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Migration shim — add new columns to existing databases without Alembic
# ---------------------------------------------------------------------------
def _ensure_columns() -> None:
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    with engine.connect() as conn:
        users_cols  = {c["name"] for c in insp.get_columns("users")}
        guides_cols = {c["name"] for c in insp.get_columns("study_guides")}

        if "is_admin" not in users_cols:
            if _DATABASE_URL.startswith("sqlite"):
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL"))
            conn.commit()

        if "guide_hash" not in guides_cols:
            conn.execute(text("ALTER TABLE study_guides ADD COLUMN guide_hash VARCHAR"))
            conn.commit()

try:
    _ensure_columns()
except Exception:
    pass  # Non-fatal — table may already have the columns



# ---------------------------------------------------------------------------
# Salted Password Security
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    db_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + db_hash.hex()


def verify_password(stored_signature: str, provided_password: str) -> bool:
    try:
        salt_hex, hash_hex = stored_signature.split(":")
        salt    = bytes.fromhex(salt_hex)
        db_hash = bytes.fromhex(hash_hex)
        test    = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, 100000)
        return test == db_hash
    except Exception:
        return False
        
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

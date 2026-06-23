import hmac
import os
import hashlib
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey, DateTime, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Define local file path for our serverless SQLite database
DB_FILE = "sundevil_ai.db"
STORAGE_DIR = "./.storage/images"

# Ensure our local visual storage directory exists to safely hold slide images
os.makedirs(STORAGE_DIR, exist_ok=True)

# Initialize SQLAlchemy connection engine
engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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


class SourceImage(Base):
    """Tracks slide diagram locations on disk (Faux Object Storage)."""
    __tablename__ = "source_images"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_file_id = Column(String, ForeignKey("source_files.id"), nullable=False)
    label = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)  # e.g., "./.storage/images/xyz.png"
    mime_type = Column(String, nullable=False)
    
    source_file = relationship("SourceFile", back_populates="images")


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
Base.metadata.create_all(bind=engine)


def _migrate_and_seed_admin() -> None:
    # Add is_admin to existing DBs that predate this column.
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
            conn.commit()
        except Exception:
            pass  # Column already exists — nothing to do.

    # Grant admin flag to the account named in the env var.
    admin_username = os.environ.get("ADMIN_USERNAME", "sharinik")
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

# ---------------------------------------------------------------------------
# Salted Password Security (Security Hardening)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Generates a secure PBKDF2 salt-and-hash signature for student passwords."""
    salt = os.urandom(16)
    db_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + db_hash.hex()


def verify_password(stored_signature: str, provided_password: str) -> bool:
    """Authenticates raw password input against stored database signature."""
    try:
        salt_hex, hash_hex = stored_signature.split(":")
        salt = bytes.fromhex(salt_hex)
        db_hash = bytes.fromhex(hash_hex)
        test_hash = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, 100000)
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


def delete_workspace_from_db(workspace_id: str) -> None:
    """Delete a workspace row, all its DB children, and physical image files."""
    db = SessionLocal()
    try:
        # Collect paths before cascade-delete removes SourceImage rows.
        paths = [
            img.storage_path
            for f in db.query(SourceFile).filter(SourceFile.workspace_id == workspace_id).all()
            for img in f.images
        ]
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if ws:
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
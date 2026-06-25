import hashlib
import json
import logging
import os
import streamlit as st

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session

# Configuration & Subsystem Imports
from utils.auth import init_auth_session_state, render_login_signup_ui, logout_user
from utils.persistence import (
    SessionLocal, User, Workspace, SourceFile, SourceImage, StudyGuide, QuizAttempt,
    save_uploaded_image_locally, load_local_image_bytes, delete_workspace_from_db
)
from utils.files import blank_workspace, refresh_processed_text
from utils.guide import render_guide

APP_TITLE = "SunDevil AI"


# ---------------------------------------------------------------------------
# Theme — only static, hardcoded CSS uses unsafe_allow_html
# ---------------------------------------------------------------------------

def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #FCF9F1;
            --sidebar: #F4F1E8;
            --panel: #FFFDF7;
            --ink: #2D2D2D;
            --muted: #6F6A60;
            --line: #E7DECF;
            --rose: #E8A0BF;
            --gold: #D4AF37;
            --gold-dark: #B8942F;
        }

        /* ── Hide Streamlit chrome (header bar, theme switcher, footer) ── */
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        #MainMenu,
        footer { display: none !important; }

        /* Force app background even when OS is in dark mode */
        html, body { background: var(--bg) !important; color: var(--ink) !important; }
        .stApp { background: var(--bg) !important; color: var(--ink) !important; }
        .main .block-container { max-width: 1360px; padding-top: 1rem; }

        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] * { color: var(--ink); letter-spacing: 0; }

        [data-testid="stSidebar"] .stButton > button {
            background: #8C1D40 !important;
            border: 1px solid #8C1D40 !important;
            color: #FFFFFF !important;
            border-radius: 999px !important;
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] .stButton > button *,
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button span { color: #FFFFFF !important; }
        [data-testid="stSidebar"] .stButton > button:hover,
        [data-testid="stSidebar"] .stButton > button:focus {
            background: #741634 !important;
            border-color: #741634 !important;
            color: #FFFFFF !important;
        }

        h1, h2, h3, p, label, span { color: var(--ink); letter-spacing: 0; }

        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 999px;
            padding: 10px 16px;
            color: var(--ink);
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: #FFFFFF;
            border: 1px solid var(--line);
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 999px;
            border: 1.5px solid var(--line);
            background: #FFFFFF !important;
            color: #2D2D2D !important;
            font-weight: 650;
        }
        .stButton > button *,
        .stButton > button p,
        .stButton > button span,
        .stDownloadButton > button *,
        .stDownloadButton > button p,
        .stDownloadButton > button span {
            color: #2D2D2D !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: #F5F0E8 !important;
            border-color: #C4B89A !important;
            color: #2D2D2D !important;
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button {
            background: var(--gold) !important;
            border-color: var(--gold) !important;
            color: #2D2D2D !important;
            font-weight: 700;
        }
        .stButton > button[kind="primary"] *,
        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span,
        .stDownloadButton > button *,
        .stDownloadButton > button p,
        .stDownloadButton > button span {
            color: #2D2D2D !important;
        }
        .stButton > button[kind="primary"]:hover,
        .stDownloadButton > button:hover {
            background: var(--gold-dark) !important;
            border-color: var(--gold-dark) !important;
            color: #2D2D2D !important;
        }

        /* ── File uploader — force light theme throughout ── */
        [data-testid="stFileUploader"] {
            background: #FFFFFF !important;
            border: 2px dashed #C4B89A !important;
            border-radius: 14px !important;
            padding: 0.75rem 1rem !important;
        }
        [data-testid="stFileUploader"] label {
            color: var(--ink) !important;
            line-height: 1.5 !important;
            margin-bottom: 0.5rem !important;
            padding-top: 0 !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: #FFFFFF !important;
        }
        /* Instructions text only — intentionally excludes button spans */
        [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stFileUploaderDropzoneInstructions"] small,
        [data-testid="stFileUploaderDropzoneInstructions"] p,
        [data-testid="stFileUploader"] small {
            color: #2D2D2D !important;
        }
        /* Upload/Browse button — dark bg, white text.
           Covers old (baseButton-secondary), new (stBaseButton-secondary),
           and the dropzone container selector for maximum compat with Streamlit 1.58+. */
        [data-testid="stFileUploaderDropzone"] button,
        [data-testid="stFileUploaderDropzoneButton"],
        button[data-testid="stBaseButton-secondary"],
        [data-testid="stFileUploader"] [data-testid="baseButton-secondary"],
        [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            background: #1e1e1e !important;
            border: none !important;
            border-radius: 8px !important;
            color: #ffffff !important;
            font-weight: 600 !important;
        }
        [data-testid="stFileUploaderDropzone"] button span,
        [data-testid="stFileUploaderDropzone"] button p,
        [data-testid="stFileUploaderDropzoneButton"] span,
        [data-testid="stFileUploaderDropzoneButton"] p,
        button[data-testid="stBaseButton-secondary"] span,
        button[data-testid="stBaseButton-secondary"] p,
        [data-testid="stFileUploader"] [data-testid="baseButton-secondary"] span,
        [data-testid="stFileUploader"] [data-testid="baseButton-secondary"] p,
        [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] span,
        [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] p {
            color: #ffffff !important;
        }
        [data-testid="stFileUploaderDropzone"] button svg,
        [data-testid="stFileUploaderDropzoneButton"] svg,
        button[data-testid="stBaseButton-secondary"] svg { fill: #ffffff !important; }

        /* ── Username badge in sidebar — readable dark text on light bg ── */
        [data-testid="stSidebar"] code {
            background: #E7DECF !important;
            color: #2D2D2D !important;
            border-radius: 6px !important;
            padding: 2px 8px !important;
            font-weight: 700 !important;
        }

        div[data-testid="stAlert"] { border-radius: 14px; color: var(--ink); }
        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            color: #2D2D2D !important;
            caret-color: #2D2D2D !important;
            background: #FFFFFF !important;
        }
        input::placeholder,
        textarea::placeholder,
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #6F6A60 !important;
            opacity: 1 !important;
        }

        div[data-testid="stMetric"],
        div[data-testid="stTextArea"],
        div[data-testid="stExpander"] {
            background: var(--panel);
            border-radius: 14px;
        }
        div[data-testid="stTextArea"] textarea {
            border: 2px solid var(--rose);
            border-radius: 14px;
            background: #FFFFFF;
            color: var(--ink);
        }
        div[data-testid="stAlert"] { border-radius: 14px; color: var(--ink); }

        /* ── st.text renders as <pre> — keep ink color even in dark-OS ── */
        pre, pre * { color: var(--ink) !important; background: transparent !important; }

        /* ── Button testid selectors — survive Streamlit dark-theme override ── */
        /* Primary buttons (gold) */
        [data-testid="baseButton-primary"],
        [data-testid="baseButton-primary"] p,
        [data-testid="baseButton-primary"] span {
            background: var(--gold) !important;
            color: #2D2D2D !important;
            border-color: var(--gold) !important;
        }
        /* Secondary buttons (white) — file-uploader upload button rules above are
           more specific so they still win for that case */
        [data-testid="baseButton-secondary"],
        [data-testid="baseButton-secondary"] p,
        [data-testid="baseButton-secondary"] span {
            background: #FFFFFF !important;
            color: #2D2D2D !important;
        }

        /* ── Sidebar expand/collapse arrow — always dark/visible on cream bg ── */
        [data-testid="collapsedControl"],
        [data-testid="collapsedControl"] button {
            display: flex !important;
            visibility: visible !important;
            color: var(--ink) !important;
        }
        [data-testid="collapsedControl"] svg { fill: var(--ink) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# DATA SYNCING: Read/Write Streamlit Workspaces dynamically to SQLite
# ---------------------------------------------------------------------------

def load_user_workspaces_from_db(username: str) -> tuple[dict, list]:
    """Queries SQLite and marshals database rows back into Streamlit workspace dictionary.

    Returns (workspaces_dict, saved_guides) so the caller can set both in session state.
    """
    db: Session = SessionLocal()
    workspaces_dict = {}
    saved_guides: list = []
    try:
        user_record = db.query(User).filter(User.username == username).first()
        if user_record:
            for ws in user_record.workspaces:
                ws_data = blank_workspace()
                ws_data["id"] = ws.id
                
                # Load indexed files
                for file_row in ws.files:
                    images_list = []
                    for img_row in file_row.images:
                        img_bytes = load_local_image_bytes(img_row.storage_path)
                        images_list.append({
                            "label": img_row.label,
                            "bytes": img_bytes,
                            "mime_type": img_row.mime_type
                        })
                    
                    ws_data["files"].append({
                        "id": file_row.id,
                        "name": file_row.name,
                        "type": file_row.file_type,
                        "content": file_row.content_text,
                        "images": images_list
                    })
                
                refresh_processed_text(ws_data)
                
                # Load all saved guides; populate sidebar list and restore active guide
                all_guides = db.query(StudyGuide).filter(
                    StudyGuide.workspace_id == ws.id
                ).order_by(StudyGuide.created_at.desc()).all()
                if all_guides:
                    ws_data["generated_notes"] = all_guides[0].content_md
                for g in all_guides:
                    saved_guides.append({
                        "id": g.guide_hash or g.id[:12],
                        "title": g.title,
                        "subject": ws.subject_name,
                        "content": g.content_md,
                        "saved_at": g.created_at.strftime("%b %d, %H:%M") if g.created_at else "",
                    })
                
                # Load quiz historical entries
                for quiz_row in ws.quizzes:
                    try:
                        questions = json.loads(quiz_row.quiz_json)
                        answers   = json.loads(quiz_row.answers_json)
                        missed    = [
                            q for i, q in enumerate(questions)
                            if answers.get(str(i)) != q.get("answer_index")
                        ]
                        ws_data["quiz_history"].append({
                            "score": quiz_row.score,
                            "questions": questions,
                            "answers": answers,
                            "missed_questions": missed,
                        })
                    except Exception:
                        continue
                        
                workspaces_dict[ws.subject_name] = ws_data
    finally:
        db.close()
    return workspaces_dict, saved_guides


def save_active_workspace_to_db(username: str, subject_name: str, ws_memory: dict):
    """Commits active memory modifications (guides, scores, uploads) back to SQLite tables."""
    db: Session = SessionLocal()
    try:
        ws_row = db.query(Workspace).filter(Workspace.user_id == username, Workspace.subject_name == subject_name).first()
        if not ws_row:
            ws_row = Workspace(user_id=username, subject_name=subject_name)
            db.add(ws_row)
            db.commit()
            db.refresh(ws_row)
            
        ws_memory["id"] = ws_row.id
        
        # Sync files
        for file_item in ws_memory.get("files", []):
            content_hash = hashlib.sha256(file_item["content"].encode("utf-8")).hexdigest() if file_item["content"] else "empty"
            existing_file = db.query(SourceFile).filter(SourceFile.workspace_id == ws_row.id, SourceFile.file_hash == content_hash).first()
            if not existing_file:
                
                new_file = SourceFile(
                    workspace_id=ws_row.id,
                    name=file_item["name"],
                    file_type=file_item["type"],
                    content_text=file_item["content"],
                    file_hash=content_hash
                )
                db.add(new_file)
                db.commit()
                db.refresh(new_file)
                
                for idx, img_item in enumerate(file_item.get("images", [])):
                    storage_path = save_uploaded_image_locally(img_item["bytes"], content_hash, idx)
                    new_img = SourceImage(
                        source_file_id=new_file.id,
                        label=img_item.get("label", f"Slide Image {idx}"),
                        storage_path=storage_path,
                        mime_type=img_item["mime_type"]
                    )
                    db.add(new_img)
                db.commit()
                
        # Sync all saved guides for this workspace, deduped by guide_hash
        for guide in st.session_state.get("saved_guides", []):
            if guide.get("subject") != subject_name:
                continue
            existing_guide = db.query(StudyGuide).filter(
                StudyGuide.workspace_id == ws_row.id,
                StudyGuide.guide_hash == guide["id"],
            ).first()
            if not existing_guide:
                db.add(StudyGuide(
                    workspace_id=ws_row.id,
                    title=guide["title"],
                    content_md=guide["content"],
                    guide_hash=guide["id"],
                ))
        db.commit()
            
        # Sync quiz history entries
        stored_attempts_count = db.query(QuizAttempt).filter(QuizAttempt.workspace_id == ws_row.id).count()
        memory_history = ws_memory.get("quiz_history", [])
        if len(memory_history) > stored_attempts_count:
            for attempt in memory_history[stored_attempts_count:]:
                new_attempt = QuizAttempt(
                    workspace_id=ws_row.id,
                    score=attempt["score"],
                    quiz_json=json.dumps(attempt.get("questions", [])),
                    answers_json=json.dumps(attempt.get("answers", {}))
                )
                db.add(new_attempt)
            db.commit()
            
    except Exception:
        db.rollback()
        logger.error("save_active_workspace_to_db failed (user=%s, subject=%s)", username, subject_name, exc_info=True)
        st.error("Something went wrong while saving your workspace. Please try again.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Sidebar View Block (Authentication-Aware)
# ---------------------------------------------------------------------------

def render_workspace_sidebar(username: str, is_admin: bool = False) -> tuple[str, str, str]:
    with st.sidebar:
        if is_admin:
            in_admin = st.session_state.get("admin_view", False)
            label = "← Back to Study" if in_admin else "🛠 Admin Dashboard"
            if st.button(label, use_container_width=True):
                st.session_state["admin_view"] = not in_admin
                st.rerun()
            st.divider()

        st.markdown(f"🔬 **Student Profile:** `{username}`")
        st.divider()
        st.header("Workspace")
        
        new_subject = st.text_input("New Subject Name", placeholder="CSE 230, Physics, MAT 243")
        if st.button("Create Workspace", type="primary", use_container_width=True):
            subject = new_subject.strip()
            if subject:
                st.session_state["workspaces"].setdefault(subject, blank_workspace())
                st.session_state["active_workspace"] = subject
                save_active_workspace_to_db(username, subject, st.session_state["workspaces"][subject])
                st.rerun()

        subjects = list(st.session_state["workspaces"].keys())
        active = st.session_state.get("active_workspace", subjects[0])
        if active not in subjects:
            active = subjects[0]

        selected = st.radio(
            "Switch Workspace", subjects,
            index=subjects.index(active),
            key="workspace_selector",
        )
        st.session_state["active_workspace"] = selected

        if st.button("Delete Workspace", type="primary", use_container_width=True):
            if len(st.session_state["workspaces"]) == 1:
                st.warning("Create another workspace before deleting the last one.")
            else:
                ws_id = st.session_state["workspaces"][selected].get("id")
                if ws_id:
                    delete_workspace_from_db(ws_id)
                del st.session_state["workspaces"][selected]
                st.session_state["active_workspace"] = next(iter(st.session_state["workspaces"]))
                st.rerun()

        st.divider()
        with st.expander("⚙ Settings"):
            api_key = st.text_input("Gemini API Key", value="", type="password",
                                    placeholder="Paste your key here…")
            from utils.gemini import GEMINI_MODEL
            st.caption(f"Model: `{GEMINI_MODEL}`")

        study_mode = st.radio("Study Mode", ["Deep Dive", "Cram Mode"])

        # ── Saved Guides ──────────────────────────────────────────────────
        saved = st.session_state.get("saved_guides", [])
        if saved:
            st.divider()
            st.markdown("**📚 Saved Guides**")
            for guide in saved:
                guide_id = guide["id"]
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    btn_label = f"{guide['title']}  •  {guide['saved_at']}"
                    if st.button(btn_label, key=f"open_guide_{guide_id}", use_container_width=True):
                        st.session_state["viewing_guide"] = guide_id
                        st.rerun()
                with col_del:
                    if st.button("✕", key=f"del_guide_{guide_id}", help="Remove"):
                        if st.session_state.get("viewing_guide") == guide_id:
                            st.session_state["viewing_guide"] = None
                        st.session_state["saved_guides"] = [
                            g for g in st.session_state["saved_guides"] if g["id"] != guide_id
                        ]
                        st.rerun()

        st.divider()
        col_profile, col_logout = st.columns(2)
        with col_profile:
            if st.button("👤 Profile", use_container_width=True):
                st.session_state["viewing_profile"] = True
                st.rerun()
        with col_logout:
            if st.button("Log Out 🚪", use_container_width=True):
                logout_user()

    return selected, api_key, study_mode


# ---------------------------------------------------------------------------
# Profile Settings page
# ---------------------------------------------------------------------------

def render_profile_page(current_user: str) -> None:
    from utils.auth import delete_account

    if st.button("← Back to workspace"):
        st.session_state["viewing_profile"] = False
        st.rerun()

    st.title("👤 Profile Settings")
    st.caption(f"Logged in as **{current_user}**")
    st.divider()

    # ── Account stats ──────────────────────────────────────────────────────
    workspaces = st.session_state.get("workspaces", {})
    ws_count    = len(workspaces)
    guide_count = sum(1 for ws in workspaces.values() if ws.get("generated_notes"))
    quiz_count  = sum(len(ws.get("quiz_history", [])) for ws in workspaces.values())

    c1, c2, c3 = st.columns(3)
    c1.metric("Workspaces", ws_count)
    c2.metric("Guides Generated", guide_count)
    c3.metric("Quizzes Taken", quiz_count)
    st.divider()

    # ── Change password ────────────────────────────────────────────────────
    st.subheader("🔑 Change Password")
    with st.form("change_password_form"):
        current_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input(
            "New Password",
            type="password",
            placeholder="Min 8 chars · 1 number · 1 special character",
        )
        confirm_pw = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button("Update Password", use_container_width=True):
            from utils.auth import _validate_password
            from utils.persistence import verify_password, hash_password, SessionLocal, User
            if not current_pw or not new_pw or not confirm_pw:
                st.error("Please fill in all fields.")
            elif new_pw != confirm_pw:
                st.error("New passwords do not match.")
            else:
                ok, msg = _validate_password(new_pw)
                if not ok:
                    st.error(msg)
                else:
                    db2 = SessionLocal()
                    try:
                        user = db2.query(User).filter(User.username == current_user).first()
                        if not verify_password(user.password_hash, current_pw):
                            st.error("Current password is incorrect.")
                        else:
                            user.password_hash = hash_password(new_pw)
                            db2.commit()
                            st.success("Password updated successfully.")
                    finally:
                        db2.close()

    st.divider()

    # ── Danger zone ────────────────────────────────────────────────────────
    st.subheader("⚠️ Danger Zone")
    st.caption("These actions are permanent and cannot be undone.")

    if not st.session_state.get("_confirm_delete_account"):
        if st.button("🗑 Delete My Account", use_container_width=True):
            st.session_state["_confirm_delete_account"] = True
            st.rerun()
    else:
        st.error(
            f"This will permanently delete your account **{current_user}** and ALL associated "
            "workspaces, guides, and quiz history. Type your username to confirm."
        )
        typed = st.text_input("Type your username to confirm deletion")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Permanently Delete Account", type="primary", use_container_width=True):
                if typed.strip().lower() == current_user:
                    success, msg = delete_account(current_user)
                    if success:
                        from utils.auth import logout_user
                        logout_user()
                    else:
                        st.error(msg)
                else:
                    st.error("Username does not match.")
        with col_no:
            if st.button("Cancel", use_container_width=True):
                st.session_state.pop("_confirm_delete_account", None)
                st.rerun()


# ---------------------------------------------------------------------------
# Guide viewer page
# ---------------------------------------------------------------------------

def render_guide_viewer(guide: dict) -> None:
    if st.button("← Back to workspace"):
        st.session_state["viewing_guide"] = None
        st.rerun()

    st.title(guide["title"])
    st.caption(f"Saved at {guide['saved_at']}")
    st.download_button(
        "⬇ Download (.md)",
        data=guide["content"].encode("utf-8"),
        file_name=f"{guide['title'].lower().replace(' ', '_').replace('—', '').replace(' ', '_')}.md",
        mime="text/markdown",
        type="primary",
    )
    st.divider()
    render_guide(guide["content"])


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------

def render_admin_dashboard(current_user: str) -> None:
    from tabs.db_inspector import render_db_inspector_tab
    from utils.metrics import _report_path, _METRICS_DIR
    import pandas as pd

    st.title("🛠 Admin Dashboard")
    st.caption(f"Logged in as **{current_user}**")

    admin_tab, metrics_tab, users_tab = st.tabs([
        "🕵️ Database Inspector", "📊 User Metrics", "👥 Users"
    ])

    with admin_tab:
        render_db_inspector_tab()

    with metrics_tab:
        st.subheader("Per-User Metrics")
        if _METRICS_DIR.exists():
            user_dirs = [d for d in _METRICS_DIR.iterdir() if d.is_dir()]
            if not user_dirs:
                st.info("No metrics recorded yet.")
            else:
                for user_dir in sorted(user_dirs):
                    uname = user_dir.name
                    report = _report_path(uname)
                    with st.expander(f"📁 {uname}", expanded=False):
                        if report.exists() and report.stat().st_size > 0:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.caption(f"{report.stat().st_size // 1024 + 1} KB")
                            with col2:
                                st.download_button(
                                    "⬇ Download",
                                    data=report.read_bytes(),
                                    file_name=f"{uname}_metrics.md",
                                    mime="text/markdown",
                                    key=f"dl_metrics_{uname}",
                                )
                            preview = report.read_text(encoding="utf-8")
                            st.markdown(preview[:4000] + ("\n\n_— download for full report —_" if len(preview) > 4000 else ""))
                        else:
                            st.caption("No activity yet.")
        else:
            st.info("No metrics directory found.")

    with users_tab:
        from utils.persistence import SessionLocal, User
        db = SessionLocal()
        try:
            users = db.query(User).all()
            if users:
                st.dataframe(
                    pd.DataFrame([{
                        "Username": u.username,
                        "Workspaces": len(u.workspaces),
                        "Registered": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "—",
                    } for u in users]),
                    use_container_width=True,
                )
            else:
                st.info("No users yet.")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Main Execution Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=":books:", layout="wide")
    init_auth_session_state()
    apply_theme()

    # 1. Auth gate
    if not st.session_state["authenticated"]:
        render_login_signup_ui()
        st.stop()

    current_user = st.session_state["username"]
    is_admin = st.session_state.get("is_admin", False)

    # 2. Session state bootstrap
    st.session_state.setdefault("saved_guides", [])
    st.session_state.setdefault("viewing_guide", None)
    st.session_state.setdefault("admin_view", False)
    st.session_state.setdefault("viewing_profile", False)
    st.session_state.setdefault("is_dirty", False)

    # 3. Load workspaces from DB on first run
    if "workspaces" not in st.session_state or not st.session_state["workspaces"]:
        loaded, loaded_guides = load_user_workspaces_from_db(current_user)
        if loaded:
            st.session_state["workspaces"] = loaded
            st.session_state["active_workspace"] = next(iter(loaded))
            st.session_state["saved_guides"] = loaded_guides
        else:
            st.session_state["workspaces"] = {"My First Workspace": blank_workspace()}
            st.session_state["active_workspace"] = "My First Workspace"
            save_active_workspace_to_db(current_user, "My First Workspace",
                                        st.session_state["workspaces"]["My First Workspace"])

    subject, api_key, study_mode = render_workspace_sidebar(current_user, is_admin)

    # 4. Profile page
    if st.session_state.get("viewing_profile"):
        render_profile_page(current_user)
        return

    # 5. Admin dashboard
    if is_admin and st.session_state.get("admin_view"):
        render_admin_dashboard(current_user)
        return

    # 6. Saved guide viewer
    viewing_id = st.session_state.get("viewing_guide")
    if viewing_id is not None:
        saved = st.session_state.get("saved_guides", [])
        guide_to_view = next((g for g in saved if g["id"] == viewing_id), None)
        if guide_to_view:
            render_guide_viewer(guide_to_view)
            return
        st.session_state["viewing_guide"] = None

    # 7. Main workspace UI
    workspace = st.session_state["workspaces"][subject]

    st.title(APP_TITLE)
    st.caption("Warm, focused study workspaces for every course and major.")
    st.subheader(subject)

    from tabs.ingest import render_ingest_tab
    from tabs.study import render_study_tab
    from tabs.quiz import render_quiz_tab

    ingest_tab, guide_tab, quiz_tab = st.tabs(["Ingest Material", "Study Guide", "Interactive Quiz"])

    with ingest_tab:
        render_ingest_tab(subject, workspace, api_key)
    with guide_tab:
        render_study_tab(api_key, subject, workspace, study_mode)
    with quiz_tab:
        render_quiz_tab(api_key, subject, workspace)

    if st.session_state["is_dirty"]:
        save_active_workspace_to_db(current_user, subject, workspace)
        st.session_state["is_dirty"] = False


if __name__ == "__main__":
    main()

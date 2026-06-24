import logging
import os
import re
import time
import streamlit as st
from utils.persistence import SessionLocal, User, hash_password, verify_password

logger = logging.getLogger(__name__)


def init_auth_session_state():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False
    if "active_workspace" not in st.session_state:
        st.session_state["active_workspace"] = None


def _validate_password(password: str) -> tuple[bool, str]:
    """Enforce: ≥8 chars, ≥1 digit, ≥1 special character."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
        return False, "Password must contain at least one special character (!@#$% etc)."
    return True, ""


def register_user(username_input: str, password_input: str) -> tuple[bool, str]:
    username = username_input.strip().lower()
    password = password_input.strip()

    if not username or not password:
        return False, "Username and password cannot be empty."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if not re.match(r"^[a-z0-9_]+$", username):
        return False, "Username may only contain letters, numbers, and underscores."

    ok, msg = _validate_password(password)
    if not ok:
        return False, msg

    reserved = os.environ.get("ADMIN_USERNAME", "").strip().lower()
    if reserved and username == reserved:
        return False, "Registration rejected: This username is reserved or unavailable."

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return False, "That username is already taken — please choose a different one."
        new_user = User(username=username, password_hash=hash_password(password))
        db.add(new_user)
        db.commit()
        return True, "Account created! You can now log in."
    except Exception:
        db.rollback()
        logger.error("register_user failed for '%s'", username, exc_info=True)
        return False, "Something went wrong while creating your account. Please try again."
    finally:
        db.close()


def login_user(username_input: str, password_input: str) -> tuple[bool, str]:
    username = username_input.strip().lower()
    password = password_input.strip()

    if not username or not password:
        return False, "Please enter both your username and password."

    db = SessionLocal()
    try:
        user_record = db.query(User).filter(User.username == username).first()
        if not user_record:
            return False, "Invalid username or password."
        if verify_password(user_record.password_hash, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.session_state["is_admin"] = bool(user_record.is_admin)
            return True, "Login successful!"
        return False, "Invalid username or password."
    except Exception:
        logger.error("login_user failed for '%s'", username, exc_info=True)
        return False, "Something went wrong while logging in. Please try again."
    finally:
        db.close()


def delete_account(username: str) -> tuple[bool, str]:
    """Permanently deletes the user, all their DB rows, and their physical image files."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, "User not found."
        # Collect paths BEFORE cascade-delete removes the SourceImage rows.
        image_paths = [
            img.storage_path
            for ws in user.workspaces
            for f in ws.files
            for img in f.images
        ]
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        logger.error("delete_account failed for '%s'", username, exc_info=True)
        return False, "Something went wrong while deleting your account. Please try again."
    finally:
        db.close()
    # Remove physical files after the DB transaction succeeds.
    for path in image_paths:
        try:
            os.remove(path)
        except OSError:
            pass  # Already gone — nothing to clean up.
    return True, "Account deleted."


def logout_user():
    for key in ["authenticated", "username", "is_admin", "active_workspace", "workspaces",
                "saved_guides", "viewing_guide", "admin_view"]:
        st.session_state.pop(key, None)
    st.rerun()


def render_login_signup_ui():
    init_auth_session_state()

    st.markdown(
        """
        <div style="text-align:center; margin-top:2rem; margin-bottom:2rem;">
            <h1 style="color:#8C1D40; font-size:2.8rem; font-weight:800;
                       letter-spacing:-1px; margin-bottom:0.2rem;">🔱 SunDevil AI</h1>
            <p style="color:#6F6A60; font-size:1.15rem;">
                Active-Recall Study Workspaces
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔒 Log In", "📝 Create Account"])

        with tab_login:
            st.subheader("Welcome Back!")
            with st.form("login_form", clear_on_submit=False):
                user_login = st.text_input("Username", placeholder="your username")
                pass_login = st.text_input("Password", type="password", placeholder="••••••••")
                if st.form_submit_button("Log In", use_container_width=True):
                    success, msg = login_user(user_login, pass_login)
                    if success:
                        st.toast(msg, icon="🔥")
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_signup:
            st.subheader("Create Your Account")
            st.caption("All workspaces, guides, and quiz history are stored privately under your account.")
            with st.form("signup_form", clear_on_submit=True):
                user_signup = st.text_input("Choose a Username",
                                             placeholder="letters, numbers, underscores only")
                pass_signup = st.text_input(
                    "Create Password",
                    type="password",
                    placeholder="Min 8 chars · 1 number · 1 special character",
                    help="Requirements: 8+ characters, at least one number, at least one special character (!@#$% etc.)"
                )
                if st.form_submit_button("Create Account", use_container_width=True):
                    success, msg = register_user(user_signup, pass_signup)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

import datetime
import hashlib
import logging
import threading
import time

import streamlit as st

from utils.gemini import generate_study_guide_sot, describe_gemini_error
from utils.guide import render_guide

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared Gemini API key — the key baked in at deploy time that free users
# fall back to when they haven't pasted their own.
# Set SHARED_GEMINI_KEY as an Azure App Service environment variable.
# ---------------------------------------------------------------------------
import os
_SHARED_KEY = os.environ.get("SHARED_GEMINI_KEY", "")


def _get_effective_api_key() -> tuple[str, bool]:
    """
    Returns (api_key, using_own_key).
    Priority: user's own key > shared backend key.
    """
    user_key = st.session_state.get("gemini_api_key", "").strip()
    if user_key:
        return user_key, True
    return _SHARED_KEY, False


def _quota_banner(usage: dict, kind: str) -> None:
    """Render a compact counter pill showing remaining uses."""
    if kind == "guide":
        remaining = usage["guides_remaining"]
        total     = usage["guide_limit"]
    else:
        remaining = usage["quizzes_remaining"]
        total     = usage["quiz_limit"]

    if remaining == total:
        color, msg = "#ABC270", f"✨ You have {remaining} free {kind} generation{'s' if remaining != 1 else ''} today"
    elif remaining > 0:
        color, msg = "#D9A441", f"⚡ {remaining} of {total} free {kind} generation{'s' if remaining != 1 else ''} left today"
    else:
        color, msg = "#C0392B", f"🔒 Daily {kind} limit reached"

    st.markdown(
        f"<div style='display:inline-block;background:{color}22;border:1.5px solid {color};"
        f"border-radius:999px;padding:4px 14px;font-size:0.82rem;font-weight:600;"
        f"color:{color};margin-bottom:0.75rem;font-family:Truculenta,sans-serif;'>"
        f"{msg}</div>",
        unsafe_allow_html=True,
    )


def _limit_reached_ui(kind: str) -> None:
    """Show the 'come back tomorrow or use your own key' wall."""
    st.markdown(
        f"""
        <div style="background:#FFF8F8;border:2px solid #C0392B;border-radius:14px;
                    padding:1.25rem 1.5rem;margin-bottom:1rem;">
          <strong style="color:#C0392B;font-family:'Truculenta',sans-serif;font-size:1rem;">
            🔒 You've used your {3 if kind == "guide" else 2} free {kind} generation{'s' if True else ''} for today
          </strong>
          <p style="color:#5C6A48;font-family:'Truculenta',sans-serif;font-size:0.9rem;
                    margin:0.5rem 0 0;">
            Come back tomorrow — or paste your own free Gemini API key in
            <strong>Settings</strong> to generate unlimited guides and quizzes.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([2, 5])
    with col1:
        if st.button("Go to Settings →", type="primary", key=f"quota_settings_{kind}"):
            st.session_state["current_page"] = "Settings"
            st.rerun()


def _save_guide(subject: str, content: str, label: str = "Study Guide") -> None:
    guide_id = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    existing_ids = {g["id"] for g in st.session_state.get("saved_guides", [])}
    if guide_id not in existing_ids:
        st.session_state["saved_guides"].append({
            "id": guide_id,
            "title": f"{subject} — {label}",
            "subject": subject,
            "content": content,
            "saved_at": datetime.datetime.now().strftime("%b %d, %H:%M"),
        })


def _generate_with_progress(api_key: str, subject: str, workspace: dict, mode: str) -> str:
    progress = st.progress(0.05, text="Analyzing materials and planning your guide…")
    progress_state: dict = {"stage": "init", "done": 0, "total": 0}
    state_lock = threading.Lock()
    result_holder: dict = {}
    username = st.session_state.get("username", "anonymous")

    def on_progress(event: str, *args) -> None:
        with state_lock:
            if event == "skeleton_done":
                progress_state.update(stage="sections", total=args[0], done=0)
            elif event == "section_done":
                progress_state.update(done=args[0], total=args[1])

    def _run() -> None:
        try:
            result_holder["output"] = generate_study_guide_sot(
                api_key, subject, workspace, mode,
                progress_callback=on_progress,
                username=username,
            )
        except Exception as exc:
            result_holder["error"] = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    while thread.is_alive():
        with state_lock:
            state = dict(progress_state)
        if state["stage"] == "init":
            progress.progress(0.08, text="Planning your study guide…")
        elif state["stage"] == "sections":
            total, done = state["total"], state["done"]
            frac = 0.15 + (done / total) * 0.80 if total else 0.15
            progress.progress(frac, text=f"Writing sections… ({done}/{total} complete)")
        time.sleep(0.3)

    thread.join()
    progress.progress(1.0, text="Done!")
    time.sleep(0.3)
    progress.empty()

    if "error" in result_holder:
        raise result_holder["error"]
    return result_holder["output"]


def render_study_tab(api_key_unused: str, subject: str, workspace: dict, mode: str) -> None:
    """api_key_unused kept for signature compatibility — we resolve the key here."""
    from utils.metrics import get_daily_usage

    wid = workspace.get("id", subject)
    effective_key, using_own_key = _get_effective_api_key()
    username = st.session_state.get("username", "anonymous")

    # Only count/show quota when the user is on the shared key
    if not using_own_key:
        usage = get_daily_usage(username)
        _quota_banner(usage, "guide")
        guide_blocked = usage["guides_remaining"] <= 0 and not effective_key
    else:
        usage = None
        guide_blocked = False

    if guide_blocked:
        _limit_reached_ui("guide")
    elif st.button("Generate Study Guide", type="primary"):
        if not effective_key:
            # No shared key configured and no own key — shouldn't normally happen
            st.warning("No API key available. Go to Settings and paste your free Gemini key.")
        elif not workspace["files"]:
            st.warning("Add material in the Ingest Material tab first.")
        else:
            try:
                output = _generate_with_progress(effective_key, subject, workspace, mode)
                workspace["generated_notes"] = output
                st.session_state["is_dirty"] = True
                _save_guide(subject, workspace["generated_notes"], f"{mode} Guide")
            except Exception as exc:
                logger.error("Study guide generation failed: %s", exc, exc_info=True)
                st.error(describe_gemini_error(exc))

    if workspace["generated_notes"]:
        guide_hash = hashlib.sha256(workspace["generated_notes"].encode()).hexdigest()[:8]
        st.download_button(
            "⬇ Download Study Guide (.md)",
            data=workspace["generated_notes"].encode("utf-8"),
            file_name=f"{subject.lower().replace(' ', '_')}_study_guide.md",
            mime="text/markdown",
            type="primary",
            key=f"dl_guide_{wid}_{guide_hash}",
        )
        st.markdown(
            "<div style='background:#FFFFFF;border:1.5px solid #C5D99A;border-radius:18px;"
            "padding:1.5rem 1.75rem;margin-top:1rem;'>",
            unsafe_allow_html=True,
        )
        render_guide(workspace["generated_notes"])
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='background:#FFFFFF;border:1.5px solid #C5D99A;border-radius:18px;"
            "padding:2rem;text-align:center;margin-top:1rem;'>"
            "<p style='color:#5C6A48;font-family:\"Truculenta\",sans-serif;font-size:1rem;'>"
            "Generate a study guide after indexing material.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

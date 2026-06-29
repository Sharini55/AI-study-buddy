import datetime
import hashlib
import logging
import threading
import time

import streamlit as st

from utils.gemini import generate_study_guide_sot
from utils.guide import render_guide

logger = logging.getLogger(__name__)


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
    """
    Runs SoT generation in a background thread and animates a real-progress bar.

    The progress bar reflects actual work: Stage 1 skeleton (~15%) then each
    completed section advances the bar proportionally toward 95%.
    """
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
            label = f"Writing sections in parallel… ({done}/{total} complete)"
            progress.progress(frac, text=label)
        time.sleep(0.3)

    thread.join()
    progress.progress(1.0, text="Done!")
    time.sleep(0.3)
    progress.empty()

    if "error" in result_holder:
        raise result_holder["error"]
    return result_holder["output"]


def render_study_tab(api_key: str, subject: str, workspace: dict, mode: str) -> None:
    wid = workspace.get("id", subject)

    if st.button("Generate Study Guide", type="primary"):
        if not api_key:
            st.warning("⚙ Enter your Gemini API key in Settings to generate a study guide.")
        elif not workspace["files"]:
            st.warning("Add material in the Ingest Material tab first.")
        else:
            try:
                output = _generate_with_progress(api_key, subject, workspace, mode)
                workspace["generated_notes"] = output
                st.session_state["is_dirty"] = True
                _save_guide(subject, workspace["generated_notes"], f"{mode} Guide")
            except Exception as exc:
                logger.error("Study guide generation failed: %s", exc, exc_info=True)
                st.error("Study guide generation failed. Check your API key and try again.")

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
        render_guide(workspace["generated_notes"])
    else:
        st.caption("Generate a study guide after indexing material.")

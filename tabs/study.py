import datetime
import hashlib
import logging
import time

import streamlit as st

from utils.gemini import call_gemini
from utils.guide import guide_prompt, render_guide
from utils.metrics import report_generation_metrics

logger = logging.getLogger(__name__)

_PROGRESS_STEPS = [
    (0.05, "Reading your materials…"),
    (0.20, "Identifying key topics…"),
    (0.40, "Writing explanations and examples…"),
    (0.65, "Building practice problems…"),
    (0.85, "Adding worked answers…"),
    (0.95, "Formatting your guide…"),
]


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


def _generate_with_progress(api_key: str, prompt: str, workspace: dict) -> str:
    progress = st.progress(0.0, text=_PROGRESS_STEPS[0][1])
    status_box = st.empty()
    result_holder: dict = {}
    username = st.session_state.get("username", "anonymous")

    import threading

    def _run():
        try:
            result_holder["output"] = call_gemini(
                api_key, prompt, workspace, metric_label="study_guide_generation",
                username=username,
            )
        except Exception as exc:
            result_holder["error"] = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    step_idx = 0
    t0 = time.perf_counter()

    while thread.is_alive():
        elapsed = time.perf_counter() - t0
        fraction = min(elapsed / 45.0, 0.94)   # calibrated to ~45s max
        while step_idx < len(_PROGRESS_STEPS) - 1 and fraction >= _PROGRESS_STEPS[step_idx + 1][0]:
            step_idx += 1
        pct, msg = _PROGRESS_STEPS[step_idx]
        progress.progress(max(fraction, pct), text=msg)
        time.sleep(0.4)

    thread.join()
    progress.progress(1.0, text="Done!")
    time.sleep(0.3)
    progress.empty()
    status_box.empty()

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
                t_start = time.perf_counter()
                has_images = any(f.get("images") for f in workspace.get("files", []))
                _prompt = guide_prompt(subject, workspace, mode, has_images=has_images)
                output = _generate_with_progress(api_key, _prompt, workspace)
                workspace["generated_notes"] = output
                st.session_state["is_dirty"] = True
                ttv = round(time.perf_counter() - t_start, 2)

                _save_guide(subject, workspace["generated_notes"], f"{mode} Guide")

                report_generation_metrics(
                    label=f"Study Guide ({mode})",
                    subject=subject,
                    mode=mode,
                    prompt_text=_prompt,
                    output_text=workspace["generated_notes"],
                    elapsed_s=ttv,
                )
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

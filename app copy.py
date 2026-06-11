import hashlib
import os

import streamlit as st

from utils.files import blank_workspace
from utils.guide import render_guide
from utils.metrics import METRICS_REPORT

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

        .stApp { background: var(--bg); color: var(--ink); }
        .main .block-container { max-width: 1360px; padding-top: 2rem; }

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

        [data-testid="stFileUploader"] button,
        [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stFileUploaderDropzoneInstructions"] small,
        [data-testid="stFileUploaderDropzoneInstructions"] p {
            color: #2D2D2D !important;
        }
        [data-testid="stFileUploader"] [data-testid="baseButton-secondary"] {
            background: #FFFFFF !important;
            border: 1.5px solid #8C1D40 !important;
            color: #8C1D40 !important;
            font-weight: 700 !important;
        }
        [data-testid="stFileUploader"] [data-testid="baseButton-secondary"] span,
        [data-testid="stFileUploader"] [data-testid="baseButton-secondary"] p {
            color: #8C1D40 !important;
        }

        input, textarea,
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

        .stFileUploader,
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
        </style>
        """,
        unsafe_allow_html=True,  # safe: only hardcoded CSS, no user-generated content
    )


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def initialize_state() -> None:
    st.session_state.setdefault("workspaces", {"CSE 230": blank_workspace()})
    st.session_state.setdefault("active_workspace", next(iter(st.session_state["workspaces"])))
    st.session_state.setdefault("saved_guides", [])
    st.session_state.setdefault("viewing_guide", None)


def active_workspace() -> dict:
    return st.session_state["workspaces"][st.session_state["active_workspace"]]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_workspace_sidebar() -> tuple[str, str, str]:
    with st.sidebar:
        st.header("Workspace")
        new_subject = st.text_input("New Subject Name", placeholder="CSE 230, Physics, MAT 243")
        if st.button("Create Workspace", type="primary", use_container_width=True):
            subject = new_subject.strip()
            if subject:
                st.session_state["workspaces"].setdefault(subject, blank_workspace())
                st.session_state["active_workspace"] = subject
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
                del st.session_state["workspaces"][selected]
                st.session_state["active_workspace"] = next(iter(st.session_state["workspaces"]))
                st.rerun()

        st.divider()
        with st.expander("⚙ Settings"):
            # API key is blank by default — never pre-filled from env (security fix)
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
            for idx, guide in enumerate(saved):
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    btn_label = f"{guide['title']}  •  {guide['saved_at']}"
                    if st.button(btn_label, key=f"open_guide_{idx}", use_container_width=True):
                        st.session_state["viewing_guide"] = idx
                        st.rerun()
                with col_del:
                    if st.button("✕", key=f"del_guide_{idx}", help="Remove"):
                        st.session_state["saved_guides"].pop(idx)
                        if st.session_state.get("viewing_guide") == idx:
                            st.session_state["viewing_guide"] = None
                        st.rerun()

        # ── Metrics download ──────────────────────────────────────────────
        st.divider()
        st.markdown("**📊 Metrics**")
        if METRICS_REPORT.exists() and METRICS_REPORT.stat().st_size > 0:
            st.download_button(
                "⬇ Download Metrics Report",
                data=METRICS_REPORT.read_bytes(),
                file_name="sundevil_ai_metrics.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.caption(f"{METRICS_REPORT.stat().st_size // 1024 + 1} KB logged")
        else:
            st.caption("No metrics yet — generate a guide or upload a file.")

    return selected, api_key, study_mode


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
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=":books:", layout="wide")
    initialize_state()
    apply_theme()

    subject, api_key, study_mode = render_workspace_sidebar()

    # Guide viewer page
    viewing_idx = st.session_state.get("viewing_guide")
    if viewing_idx is not None:
        saved = st.session_state.get("saved_guides", [])
        if 0 <= viewing_idx < len(saved):
            render_guide_viewer(saved[viewing_idx])
            return
        else:
            st.session_state["viewing_guide"] = None

    # Normal workspace page
    workspace = active_workspace()

    st.title(APP_TITLE)
    st.caption("Warm, focused study workspaces for ASU computer science courses.")
    st.subheader(subject)

    ingest_tab, guide_tab, quiz_tab = st.tabs(["Ingest Material", "Study Guide", "Interactive Quiz"])

    from tabs.ingest import render_ingest_tab
    from tabs.study import render_study_tab
    from tabs.quiz import render_quiz_tab

    with ingest_tab:
        render_ingest_tab(subject, workspace, api_key)
    with guide_tab:
        render_study_tab(api_key, subject, workspace, study_mode)
    with quiz_tab:
        render_quiz_tab(api_key, subject, workspace)


if __name__ == "__main__":
    main()

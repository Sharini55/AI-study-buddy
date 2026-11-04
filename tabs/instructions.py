"""
tabs/instructions.py
────────────────────
Renders the AI Study Buddy tutorial slideshow.

The HTML is self-contained (all screenshots embedded as base64 data URIs)
so no extra static-file serving is needed on Azure App Service.
"""
import os


def _load_html() -> str:
    """Load the tutorial HTML from the same directory as this file."""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instructions.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


def render_instructions_tab() -> None:
    """Full-page How to Use view — shown on first login and via sidebar nav."""
    import streamlit as st
    import streamlit.components.v1 as components

    if st.button("← Back", key="_instructions_back"):
        st.session_state["current_page"] = "Dashboard"
        st.rerun()

    st.markdown(
        "<h2 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
        "color:#242B18;margin-bottom:0.1rem;'>"
        "<i class='ti ti-info-circle' style='color:#D9A441;margin-right:8px;'></i>"
        "How to Use</h2>"
        "<p style='color:#5C6A48;font-family:\"Truculenta\",sans-serif;"
        "font-size:0.95rem;margin-top:0;'>A quick walkthrough of AI Study Buddy</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    html = _load_html()
    components.html(html, height=680, scrolling=False)

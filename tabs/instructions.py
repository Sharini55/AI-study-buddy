"""
tabs/instructions.py
────────────────────
Renders the AI Study Buddy tutorial popup.

The HTML is self-contained (all 8 app screenshots embedded as base64 data
URIs) so it works with no extra static-file serving on Azure App Service.

Call render_instructions_tab() from app.py to show it as a full page, or
call show_tutorial_popup() to inject it as an overlay on any page.
"""
import streamlit as st
import streamlit.components.v1 as components
import os


def _load_html() -> str:
    """Load the tutorial HTML from the same directory as this file."""
    html_path = os.path.join(os.path.dirname(__file__), "instructions.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


def render_instructions_tab() -> None:
    """Full-page How to Use view — navigate here from the sidebar."""
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
    # Render at a fixed height that fits the slideshow card; scrolling is
    # handled inside the iframe by the slideshow itself.
    components.html(html, height=680, scrolling=False)


def show_tutorial_popup() -> None:
    """
    Inject the tutorial as an auto-opening modal overlay on the current page.

    Call this once early in main() when tutorial_seen is False.  The HTML
    already auto-opens the modal on load, so just rendering it is enough.
    After the user closes it the session-state flag is set by a Streamlit
    button below the hidden component, which triggers a rerun.
    """
    html = _load_html()
    # Height 0 + hidden container: the modal is position:fixed in the HTML
    # so it floats above everything regardless of its iframe size.
    components.html(html, height=0, scrolling=False)

    # Provide a hidden Streamlit button that JS inside the iframe can
    # trigger via a postMessage → parent click relay (see below).
    # For simplicity we just show a small "Skip tutorial" link so users
    # on first visit can dismiss and mark it seen.
    st.markdown(
        """
        <style>
        #_tut_dismiss_wrap { display:none; }
        </style>
        <div id="_tut_dismiss_wrap">
        """,
        unsafe_allow_html=True,
    )
    if st.button("Mark tutorial seen", key="_tut_dismiss_btn"):
        st.session_state["tutorial_seen"] = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

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
        /* ── Icon fonts ── */
        @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css');
        @import url('https://fonts.googleapis.com/css2?family=Truculenta:opsz,wght@12..72,100..900&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=swap');

        /* ── Design tokens ── */
        :root {
            --bg:          #F5F8EE;   /* warm green-tinted page canvas  */
            --sidebar:     #ECF1E2;   /* slightly deeper green for sidebar */
            --panel:       #FFFFFF;
            --ink:         #242B18;   /* very dark green-black for max contrast */
            --muted:       #5C6A48;
            --line:        #C5D99A;   /* soft green rule / border */
            --green:       #ABC270;   /* primary accent — bounding, badges, active states */
            --green-dark:  #8BA552;   /* hover for green elements */
            --yellow:      #D9A441;   /* primary CTA buttons, active nav */
            --orange:      #C18A2A;   /* hover state for yellow elements */
            --green-glow:  rgba(171, 194, 112, 0.22);
        }

        /* ── Typography — Truculenta across all text-bearing elements ── */
        html, body, .stApp,
        h1, h2, h3, h4, h5, h6,
        p, label, span, button, input, textarea, select,
        [data-testid="stSidebar"] *,
        [data-testid="stTabs"] button[role="tab"],
        [data-testid="stMetricLabel"] label,
        [data-testid="stMetricValue"],
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            font-family: 'Truculenta', sans-serif !important;
        }
        span[data-testid="stIconMaterial"],
        [data-testid="stTextInput"] button span[data-testid="stIconMaterial"],
        div[data-baseweb="input"] button span[data-testid="stIconMaterial"] {
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
            font-size: 20px !important;
            font-weight: 400 !important;
            line-height: 1 !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            white-space: nowrap !important;
            word-wrap: normal !important;
            direction: ltr !important;
            color: var(--ink) !important;
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24 !important;
        }

        /* ── Strip Streamlit chrome ── */
        header[data-testid="stHeader"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        /* DO NOT hide stToolbar — stExpandSidebarButton lives inside it.
           Hiding the toolbar hides the expand button, making the sidebar
           permanently unrecoverable once collapsed. */
        [data-testid="stToolbar"] {
            background: transparent !important;
            box-shadow: none !important;
        }
        /* Hide only the specific sub-elements we don't want */
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stToolbarActionButtonTooltip"],
        #MainMenu,
        footer { display: none !important; }

        /* ── Page canvas — force pastel even when OS is in dark mode ── */
        html, body { background: var(--bg) !important; color: var(--ink) !important; }
        .stApp    { background: var(--bg) !important; color: var(--ink) !important; }
        .main .block-container { max-width: 1360px; padding-top: 1rem; }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: var(--sidebar) !important;
            border-right: 2px solid var(--line) !important;
        }
        [data-testid="stSidebar"] * { color: var(--ink) !important; letter-spacing: 0; }

        /* Sidebar secondary buttons — transparent nav items (inactive) */
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
        [data-testid="stSidebar"] [data-testid="baseButton-secondary"] {
            background:       transparent !important;
            border:           none !important;
            border-radius:    10px !important;
            justify-content:  flex-start !important;
            font-weight:      400 !important;
            color:            var(--ink) !important;
            padding:          8px 12px !important;
            font-family:      'Truculenta', sans-serif !important;
            transition:       background 0.12s;
        }
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover,
        [data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover {
            background: rgba(217,164,65,0.15) !important;
        }
        /* Sidebar primary buttons — active nav (dark gold + white text) */
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
        [data-testid="stSidebar"] [data-testid="baseButton-primary"] {
            background:       var(--yellow) !important;
            border:           none !important;
            border-radius:    10px !important;
            justify-content:  flex-start !important;
            font-weight:      700 !important;
            color:            #FFFFFF !important;
            padding:          8px 12px !important;
            font-family:      'Truculenta', sans-serif !important;
        }
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover,
        [data-testid="stSidebar"] [data-testid="baseButton-primary"]:hover {
            background: var(--orange) !important;
        }
        /* Primary text: white; secondary text: ink */
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p,
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] span { color: #FFFFFF !important; }
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] p,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] span { color: var(--ink) !important; }

        /* Active workspace: subtle green tint via marker sibling */
        [data-testid="stSidebar"] div:has(.ws-active-marker) + div [data-testid="stBaseButton-secondary"],
        [data-testid="stSidebar"] div:has(.ws-active-marker) + div [data-testid="baseButton-secondary"] {
            background:  rgba(171,194,112,0.28) !important;
            border:      1.5px solid var(--green) !important;
            font-weight: 600 !important;
        }

        /* Study mode segmented toggle: joined pills */
        [data-testid="stSidebar"] button.mode-btn-left {
            border-radius: 999px 0 0 999px !important;
            border-right:  none !important;
        }
        [data-testid="stSidebar"] button.mode-btn-right {
            border-radius: 0 999px 999px 0 !important;
            border-left:   none !important;
        }
        [data-testid="stSidebar"] button.mode-btn-left,
        [data-testid="stSidebar"] button.mode-btn-right {
            border: 1.5px solid rgba(217,164,65,0.4) !important;
        }
        [data-testid="stSidebar"] button.mode-btn-left[data-testid="stBaseButton-primary"],
        [data-testid="stSidebar"] button.mode-btn-right[data-testid="stBaseButton-primary"] {
            background: var(--ink) !important;
            color:      #FFFFFF !important;
            border:     1.5px solid var(--ink) !important;
        }
        [data-testid="stSidebar"] button.mode-btn-left[data-testid="stBaseButton-primary"] p,
        [data-testid="stSidebar"] button.mode-btn-right[data-testid="stBaseButton-primary"] p,
        [data-testid="stSidebar"] button.mode-btn-left[data-testid="stBaseButton-primary"] span,
        [data-testid="stSidebar"] button.mode-btn-right[data-testid="stBaseButton-primary"] span {
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] button.mode-btn-left[data-testid="stBaseButton-secondary"],
        [data-testid="stSidebar"] button.mode-btn-right[data-testid="stBaseButton-secondary"] {
            background: transparent !important;
            color:      var(--muted) !important;
        }

        /* Sidebar footer text-link buttons */
        [data-testid="stSidebar"] button.sb-footer-link {
            background:      transparent !important;
            border:          none !important;
            border-radius:   6px !important;
            font-size:       0.78rem !important;
            font-weight:     400 !important;
            color:           var(--muted) !important;
            padding:         4px 8px !important;
            height:          auto !important;
            min-height:      0 !important;
            text-decoration: underline !important;
            justify-content: flex-start !important;
        }
        [data-testid="stSidebar"] button.sb-footer-link p,
        [data-testid="stSidebar"] button.sb-footer-link span { color: var(--muted) !important; }
        [data-testid="stSidebar"] button.sb-footer-link:hover {
            color: var(--ink) !important;
            background: transparent !important;
        }
        [data-testid="stSidebar"] button.sb-footer-link:hover p,
        [data-testid="stSidebar"] button.sb-footer-link:hover span { color: var(--ink) !important; }

        /* ── Headings ── */
        h1, h2, h3, h4, h5, h6 {
            color: var(--ink) !important;
            font-family: 'Truculenta', sans-serif !important;
            letter-spacing: -0.3px;
        }

        /* ── Main workspace tabs — green active, clean inactive ── */
        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 999px;
            padding: 10px 20px;
            color: var(--ink) !important;
            font-family: 'Truculenta', sans-serif !important;
            font-weight: 600;
            transition: background 0.15s;
        }
        div[data-testid="stTabs"] button[role="tab"] p,
        div[data-testid="stTabs"] button[role="tab"] span {
            color: var(--ink) !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: var(--green) !important;
            border: none !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] p,
        div[data-testid="stTabs"] button[aria-selected="true"] span { color: #FFFFFF !important; }
        div[data-testid="stTabs"] button[aria-selected="false"]:hover {
            background: #DFE9C8 !important;
        }
        div[data-testid="stTabs"] button[aria-selected="false"],
        div[data-testid="stTabs"] button[aria-selected="false"] p,
        div[data-testid="stTabs"] button[aria-selected="false"] span {
            color: var(--ink) !important;
        }

        /* ── All non-sidebar buttons — secondary (white) ── */
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 999px;
            border: 1.5px solid var(--line);
            background: #FFFFFF !important;
            color: var(--ink) !important;
            font-weight: 600;
            font-family: 'Truculenta', sans-serif !important;
            transition: background 0.15s, border-color 0.15s;
        }
        .stButton > button *,
        .stButton > button p,
        .stButton > button span,
        .stDownloadButton > button *,
        .stDownloadButton > button p,
        .stDownloadButton > button span { color: var(--ink) !important; }
        .stButton > button:hover {
            background: #E8F0D5 !important;
            border-color: var(--green) !important;
        }

        /* Primary buttons — yellow fill, orange hover */
        .stButton > button[kind="primary"],
        .stDownloadButton > button {
            background: var(--yellow) !important;
            border-color: var(--yellow) !important;
            color: var(--ink) !important;
            font-weight: 700;
        }
        .stButton > button[kind="primary"] *,
        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span,
        .stDownloadButton > button *,
        .stDownloadButton > button p,
        .stDownloadButton > button span { color: var(--ink) !important; }
        .stButton > button[kind="primary"]:hover,
        .stDownloadButton > button:hover {
            background: var(--orange) !important;
            border-color: var(--orange) !important;
        }

        /* testid overrides that survive Streamlit's dark-theme injection */
        [data-testid="baseButton-primary"],
        [data-testid="stBaseButton-primary"] {
            background: var(--yellow) !important;
            border-color: var(--yellow) !important;
            color: var(--ink) !important;
            font-family: 'Truculenta', sans-serif !important;
        }
        [data-testid="baseButton-primary"] p,
        [data-testid="baseButton-primary"] span,
        [data-testid="stBaseButton-primary"] p,
        [data-testid="stBaseButton-primary"] span { color: var(--ink) !important; }

        /* Tabler icon alignment inside nav buttons */
        [data-testid="stSidebar"] button .ti {
            font-size: 1rem;
            margin-right: 7px;
            vertical-align: middle;
            line-height: 1;
        }
        [data-testid="baseButton-secondary"],
        [data-testid="stBaseButton-secondary"] {
            background: #FFFFFF !important;
            color: var(--ink) !important;
            font-family: 'Truculenta', sans-serif !important;
        }
        [data-testid="baseButton-secondary"] p,
        [data-testid="baseButton-secondary"] span,
        [data-testid="stBaseButton-secondary"] p,
        [data-testid="stBaseButton-secondary"] span { color: var(--ink) !important; }

        /* Re-apply sidebar contrast after the global button overrides above. */
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
        [data-testid="stSidebar"] [data-testid="baseButton-primary"] {
            background: #8C1D40 !important;
            border-color: #8C1D40 !important;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] *,
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p,
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] span,
        [data-testid="stSidebar"] [data-testid="baseButton-primary"] *,
        [data-testid="stSidebar"] [data-testid="baseButton-primary"] p,
        [data-testid="stSidebar"] [data-testid="baseButton-primary"] span {
            color: #FFFFFF !important;
        }

        /* ── File uploader ── */
        [data-testid="stFileUploader"] {
            background: #FFFFFF !important;
            border: 2.5px dashed var(--green) !important;
            border-radius: 18px !important;
            padding: 0.75rem 1rem !important;
        }
        [data-testid="stFileUploader"] label {
            color: var(--ink) !important;
            line-height: 1.5 !important;
            margin-bottom: 0.5rem !important;
            padding-top: 0 !important;
            font-family: 'Truculenta', sans-serif !important;
        }
        [data-testid="stFileUploaderDropzone"] { background: #FFFFFF !important; }
        [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stFileUploaderDropzoneInstructions"] small,
        [data-testid="stFileUploaderDropzoneInstructions"] p,
        [data-testid="stFileUploader"] small { color: var(--muted) !important; }

        /* Browse / Upload button */
        [data-testid="stFileUploaderDropzone"] button {
            position: relative !important;
            background: var(--yellow) !important;
            border: none !important;
            border-radius: 999px !important;
            padding: 6px 28px !important;
            min-width: 90px !important;
            min-height: 36px !important;
            cursor: pointer !important;
        }
        [data-testid="stFileUploaderDropzone"] button span,
        [data-testid="stFileUploaderDropzone"] button p,
        [data-testid="stFileUploaderDropzone"] button div,
        [data-testid="stFileUploaderDropzone"] button svg {
            font-size: 0 !important;
            color:     transparent !important;
            fill:      transparent !important;
            width:     0 !important;
            height:    0 !important;
            overflow:  hidden !important;
            display:   inline-block !important;
        }
        [data-testid="stFileUploaderDropzone"] button::after {
            content:      "Upload" !important;
            position:     absolute !important;
            inset:        0 !important;
            display:      flex !important;
            align-items:  center !important;
            justify-content: center !important;
            font-size:    1rem !important;
            font-weight:  600 !important;
            font-family:  'Truculenta', sans-serif !important;
            color:        var(--ink) !important;
            pointer-events: none !important;
        }

        /* ── Input fields — green focus ring ── */
        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            color: var(--ink) !important;
            caret-color: var(--green) !important;
            background: #FFFFFF !important;
            border-color: var(--line) !important;
            border-radius: 10px !important;
            font-family: 'Truculenta', sans-serif !important;
        }
        div[data-baseweb="input"] input:focus,
        [data-testid="stTextInput"] input:focus {
            border-color: var(--green) !important;
            box-shadow: 0 0 0 3px var(--green-glow) !important;
            outline: none !important;
        }
        div[data-baseweb="textarea"] textarea:focus,
        [data-testid="stTextArea"] textarea:focus {
            border-color: var(--green) !important;
            box-shadow: 0 0 0 3px var(--green-glow) !important;
            outline: none !important;
        }
        input::placeholder,
        textarea::placeholder,
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: var(--muted) !important;
            opacity: 1 !important;
        }

        /* ── Cards: metrics, expanders, text areas ── */
        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1.5px solid var(--line);
            border-radius: 16px;
            padding: 1rem 1.25rem;
        }
        div[data-testid="stExpander"] {
            background: var(--panel) !important;
            border: 1.5px solid var(--line) !important;
            border-radius: 16px !important;
            border-left: 4px solid var(--green) !important;
        }
        div[data-testid="stExpander"] summary {
            font-family: 'Truculenta', sans-serif !important;
            font-weight: 600;
            color: var(--ink) !important;
        }
        div[data-testid="stTextArea"] {
            background: var(--panel);
            border-radius: 14px;
        }
        div[data-testid="stTextArea"] textarea {
            border: 2px solid var(--line);
            border-radius: 14px;
            background: #FFFFFF;
            color: var(--ink);
        }

        /* ── Login form card ── */
        [data-testid="stForm"] {
            background: #FFFFFF;
            border: 1.5px solid var(--line);
            border-radius: 18px;
            padding: 1.5rem 1.5rem 0.5rem;
        }

        /* ── Form labels — force dark so they're visible on white form bg ── */
        [data-testid="stForm"] label,
        [data-testid="stForm"] [data-testid="stWidgetLabel"],
        [data-testid="stForm"] [data-testid="stWidgetLabel"] p,
        [data-testid="stForm"] [data-testid="stWidgetLabel"] label {
            color: var(--ink) !important;
        }

        /* ── Form submit buttons — green fill, white text ── */
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"],
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"],
        [data-testid="stFormSubmitButton"] button {
            background: #8C1D40 !important;
            border-color: #8C1D40 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border-radius: 999px !important;
        }
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] *,
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] p,
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] span,
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"] *,
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"] p,
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"] span,
        [data-testid="stFormSubmitButton"] button *,
        [data-testid="stFormSubmitButton"] button p,
        [data-testid="stFormSubmitButton"] button span {
            color: #FFFFFF !important;
        }
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"]:hover,
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"]:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            background: #6E1532 !important;
            border-color: #6E1532 !important;
        }

        /* ── Metric cards — force dark text (profile/settings page) ── */
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] label,
        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] div,
        [data-testid="stMetricDelta"] { color: var(--ink) !important; }

        /* ── Alert components — force high-contrast text regardless of bg colour ── */
        div[data-testid="stAlert"] {
            border-radius: 14px !important;
            font-family: 'Truculenta', sans-serif !important;
        }
        div[data-testid="stAlert"],
        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] span,
        div[data-testid="stAlert"] li,
        div[data-testid="stAlert"] a,
        div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
            color: var(--ink) !important;
        }

        /* Dashboard/history text should remain readable on the light workspace. */
        .main [data-testid="stMarkdownContainer"],
        .main [data-testid="stMarkdownContainer"] p,
        .main [data-testid="stMarkdownContainer"] span,
        .main [data-testid="stMarkdownContainer"] li,
        .main [data-testid="stCaptionContainer"],
        .main [data-testid="stCaptionContainer"] *,
        .main label,
        .main label p {
            color: var(--ink) !important;
        }

        /* ── Progress bar — green fill ── */
        div[role="progressbar"] > div,
        .stProgress > div > div > div > div {
            background-color: var(--green) !important;
            border-radius: 999px;
        }

        /* ── Selectbox / dropdown ── */
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background: #FFFFFF !important;
            border-color: var(--line) !important;
            border-radius: 10px !important;
            font-family: 'Truculenta', sans-serif !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
            border-color: var(--green) !important;
            box-shadow: 0 0 0 3px var(--green-glow) !important;
        }

        /* ── Radio buttons — green accent ── */
        [data-baseweb="radio"] > div:first-child {
            border-color: var(--green) !important;
        }
        [data-baseweb="radio"] > div:first-child[aria-checked="true"] {
            background: var(--green) !important;
            border-color: var(--green) !important;
        }

        /* ── Checkboxes — green accent ── */
        [data-baseweb="checkbox"] [role="checkbox"] {
            border-color: var(--green) !important;
        }
        [data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] {
            background: var(--green) !important;
            border-color: var(--green) !important;
        }

        /* ── Sidebar section label helper ── */
        .sb-section-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: var(--muted) !important;
            letter-spacing: 1.6px;
            text-transform: uppercase;
            font-family: 'Truculenta', sans-serif;
            margin: 14px 0 4px;
            padding-left: 2px;
        }

        /* ── Dataframe table ── */
        [data-testid="stDataFrame"] {
            border: 1.5px solid var(--line) !important;
            border-radius: 14px !important;
            overflow: hidden;
        }
        [data-testid="stDataFrame"] th {
            background: var(--sidebar) !important;
            color: var(--ink) !important;
            font-family: 'Truculenta', sans-serif !important;
            font-weight: 700;
        }

        /* ── Divider ── */
        hr { border-color: var(--line) !important; opacity: 1; }

        /* ── pre / code ── */
        pre, pre * { color: var(--ink) !important; background: transparent !important; }
        code:not([class]) {
            background: #E3EED0 !important;
            color: #2A450A !important;
            border-radius: 5px !important;
            padding: 1px 5px !important;
            font-family: 'Truculenta', monospace !important;
        }

        /* ── Spinner ── */
        [data-testid="stSpinner"] > div {
            border-top-color: var(--green) !important;
        }

        /* ── Sidebar collapse button ── */
        [data-testid="stSidebarCollapseButton"] button {
            position: relative !important;
            width:         42px !important;
            height:        42px !important;
            min-width:     42px !important;
            min-height:    42px !important;
            line-height:   42px !important;
            padding:       0 !important;
            background:    #FFFFFF !important;
            border:        1.5px solid var(--ink) !important;
            border-radius: 999px !important;
            cursor:        pointer !important;
            overflow:      hidden !important;
        }
        [data-testid="stSidebarCollapseButton"] button svg,
        [data-testid="stSidebarCollapseButton"] button span,
        [data-testid="stSidebarCollapseButton"] button p,
        [data-testid="stSidebarCollapseButton"] button div {
            color:      transparent !important;
            fill:       transparent !important;
            opacity:    0 !important;
            user-select: none !important;
        }
        [data-testid="stSidebarCollapseButton"] button::after {
            content:    "«";
            position:   absolute !important;
            inset:      0 !important;
            display:    flex !important;
            align-items:     center !important;
            justify-content: center !important;
            font-size:  1.35rem !important;
            font-weight: 700 !important;
            color:      #000000 !important;
            pointer-events: none !important;
        }

        /* ── Sidebar expand button ── */
        [data-testid="stExpandSidebarButton"] button {
            position: relative !important;
            width:         42px !important;
            height:        42px !important;
            min-width:     42px !important;
            min-height:    42px !important;
            line-height:   42px !important;
            padding:       0 !important;
            background:    #FFFFFF !important;
            border:        1.5px solid var(--ink) !important;
            border-radius: 0 10px 10px 0 !important;
            cursor:        pointer !important;
            overflow:      hidden !important;
        }
        [data-testid="stExpandSidebarButton"] button svg,
        [data-testid="stExpandSidebarButton"] button span,
        [data-testid="stExpandSidebarButton"] button p,
        [data-testid="stExpandSidebarButton"] button div {
            color:      transparent !important;
            fill:       transparent !important;
            opacity:    0 !important;
            user-select: none !important;
        }
        [data-testid="stExpandSidebarButton"] button::after {
            content:    "»";
            position:   absolute !important;
            inset:      0 !important;
            display:    flex !important;
            align-items:     center !important;
            justify-content: center !important;
            font-size:  1.35rem !important;
            font-weight: 700 !important;
            color:      #000000 !important;
            pointer-events: none !important;
        }

        section[data-testid="stSidebar"] {
            min-width: 0 !important;
        }

        /* ── Study guide expanders ── */
        details > summary { list-style: none !important; }
        details > summary::-webkit-details-marker { display: none !important; }

        div[data-testid="stExpander"] {
            background:    var(--panel) !important;
            border:        1.5px solid var(--line) !important;
            border-radius: 14px !important;
            border-left:   4px solid var(--green) !important;
            margin-bottom: 0.5rem !important;
        }

        div[data-testid="stExpander"] details summary {
            background:    var(--sidebar) !important;
            border-radius: 10px !important;
            padding:       0.6rem 1rem !important;
            cursor:        pointer !important;
        }
        div[data-testid="stExpander"] details[open] > summary {
            border-radius:  10px 10px 0 0 !important;
            border-bottom:  1px solid var(--line) !important;
        }

        div[data-testid="stExpander"] details summary [data-testid="stIconMaterial"],
        div[data-testid="stExpander"] details summary svg { display: none !important; }

        div[data-testid="stExpander"] details summary::before {
            content:        "›";
            font-size:      1.3rem;
            font-weight:    700;
            color:          var(--green);
            margin-right:   8px;
            display:        inline-block;
            transition:     transform 0.15s;
            vertical-align: middle;
            line-height:    1;
        }
        div[data-testid="stExpander"] details[open] > summary::before {
            transform: rotate(90deg);
        }

        div[data-testid="stExpander"] details > div {
            padding: 0.75rem 1rem !important;
        }

        /* ── Final accessibility overrides ── */
        /* These prevent Streamlit's dark mode properties from accidentally flipping text colors */
        .main p, .main span, .main label, .main h1, .main h2, .main h3 {
            color: var(--ink) !important;
            opacity: 1 !important;
        }

        /* 🔧 FIXED: Ensure tab navigation labels inside the authentication menu stay clear */
        [data-testid="stTabs"] [role="tablist"] button p {
            color: inherit !important;
        }
        
        /* Smooth transitions for inputs */
        input, textarea, select {
            transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
        }

        [data-testid="stFileUploaderDropzone"],
        [data-testid="stFileUploaderDropzone"] *,
        [data-testid="stFileUploader"] label,
        [data-testid="stFileUploader"] label *,
        [data-testid="stFileUploader"] small {
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] input,
        div[data-baseweb="input"] input,
        [data-testid="stTextArea"] textarea,
        div[data-baseweb="textarea"] textarea {
            color: var(--ink) !important;
            -webkit-text-fill-color: var(--ink) !important;
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] button,
        div[data-baseweb="input"] button {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            color: transparent !important;
            min-width: 2.25rem !important;
            overflow: hidden !important;
            position: relative !important;
        }

        [data-testid="stTextInput"] button *,
        div[data-baseweb="input"] button * {
            color: transparent !important;
            -webkit-text-fill-color: transparent !important;
            opacity: 0 !important;
            font-size: 0 !important;
        }

        [data-testid="stTextInput"] button::after,
        div[data-baseweb="input"] button::after {
            content: "○" !important;
            position: absolute !important;
            inset: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            color: var(--ink) !important;
            -webkit-text-fill-color: var(--ink) !important;
            opacity: 1 !important;
            font-size: 1.05rem !important;
            font-family: Arial, sans-serif !important;
            font-weight: 700 !important;
            pointer-events: none !important;
        }

        .main .block-container h1,
        .main .block-container h1 *,
        .main .block-container h2,
        .main .block-container h2 * {
            color: var(--ink) !important;
            opacity: 1 !important;
        }
        </style>

        <script>
        (function() {
            var NAV_ICONS = {
                'Dashboard':    'ti-layout-dashboard',
                'Study guide':  'ti-book',
                'Quiz':         'ti-help-circle',
                'Saved Guides': 'ti-bookmark',
            };

            function initSidebar() {
                var sidebar = document.querySelector('[data-testid="stSidebar"]');
                if (!sidebar) return;

                sidebar.querySelectorAll('button').forEach(function(btn) {
                    var p = btn.querySelector('p');
                    if (!p) return;
                    var txt = p.textContent.trim();
                    var iconCls = NAV_ICONS[txt];
                    if (iconCls && !p.querySelector('i.ti')) {
                        var i = document.createElement('i');
                        i.className = 'ti ' + iconCls;
                        p.insertBefore(document.createTextNode(' '), p.firstChild);
                        p.insertBefore(i, p.firstChild);
                    }
                });
            }

            var _amo = new MutationObserver(initSidebar);
            _amo.observe(document.body, {childList: true, subtree: true});
            setTimeout(initSidebar, 400);
        })();
        </script>

        <script>
        (function() {
            function restoreApiKey() {
                var kInput = document.querySelector('[data-testid="stTextInput"] input[type="password"]');
                if (!kInput) return;
                var saved = localStorage.getItem('_gemini_cached_api_key');
                if (saved && !kInput.value) {
                    kInput.value = saved;
                    kInput.dispatchEvent(new Event('input', { bubbles: true }));
                    var btn = kInput.closest('form')?.querySelector('button[type="submit"]') || 
                              document.querySelector('[data-testid="stFormSubmitButton"] button');
                    if (btn) {
                        setTimeout(function() { btn.click(); }, 150);
                    }
                }
            }
            var _amo = new MutationObserver(restoreApiKey);
            _amo.observe(document.body, {childList: true, subtree: true});
            setTimeout(restoreApiKey, 500);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# DATA SYNCING: Read/Write Streamlit Workspaces dynamically to SQLite
# ---------------------------------------------------------------------------

def load_user_workspaces_from_db(username: str) -> tuple[dict, list]:
    db: Session = SessionLocal()
    workspaces_dict = {}
    saved_guides: list = []
    try:
        user_record = db.query(User).filter(User.username == username).first()
        if user_record:
            for ws in user_record.workspaces:
                ws_data = blank_workspace()
                ws_data["id"] = ws.id
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

                for quiz_row in ws.quizzes:
                    try:
                        questions = json.loads(quiz_row.quiz_json)
                        answers = json.loads(quiz_row.answers_json)
                        missed = [
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
    db: Session = SessionLocal()
    try:
        ws_row = db.query(Workspace).filter(
            Workspace.user_id == username,
            Workspace.subject_name == subject_name
        ).first()
        if not ws_row:
            ws_row = Workspace(user_id=username, subject_name=subject_name)
            db.add(ws_row)
            db.commit()
            db.refresh(ws_row)

        ws_memory["id"] = ws_row.id

        current_file_ids = []
        for f in ws_memory.get("files", []):
            f_row = None
            if f.get("id"):
                f_row = db.query(SourceFile).filter(SourceFile.id == f["id"]).first()
            
            if not f_row:
                f_row = SourceFile(
                    workspace_id=ws_row.id,
                    name=f["name"],
                    file_type=f["type"],
                    content_text=f["content"]
                )
                db.add(f_row)
                db.commit()
                db.refresh(f_row)
                f["id"] = f_row.id
            else:
                f_row.name = f["name"]
                f_row.file_type = f["type"]
                f_row.content_text = f["content"]
                db.commit()

            current_file_ids.append(f_row.id)

            current_img_labels = []
            for img in f.get("images", []):
                img_row = db.query(SourceImage).filter(
                    SourceImage.file_id == f_row.id,
                    SourceImage.label == img["label"]
                ).first()
                
                if not img_row:
                    local_path = save_uploaded_image_locally(username, img["bytes"], img["label"])
                    img_row = SourceImage(
                        file_id=f_row.id,
                        label=img["label"],
                        storage_path=local_path,
                        mime_type=img["mime_type"]
                    )
                    db.add(img_row)
                current_img_labels.append(img["label"])
            
            db.query(SourceImage).filter(
                SourceImage.file_id == f_row.id,
                ~SourceImage.label.in_(current_img_labels)
            ).delete(synchronize_session=False)
            db.commit()

        db.query(SourceFile).filter(
            SourceFile.workspace_id == ws_row.id,
            ~SourceFile.id.in_(current_file_ids)
        ).delete(synchronize_session=False)
        db.commit()

        if ws_memory.get("generated_notes"):
            notes_md = ws_memory["generated_notes"]
            notes_hash = hashlib.md5(notes_md.encode("utf-8")).hexdigest()
            existing_guide = db.query(StudyGuide).filter(
                StudyGuide.workspace_id == ws_row.id,
                StudyGuide.guide_hash == notes_hash
            ).first()
            
            if not existing_guide:
                first_line = notes_md.split("\n")[0] if notes_md else ""
                title = first_line.replace("#", "").strip() if first_line.startswith("#") else f"{subject_name} Study Guide"
                new_guide = StudyGuide(
                    workspace_id=ws_row.id,
                    title=title[:80],
                    content_md=notes_md,
                    guide_hash=notes_hash
                )
                db.add(new_guide)
                db.commit()

        db.query(QuizAttempt).filter(QuizAttempt.workspace_id == ws_row.id).delete()
        for q in ws_memory.get("quiz_history", []):
            attempt_row = QuizAttempt(
                workspace_id=ws_row.id,
                score=q["score"],
                quiz_json=json.dumps(q["questions"]),
                answers_json=json.dumps(q["answers"])
            )
            db.add(attempt_row)
        db.commit()

    except Exception:
        logger.error("save_active_workspace_to_db crashed", exc_info=True)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Sidebar helper
# ---------------------------------------------------------------------------

def _sb_section(label: str) -> None:
    st.markdown(
        f'<div class="sb-section-label">{label}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar View Block (Authentication-Aware)
# ---------------------------------------------------------------------------

def render_workspace_sidebar(username: str, is_admin: bool = False) -> tuple[str, str, str]:
    with st.sidebar:
        initial = (username[0].upper()) if username else "?"
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:13px;
                        padding:14px 4px 16px; border-bottom:1px solid var(--line);margin-bottom:6px;">
                <div style="width:50px;height:50px;border-radius:50%;
                            background:var(--yellow);flex-shrink:0;
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.45rem;font-weight:800;color:#FFFFFF;
                            font-family:'Truculenta',sans-serif;">
                    {initial}
                </div>
                <div>
                    <div style="font-weight:800;font-size:1rem;color:var(--ink);
                                font-family:'Truculenta',sans-serif;line-height:1.25;">
                        {username.title()}
                    </div>
                    <div style="font-size:0.78rem;color:var(--muted);
                                font-family:'Truculenta',sans-serif;">
                        {username}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if is_admin:
            in_admin = st.session_state.get("admin_view", False)
            lbl = "← Back to Study" if in_admin else "🛠 Admin Dashboard"
            if st.button(lbl, use_container_width=True):
                st.session_state["admin_view"] = not in_admin
                st.rerun()

        _sb_section("Navigation")
        current_page = st.session_state.get("current_page", "Dashboard")
        nav_pages = ["Dashboard", "Study guide", "Quiz", "Saved Guides"]
        for page in nav_pages:
            is_active = current_page == page
            btn_type = "primary" if is_active else "secondary"
            if st.button(page, key=f"nav_{page}", use_container_width=True, type=btn_type):
                st.session_state["current_page"] = page
                st.session_state["viewing_guide"] = None
                st.rerun()

        _sb_section("Workspaces")
        subjects = list(st.session_state["workspaces"].keys())
        active = st.session_state.get("active_workspace", subjects[0])
        if active not in subjects:
            active = subjects[0]

        selected = active
        for ws_name in subjects:
            if ws_name == active:
                st.markdown('<div class="ws-active-marker"></div>', unsafe_allow_html=True)
            if st.button(ws_name, key=f"ws_{ws_name}", use_container_width=True, type="secondary"):
                selected = ws_name

        new_subject = st.text_input("New subject...", key="new_subject_input", label_visibility="collapsed")
        if st.button("➕ Add Workspace", use_container_width=True):
            cleaned = new_subject.strip()
            if cleaned and cleaned not in st.session_state["workspaces"]:
                st.session_state["workspaces"][cleaned] = blank_workspace()
                selected = cleaned
                st.session_state["is_dirty"] = True
                st.rerun()

        if len(st.session_state["workspaces"]) > 1:
            if not st.session_state.get("_confirm_del_ws", False):
                if st.button(f"🗑 Delete '{active}'", use_container_width=True, type="secondary"):
                    st.session_state["_confirm_del_ws"] = True
                    st.rerun()
            else:
                st.warning(f"Delete '{active}' permanently?")
                cy, cn = st.columns(2)
                with cy:
                    if st.button("Yes", key="_del_ws_yes", type="primary", use_container_width=True):
                        ws_id = st.session_state["workspaces"][active].get("id")
                        if ws_id:
                            delete_workspace_from_db(username=username, workspace_id=ws_id)
                        del st.session_state["workspaces"][active]
                        st.session_state["active_workspace"] = next(iter(st.session_state["workspaces"]))
                        st.session_state["_confirm_del_ws"] = False
                        st.rerun()
                with cn:
                    if st.button("Cancel", key="_del_ws_no", use_container_width=True):
                        st.session_state["_confirm_del_ws"] = False
                        st.rerun()

        _sb_section("Study Modes")
        study_mode = st.session_state.get("_study_mode", "Deep Dive")
        c_deep, c_cram = st.columns(2)
        with c_deep:
            deep_t = "primary" if study_mode == "Deep Dive" else "secondary"
            if st.button("Deep Mode", key="_mode_deep", use_container_width=True, type=deep_t):
                st.session_state["_study_mode"] = "Deep Dive"
                st.rerun()
        with c_cram:
            cram_t = "primary" if study_mode == "Cram Mode" else "secondary"
            if st.button("Cram Mode", key="_mode_cram", use_container_width=True, type=cram_t):
                st.session_state["_study_mode"] = "Cram Mode"
                st.rerun()

        st.divider()
        c_set, c_out = st.columns(2)
        with c_set:
            if st.button("Settings", key="_sb_settings_btn", use_container_width=True, type="secondary"):
                st.session_state["current_page"] = "Settings"
                st.rerun()
        with c_out:
            if st.button("Log Out", key="_sb_logout_btn", use_container_width=True, type="secondary"):
                logout_user()

        st.session_state["active_workspace"] = selected
        api_key = st.session_state.get("gemini_api_key", "")
        return selected, api_key, study_mode


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------

def render_settings_page(current_user: str) -> None:
    import json as _json
    from utils.auth import delete_account
    from utils.gemini import GEMINI_MODEL

    if st.button("← Back"):
        st.session_state["current_page"] = "Dashboard"
        st.rerun()

    st.markdown(
        "<h1 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
        "color:#242B18;'>🔧 Settings & Account Management</h1>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h3 style='font-family:\"Truculenta\",sans-serif;color:#242B18;'>🔑 Gemini API Key</h3>",
        unsafe_allow_html=True,
    )
    current_key = st.session_state.get("gemini_api_key", "")
    new_key = st.text_input(
        "Enter your Google AI Studio API Key",
        value=current_key,
        type="password",
        help="Your key is held safely in browser runtime state — never compiled or checked on centralized disks.",
    )
    if new_key != current_key:
        st.session_state["gemini_api_key"] = new_key.strip()
        st.success("API key synchronized.")

    st.markdown(
        f"<div style='margin-top:-0.5rem;margin-bottom:1.5rem;font-size:0.85rem;color:var(--muted);'>"
        f"Active LLM Core Subsystem: <strong>{GEMINI_MODEL}</strong></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h3 style='font-family:\"Truculenta\",sans-serif;color:#242B18;'>🔒 Update Password</h3>",
        unsafe_allow_html=True,
    )
    with st.form("change_password_form"):
        current_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        submit_change = st.form_submit_button("Modify Password")

    if submit_change:
        from utils.auth import _validate_password
        from utils.persistence import verify_password, hash_password
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
                    if user is None or not verify_password(user.password_hash, current_pw):
                        st.error("Current password is incorrect.")
                    else:
                        user.password_hash = hash_password(new_pw)
                        db2.commit()
                        st.success("Password updated successfully.")
                except Exception:
                    logger.error("change_password failed for '%s'", current_user, exc_info=True)
                    st.error("Something went wrong while updating your password. Please try again.")
                finally:
                    db2.close()

    st.divider()
    st.markdown(
        "<h3 style='font-family:\"Truculenta\",sans-serif;color:#242B18;'>🚪 Log Out</h3>",
        unsafe_allow_html=True,
    )
    st.caption("You'll be returned to the login screen. Your API key stays saved in this browser.")
    if st.button("Log Out", key="_settings_logout", use_container_width=True, type="primary"):
        logout_user()

    st.divider()
    st.markdown(
        "<h3 style='font-family:\"Truculenta\",sans-serif;color:#242B18;'>⚠️ Danger Zone</h3>",
        unsafe_allow_html=True,
    )
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
                        logout_user()
                    else:
                        st.error(msg)
                else:
                    st.error("Username does not match.")
        with col_no:
            if st.button("Cancel", key="_del_acct_cancel", use_container_width=True):
                st.session_state.pop("_confirm_delete_account", None)
                st.rerun()


# ---------------------------------------------------------------------------
# Guide viewer page
# ---------------------------------------------------------------------------

def render_guide_viewer(guide: dict) -> None:
    if st.button("← Back to Saved"):
        st.session_state["viewing_guide"] = None
        st.rerun()
    render_guide(guide["content"], title=guide["title"])


# ---------------------------------------------------------------------------
# Admin Metrics Subsystem
# ---------------------------------------------------------------------------

def render_admin_dashboard() -> None:
    import pandas as pd
    from pathlib import Path
    st.markdown(
        "<h1 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
        "color:#242B18;'>🛠 Admin Control Dashboard</h1>",
        unsafe_allow_html=True,
    )
    
    metrics_tab, users_tab = st.tabs(["📊 Activity Logs", "👥 User Registrations"])
    with metrics_tab:
        _METRICS_DIR = Path("metrics")
        def _report_path(u: str) -> Path:
            return _METRICS_DIR / u / "activity_report.md"

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
                                u_key = f"dl_metrics_{uname}"
                                st.download_button(
                                    "⬇ Download",
                                    data=report.read_bytes(),
                                    file_name=f"{uname}_metrics.md",
                                    mime="text/markdown",
                                    key=u_key,
                                )
                            preview = report.read_text(encoding="utf-8")
                            st.markdown(preview[:4000] + ("\n\n_— download for full report —_" if len(preview) > 4000 else ""))
                        else:
                            st.caption("No activity yet.")
        else:
            st.info("No metrics directory found.")

    with users_tab:
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
# Saved Guides page
# ---------------------------------------------------------------------------

def render_saved_guides_page() -> None:
    st.markdown(
        "<h1 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
        "color:#242B18;margin-bottom:1rem;'>"
        "<i class='ti ti-bookmark' style='color:#D9A441;margin-right:10px;'></i>"
        "Saved Guides</h1>",
        unsafe_allow_html=True,
    )
    saved = st.session_state.get("saved_guides", [])
    if not saved:
        st.markdown(
            "<div style='background:#FFFFFF;border:1.5px solid #C5D99A;"
            "border-radius:14px;padding:2rem;text-align:center;color:#5C6A48;font-size:1.1rem;'>"
            "No notes saved yet. Generate notes inside a workspace and they'll compile here!"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    for item in saved:
        with st.container():
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1.5px solid var(--line);
                            border-radius:14px; padding:1.25rem 1.5rem; margin-bottom:0.75rem;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem;">
                        <div>
                            <span style="background:var(--sidebar); color:var(--ink);
                                         padding:3px 10px; border-radius:999px; font-size:0.75rem;
                                         font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">
                                {item['subject']}
                            </span>
                            <h3 style="margin:0.5rem 0 0.2rem 0; font-family:'Truculenta',sans-serif; font-weight:800; color:var(--ink);">
                                {item['title']}
                            </h3>
                            <div style="font-size:0.78rem; color:var(--muted);">
                                Saved on {item['saved_at']}
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            _, col_btn = st.columns([5, 1])
            with col_btn:
                if st.button("📖 View Guide", key=f"view_sg_{item['id']}", use_container_width=True):
                    st.session_state["viewing_guide"] = item["id"]
                    st.rerun()


# ---------------------------------------------------------------------------
# Core Runtime Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    apply_theme()
    init_auth_session_state()

    current_user = st.session_state.get("username")
    is_admin = st.session_state.get("is_admin", False)

    if not current_user:
        render_login_signup_ui()
        return

    if "workspaces" not in st.session_state:
        ws_dict, saved_gs = load_user_workspaces_from_db(current_user)
        if not ws_dict:
            ws_dict["General Study"] = blank_workspace()
        st.session_state["workspaces"] = ws_dict
        st.session_state["saved_guides"] = saved_gs
        st.session_state["is_dirty"] = False

    if is_admin and st.session_state.get("admin_view", False):
        render_workspace_sidebar(current_user, is_admin=True)
        render_admin_dashboard()
        return

    subject, api_key, study_mode = render_workspace_sidebar(current_user, is_admin=is_admin)

    if st.session_state.get("current_page") == "Settings":
        render_settings_page(current_user)
        return

    viewing_id = st.session_state.get("viewing_guide")
    if viewing_id:
        saved = st.session_state.get("saved_guides", [])
        guide_to_view = next((g for g in saved if g["id"] == viewing_id), None)
        if guide_to_view:
            render_guide_viewer(guide_to_view)
            return
        st.session_state["viewing_guide"] = None

    workspace = st.session_state["workspaces"][subject]
    current_page = st.session_state.get("current_page", "Dashboard")

    from tabs.ingest import render_ingest_tab
    from tabs.study import render_study_tab
    from tabs.quiz import render_quiz_tab

    if current_page == "Saved Guides":
        render_saved_guides_page()
    elif current_page == "Dashboard":
        st.markdown(
            "<h1 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
            "color:#242B18;margin-bottom:0.1rem;'>SunDevil AI</h1>"
            f"<p style='color:#5C6A48;font-family:\"Truculenta\",sans-serif;font-size:1.15rem;margin-bottom:1.5rem;'>"
            f"Active Workspace: <strong>{subject}</strong> — Upload materials to configure study tabs.</p>",
            unsafe_allow_html=True,
        )
        render_ingest_tab(workspace)
    else:
        if not api_key:
            st.markdown(
                """
                <div style="background:#FFF9E6;border:1.5px solid #E6A100;border-radius:14px;
                            padding:1.25rem 1.5rem;margin:1rem 0 1.5rem 0;">
                  <strong style="color:#805900;font-size:1.1rem;font-family:'Truculenta',sans-serif;">
                    🔑 Gemini API Key required
                  </strong>
                  <p style="color:#5C6A48;font-family:'Truculenta',sans-serif;
                            font-size:0.9rem;margin:0.4rem 0 0;">
                    SunDevil AI uses Google's Gemini to generate study guides and quizzes.
                    Your key is <strong>stored only in this browser</strong> — never on our servers.
                    <a href="https://aistudio.google.com/app/apikey" target="_blank"
                       style="color:#8BA552;">Get a free key →</a>
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns([2, 5])
            with b1:
                if st.button("Go to Settings", type="primary"):
                    st.session_state["current_page"] = "Settings"
                    st.rerun()
            with b2:
                if st.button("Dismiss"):
                    st.session_state["_api_key_banner_dismissed"] = True
                    st.rerun()

        st.divider()
        if current_page == "Study guide":
            render_study_tab(api_key, subject, workspace, study_mode)
        elif current_page == "Quiz":
            render_quiz_tab(api_key, subject, workspace)

    if st.session_state["is_dirty"]:
        save_active_workspace_to_db(current_user, subject, workspace)
        st.session_state["is_dirty"] = False


if __name__ == "__main__":
    main()

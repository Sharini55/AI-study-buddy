import hashlib
import json
import logging
import os
import streamlit as st

logger = logging.getLogger(__name__)
from sqlalchemy import or_
from sqlalchemy.orm import Session

from utils.auth import init_auth_session_state, render_login_signup_ui, logout_user
from utils.persistence import (
    SessionLocal, User, Workspace, SourceFile, SourceImage, StudyGuide, QuizAttempt,
    save_uploaded_image_locally, load_local_image_bytes, delete_workspace_from_db
)
from utils.files import blank_workspace, refresh_processed_text
from utils.guide import render_guide

APP_TITLE = "AI Study Buddy"


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css');
        @import url('https://fonts.googleapis.com/css2?family=Truculenta:opsz,wght@12..72,100..900&display=swap');

        :root {
            --bg:          #F5F8EE;
            --sidebar:     #ECF1E2;
            --panel:       #FFFFFF;
            --ink:         #242B18;
            --muted:       #5C6A48;
            --line:        #C5D99A;
            --green:       #ABC270;
            --green-dark:  #8BA552;
            --yellow:      #D9A441;
            --orange:      #C18A2A;
            --green-glow:  rgba(171, 194, 112, 0.22);
        }

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

        header[data-testid="stHeader"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        [data-testid="stToolbar"] {
            background: transparent !important;
            box-shadow: none !important;
        }
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stToolbarActionButtonTooltip"],
        #MainMenu,
        footer { display: none !important; }

        html, body { background: var(--bg) !important; color: var(--ink) !important; }
        .stApp    { background: var(--bg) !important; color: var(--ink) !important; }
        .main .block-container { max-width: 1360px; padding-top: 1rem; }

        [data-testid="stSidebar"] {
            background: var(--sidebar) !important;
            border-right: 2px solid var(--line) !important;
        }
        [data-testid="stSidebar"] * { color: var(--ink) !important; letter-spacing: 0; }

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
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p,
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] span { color: #FFFFFF !important; }
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] p,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] span { color: var(--ink) !important; }

        [data-testid="stSidebar"] div:has(.ws-active-marker) + div [data-testid="stBaseButton-secondary"],
        [data-testid="stSidebar"] div:has(.ws-active-marker) + div [data-testid="baseButton-secondary"] {
            background:  rgba(171,194,112,0.28) !important;
            border:      1.5px solid var(--green) !important;
            font-weight: 600 !important;
        }

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

        h1, h2, h3, h4, h5, h6 {
            color: var(--ink) !important;
            font-family: 'Truculenta', sans-serif !important;
            letter-spacing: -0.3px;
        }

        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 999px;
            padding: 10px 20px;
            color: var(--ink);
            font-family: 'Truculenta', sans-serif !important;
            font-weight: 600;
            transition: background 0.15s;
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

        [data-testid="stFileUploaderDropzone"] button {
            position:      relative !important;
            background:    var(--yellow) !important;
            border:        none !important;
            border-radius: 999px !important;
            padding:       6px 28px !important;
            min-width:     90px !important;
            min-height:    36px !important;
            cursor:        pointer !important;
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

        [data-testid="stForm"] {
            background: #FFFFFF;
            border: 1.5px solid var(--line);
            border-radius: 18px;
            padding: 1.5rem 1.5rem 0.5rem;
        }
        [data-testid="stForm"] label,
        [data-testid="stForm"] [data-testid="stWidgetLabel"],
        [data-testid="stForm"] [data-testid="stWidgetLabel"] p,
        [data-testid="stForm"] [data-testid="stWidgetLabel"] label {
            color: var(--ink) !important;
        }
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"],
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"] {
            background: var(--green) !important;
            border-color: var(--green) !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border-radius: 999px !important;
        }
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] p,
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"] span,
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"] p,
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"] span {
            color: #FFFFFF !important;
        }
        [data-testid="stForm"] [data-testid="stBaseButton-primaryFormSubmit"]:hover,
        [data-testid="stForm"] [data-testid="baseButton-primaryFormSubmit"]:hover {
            background: var(--green-dark) !important;
            border-color: var(--green-dark) !important;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] label,
        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] div,
        [data-testid="stMetricDelta"] { color: var(--ink) !important; }

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

        div[role="progressbar"] > div,
        .stProgress > div > div > div > div {
            background-color: var(--green) !important;
            border-radius: 999px;
        }

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

        [data-baseweb="radio"] > div:first-child {
            border-color: var(--green) !important;
        }
        [data-baseweb="radio"] > div:first-child[aria-checked="true"] {
            background: var(--green) !important;
            border-color: var(--green) !important;
        }

        [data-baseweb="checkbox"] [role="checkbox"] {
            border-color: var(--green) !important;
        }
        [data-baseweb="checkbox"] [role="checkbox"][aria-checked="true"] {
            background: var(--green) !important;
            border-color: var(--green) !important;
        }

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

        hr { border-color: var(--line) !important; opacity: 1; }

        pre, pre * { color: var(--ink) !important; background: transparent !important; }
        code:not([class]) {
            background: #E3EED0 !important;
            color: #2A450A !important;
            border-radius: 5px !important;
            padding: 1px 5px !important;
            font-family: 'Truculenta', monospace !important;
        }

        [data-testid="stSpinner"] > div {
            border-top-color: var(--green) !important;
        }

        [data-testid="stSidebarCollapseButton"] button {
            position:      relative !important;
            width:         42px !important;
            height:        42px !important;
            min-width:     42px !important;
            min-height:    42px !important;
            line-height:   42px !important;
            padding:       0 !important;
            background:    transparent !important;
            border:        none !important;
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
            color:      var(--ink) !important;
            pointer-events: none !important;
        }

        [data-testid="stExpandSidebarButton"] button {
            position:      relative !important;
            width:         42px !important;
            height:        42px !important;
            min-width:     42px !important;
            min-height:    42px !important;
            line-height:   42px !important;
            padding:       0 !important;
            background:    var(--yellow) !important;
            border:        none !important;
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
            color:      var(--ink) !important;
            pointer-events: none !important;
        }

        section[data-testid="stSidebar"] {
            min-width: 0 !important;
        }

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

        /* ── Password input toggle button styling fix ── */
        [data-testid="stPasswordInput"] button,
        div[data-baseweb="input-password"] button {
            position:      relative !important;
            background:    transparent !important;
            border:        none !important;
            padding:       0 !important;
            margin-right:  4px !important;
            width:         30px !important;
            min-width:     30px !important;
            height:        30px !important;
            min-height:    30px !important;
            border-radius: 6px !important;
            cursor:        pointer !important;
            overflow:      hidden !important;
        }
        [data-testid="stPasswordInput"] button:hover,
        div[data-baseweb="input-password"] button:hover {
            background: rgba(139, 165, 82, 0.15) !important;
        }
        /* hide whatever Streamlit renders inside (icon-font text like "visibility") */
        [data-testid="stPasswordInput"] button svg,
        [data-testid="stPasswordInput"] button span,
        [data-testid="stPasswordInput"] button p,
        [data-testid="stPasswordInput"] button div,
        div[data-baseweb="input-password"] button svg,
        div[data-baseweb="input-password"] button span,
        div[data-baseweb="input-password"] button p,
        div[data-baseweb="input-password"] button div {
            font-size:  0 !important;
            color:      transparent !important;
            fill:       transparent !important;
            opacity:    0 !important;
            width:      0 !important;
            height:     0 !important;
            overflow:   hidden !important;
        }
        /* draw our own eye icon instead */
        [data-testid="stPasswordInput"] button::after,
        div[data-baseweb="input-password"] button::after {
            content:         "\\1F441";
            position:        absolute !important;
            inset:           0 !important;
            display:         flex !important;
            align-items:     center !important;
            justify-content: center !important;
            font-size:       1rem !important;
            line-height:     1 !important;
            color:           var(--muted) !important;
            pointer-events:  none !important;
        }
        [data-testid="stPasswordInput"] button[aria-label*="Hide" i]::after,
        div[data-baseweb="input-password"] button[aria-label*="Hide" i]::after {
            content: "\\1F576";
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

                    if (txt === 'Deep Mode')  btn.classList.add('mode-btn-left');
                    if (txt === 'Cram Mode')  btn.classList.add('mode-btn-right');

                    if (txt === 'Settings' || txt === 'Log Out') btn.classList.add('sb-footer-link');
                });
            }

            function fixFileUploaderBtn() {
                document.querySelectorAll(
                    '[data-testid="stFileUploaderDropzone"] button'
                ).forEach(function(btn) {
                    btn.querySelectorAll('span').forEach(function(s) {
                        if (s.children.length === 0 &&
                            s.textContent.trim().toLowerCase() === 'upload') {
                            s.style.setProperty('font-size',  '0',            'important');
                            s.style.setProperty('width',      '0',            'important');
                            s.style.setProperty('height',     '0',            'important');
                            s.style.setProperty('overflow',   'hidden',       'important');
                            s.style.setProperty('display',    'inline-block', 'important');
                        }
                    });
                });
            }

            function _runAll() { initSidebar(); fixFileUploaderBtn(); }
            var _mo = new MutationObserver(_runAll);
            _mo.observe(document.body, {childList: true, subtree: true});
            _runAll();

            var _restored = false;
            function restoreApiKey() {
                if (_restored) return;
                var stored = localStorage.getItem('gemini_api_key');
                if (!stored) return;
                var inp = Array.from(document.querySelectorAll('input[type="password"]'))
                              .find(function(i) { return i.placeholder && i.placeholder.toLowerCase().indexOf('gemini') !== -1; });
                if (!inp || inp.value) { _restored = !!inp; return; }
                try {
                    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(inp, stored);
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    _restored = true;
                } catch(e) {}
            }
            var _amo = new MutationObserver(restoreApiKey);
            _amo.observe(document.body, {childList: true, subtree: true});
            setTimeout(restoreApiKey, 500);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


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
                    guide_id = g.guide_hash or hashlib.sha256(
                        g.content_md.encode("utf-8")
                    ).hexdigest()[:12]
                    saved_guides.append({
                        "id": guide_id,
                        "title": g.title,
                        "subject": ws.subject_name,
                        "content": g.content_md,
                        "saved_at": g.created_at.strftime("%b %d, %H:%M") if g.created_at else "",
                    })

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

        for file_item in ws_memory.get("files", []):
            content_hash = hashlib.sha256(file_item["content"].encode("utf-8")).hexdigest() if file_item["content"] else "empty"
            existing_file = db.query(SourceFile).filter(
                SourceFile.workspace_id == ws_row.id,
                SourceFile.file_hash == content_hash
            ).first()
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

        for guide in st.session_state.get("saved_guides", []):
            if guide.get("subject") != subject_name:
                continue
            existing_guide = db.query(StudyGuide).filter(
                StudyGuide.workspace_id == ws_row.id,
                or_(
                    StudyGuide.guide_hash == guide["id"],
                    StudyGuide.content_md == guide["content"],
                ),
            ).first()
            if not existing_guide:
                db.add(StudyGuide(
                    workspace_id=ws_row.id,
                    title=guide["title"],
                    content_md=guide["content"],
                    guide_hash=guide["id"],
                ))
        db.commit()

        stored_attempts_count = db.query(QuizAttempt).filter(
            QuizAttempt.workspace_id == ws_row.id
        ).count()
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


def _sb_section(label: str) -> None:
    st.markdown(
        f'<div class="sb-section-label">{label}</div>',
        unsafe_allow_html=True,
    )


def render_workspace_sidebar(username: str, is_admin: bool = False) -> tuple[str, str, str]:
    with st.sidebar:
        initial = (username[0].upper()) if username else "?"
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:13px;
                        padding:14px 4px 16px;
                        border-bottom:1px solid var(--line);margin-bottom:6px;">
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
                st.session_state["active_workspace"] = ws_name
                selected = ws_name
                st.rerun()

        if st.session_state.get("_rename_ws_open"):
            new_name = st.text_input(
                "Rename", value=active, key="_rename_ws_val",
                label_visibility="collapsed",
            )
            c_save, c_cancel = st.columns(2)
            with c_save:
                if st.button("Save", key="_rename_save", use_container_width=True, type="primary"):
                    new_name = new_name.strip()
                    if new_name and new_name != active:
                        ws_data = st.session_state["workspaces"].pop(active)
                        st.session_state["workspaces"][new_name] = ws_data
                        st.session_state["active_workspace"] = new_name
                        selected = new_name
                    st.session_state["_rename_ws_open"] = False
                    st.rerun()
            with c_cancel:
                if st.button("Cancel", key="_rename_cancel", use_container_width=True):
                    st.session_state["_rename_ws_open"] = False
                    st.rerun()

        c_add, c_ren, c_del = st.columns([4, 1, 1])
        with c_add:
            if st.button("＋ Add Workspace", key="_add_ws_toggle", use_container_width=True):
                st.session_state["_add_ws_open"] = (
                    not st.session_state.get("_add_ws_open", False)
                )
                st.rerun()
        with c_ren:
            if st.button("✎", key="_ren_ws_btn", help="Rename active workspace"):
                st.session_state["_rename_ws_open"] = (
                    not st.session_state.get("_rename_ws_open", False)
                )
                st.rerun()
        with c_del:
            if st.button("🗑", key="_del_ws_btn", help="Delete active workspace"):
                st.session_state["_confirm_del_ws"] = True
                st.rerun()

        if st.session_state.get("_add_ws_open"):
            new_subject = st.text_input(
                "", placeholder="e.g. CSE 240, Physics…",
                key="_new_ws_name", label_visibility="collapsed",
            )
            if st.button("Create", key="_create_ws", type="primary", use_container_width=True):
                s = new_subject.strip()
                if s:
                    st.session_state["workspaces"].setdefault(s, blank_workspace())
                    st.session_state["active_workspace"] = s
                    selected = s
                    save_active_workspace_to_db(
                        username, s, st.session_state["workspaces"][s]
                    )
                    st.session_state["_add_ws_open"] = False
                    st.rerun()

        if st.session_state.get("_confirm_del_ws"):
            if len(subjects) == 1:
                st.warning("Create another workspace first.")
                st.session_state["_confirm_del_ws"] = False
            else:
                st.warning(f"Delete **{active}**? This cannot be undone.")
                cy, cn = st.columns(2)
                with cy:
                    if st.button("Yes", key="_del_ws_yes", type="primary", use_container_width=True):
                        ws_id = st.session_state["workspaces"][active].get("id")
                        if ws_id:
                            delete_workspace_from_db(username=username, workspace_id=ws_id)
                        del st.session_state["workspaces"][active]
                        st.session_state["active_workspace"] = next(
                            iter(st.session_state["workspaces"])
                        )
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


def render_settings_page(current_user: str) -> None:
    import json as _json
    from utils.auth import delete_account
    from utils.gemini import GEMINI_MODEL

    if st.button("← Back"):
        st.session_state["current_page"] = "Dashboard"
        st.rerun()

    st.markdown(
        "<h1 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
        "color:#242B18;margin-bottom:0.2rem;'>⚙ Settings</h1>",
        unsafe_allow_html=True,
    )
    st.caption(f"Logged in as **{current_user}**")

    workspaces   = st.session_state.get("workspaces", {})
    saved_guides = st.session_state.get("saved_guides", [])
    ws_count     = len(workspaces)
    guide_count  = len(saved_guides)
    quiz_count   = sum(len(ws.get("quiz_history", [])) for ws in workspaces.values())
    c1, c2, c3 = st.columns(3)
    c1.metric("Workspaces",    ws_count)
    c2.metric("Guides Saved",  guide_count)
    c3.metric("Quizzes Taken", quiz_count)

    st.divider()

    st.markdown(
        "<h3 style='font-family:\"Truculenta\",sans-serif;color:#242B18;'>🔑 Gemini API Key</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "AI Study Buddy uses Google's Gemini to generate your study guides. "
        "Your key is **stored only on this device** in your browser — it is never sent to our servers. "
        '<a href="https://aistudio.google.com/app/apikey" target="_blank" '
        'style="color:var(--green-dark);">Get a free key here →</a>',
        unsafe_allow_html=True,
    )
    st.caption(f"Active model: `{GEMINI_MODEL}`")

    api_key_val = st.session_state.get("gemini_api_key", "")
    api_key_input = st.text_input(
        "API Key",
        value=api_key_val,
        type="password",
        placeholder="Paste your Gemini API key here…",
        label_visibility="collapsed",
        key="_settings_api_key_input",
    )
    if st.button("Save API Key", type="primary"):
        st.session_state["gemini_api_key"] = api_key_input
        safe_key = _json.dumps(api_key_input)
        st.markdown(
            f"<script>try{{localStorage.setItem('gemini_api_key',{safe_key});}}catch(e){{}}</script>",
            unsafe_allow_html=True,
        )
        st.success("API key saved to this browser.")

    st.divider()

    st.markdown(
        "<h3 style='font-family:\"Truculenta\",sans-serif;color:#242B18;'>🔒 Change Password</h3>",
        unsafe_allow_html=True,
    )
    current_pw = st.text_input("Current Password", type="password", key="_cp_current")
    new_pw     = st.text_input(
        "New Password", type="password",
        placeholder="Min 8 chars · 1 number · 1 special character",
        key="_cp_new",
    )
    confirm_pw = st.text_input("Confirm New Password", type="password", key="_cp_confirm")
    if st.button("Update Password", use_container_width=True, type="primary", key="_cp_submit"):
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
                    st.error("Something went wrong. Please try again.")
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


def render_admin_dashboard(current_user: str) -> None:
    from tabs.db_inspector import render_db_inspector_tab

    _db_check = SessionLocal()
    try:
        _user_row = _db_check.query(User).filter(User.username == current_user).first()
        _confirmed_admin = bool(_user_row and _user_row.is_admin)
    except Exception:
        logger.error("Admin gate DB check failed for '%s'", current_user, exc_info=True)
        _confirmed_admin = False
    finally:
        _db_check.close()

    if not _confirmed_admin:
        st.error("Access denied.")
        logger.warning("Admin dashboard access attempt by non-admin '%s'", current_user)
        return

    st.title("🛠 Admin Dashboard")
    st.caption(f"Logged in as **{current_user}**")

    render_db_inspector_tab()


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
            "<div style='background:#FFFFFF;border:1.5px solid #C5D99A;border-radius:18px;"
            "padding:2rem;text-align:center;margin-top:1rem;'>"
            "<p style='color:#5C6A48;font-family:\"Truculenta\",sans-serif;font-size:1rem;'>"
            "No guides saved yet — generate a study guide to see it here.</p></div>",
            unsafe_allow_html=True,
        )
        return

    for guide in saved:
        guide_id = guide["id"]
        col_pill, col_del = st.columns([9, 1])
        with col_pill:
            label = f"📄  {guide['title']}  ·  {guide['saved_at']}"
            if st.button(label, key=f"sg_open_{guide_id}", use_container_width=True, type="primary"):
                st.session_state["viewing_guide"] = guide_id
                st.rerun()
        with col_del:
            if st.button("✕", key=f"sg_del_{guide_id}", help="Remove guide"):
                if st.session_state.get("viewing_guide") == guide_id:
                    st.session_state["viewing_guide"] = None
                st.session_state["saved_guides"] = [
                    g for g in saved if g["id"] != guide_id
                ]
                st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=":books:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_auth_session_state()
    apply_theme()

    if not st.session_state["authenticated"]:
        render_login_signup_ui()
        st.stop()

    current_user = st.session_state["username"]
    is_admin = st.session_state.get("is_admin", False)

    st.session_state.setdefault("current_page", "Dashboard")
    st.session_state.setdefault("saved_guides", [])
    st.session_state.setdefault("viewing_guide", None)
    st.session_state.setdefault("admin_view", False)
    st.session_state.setdefault("viewing_profile", False)
    st.session_state.setdefault("is_dirty", False)
    st.session_state.setdefault("gemini_api_key", "")
    st.session_state.setdefault("_api_key_banner_dismissed", False)

    if "workspaces" not in st.session_state or not st.session_state["workspaces"]:
        loaded, loaded_guides = load_user_workspaces_from_db(current_user)
        if loaded:
            st.session_state["workspaces"] = loaded
            st.session_state["active_workspace"] = next(iter(loaded))
            st.session_state["saved_guides"] = loaded_guides
        else:
            default_ws_name = "My Workspace"
            st.session_state["workspaces"] = {default_ws_name: blank_workspace()}
            st.session_state["active_workspace"] = default_ws_name
            save_active_workspace_to_db(current_user, default_ws_name,
                                        st.session_state["workspaces"][default_ws_name])

    subject, api_key, study_mode = render_workspace_sidebar(current_user, is_admin)

    if st.session_state.get("current_page") == "Settings" or st.session_state.get("viewing_profile"):
        render_settings_page(current_user)
        return

    if is_admin and st.session_state.get("admin_view"):
        render_admin_dashboard(current_user)
        return

    viewing_id = st.session_state.get("viewing_guide")
    if viewing_id is not None:
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
            "color:#242B18;margin-bottom:0.1rem;'>AI Study Buddy</h1>"
            f"<p style='color:#5C6A48;font-family:\"Truculenta\",sans-serif;"
            f"font-size:0.95rem;margin-top:0;'>{subject}</p>",
            unsafe_allow_html=True,
        )
        st.divider()
        render_ingest_tab(subject, workspace, api_key)
    else:
        page_meta = {
            "Study guide": (
                "<i class='ti ti-book' style='color:#D9A441;margin-right:8px;'></i>Study Guide",
                subject,
            ),
            "Quiz": (
                "<i class='ti ti-help-circle' style='color:#D9A441;margin-right:8px;'></i>Interactive Quiz",
                subject,
            ),
        }
        title_html, caption = page_meta.get(
            current_page,
            ("<i class='ti ti-layout-dashboard' style='color:#D9A441;margin-right:8px;'></i>Dashboard", subject),
        )
        st.markdown(
            f"<h2 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
            f"color:#242B18;margin-bottom:0.1rem;'>{title_html}</h2>"
            f"<p style='color:#5C6A48;font-family:\"Truculenta\",sans-serif;"
            f"font-size:0.95rem;margin-top:0;'>{caption}</p>",
            unsafe_allow_html=True,
        )

        if (not st.session_state.get("gemini_api_key")
                and not st.session_state.get("_api_key_banner_dismissed")):
            st.markdown(
                """
                <div style="border:2px solid #D9A441;border-radius:14px;
                            padding:1rem 1.25rem;background:#FFFBEF;margin-bottom:1rem;">
                  <strong style="color:#242B18;font-family:'Truculenta',sans-serif;">
                    🔑 Gemini API Key required
                  </strong>
                  <p style="color:#5C6A48;font-family:'Truculenta',sans-serif;
                            font-size:0.9rem;margin:0.4rem 0 0;">
                    AI Study Buddy uses Google's Gemini to generate study guides and quizzes.
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

"""tabs/how_it_works.py

A short walkthrough that shows a new user the minimum path to a first result:
add notes -> pick a mode -> generate. Everything else (question counts, weak
areas, progress bars) they can discover by clicking.

Screenshots live in assets/tour/ at the repo root. If an image file is missing
the slide still renders, with a small placeholder, instead of crashing the page.
"""

import logging
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

_TOUR_DIR = Path(__file__).resolve().parent.parent / "assets" / "tour"

_BADGE_BG = "#C8E6B3"
_INK = "#242B18"
_MUTED = "#5C6A48"
_YELLOW = "#D9A441"
_LINE = "#C5D99A"

# Each slide: eyebrow label, title, intro text, then either a single full-width
# image, or a pair (sidebar button crop on the left, the page on the right) with
# a numbered caption under each, and an optional numbered legend and tip.
SLIDES = [
    {
        "eyebrow": "Welcome",
        "title": "Welcome to AI Study Buddy",
        "intro": (
            "Upload your notes and get a study guide or a quiz, or use Adaptive "
            "Study to focus on your weak spots. Everything is built only from the "
            "notes you give it. It doesn't use the internet."
        ),
        "images": [("01_overview.png", None)],
    },
    {
        "eyebrow": "Step 1 · Add your notes",
        "title": "Add your notes",
        "intro": "Do 1.1, 1.2, or both. Then click 2.",
        "images": [("02_add_notes.png", None)],
        "legend": [
            ("1.1", "Click Upload and choose your files (PDF, PPTX, JPG, or PNG)."),
            ("1.2", "Or paste text from your textbook or notes into the box."),
            ("2", "Click Index Materials to save everything you added."),
        ],
        "tip": (
            "Use notes, slides, or textbook pages with real explanations. A list of "
            "keywords or a worksheet full of questions can't be turned into a guide."
        ),
    },
    {
        "eyebrow": "Step 2 · Pick a mode",
        "title": "Study Guide",
        "intro": "A written guide with explanations, worked examples, and a challenge for each topic.",
        "images": [
            ("03a_study_guide_button.png", (3, "Click Study guide in the sidebar.")),
            ("03b_study_guide_page.png", (4, "Click Generate Study Guide.")),
        ],
        "tip": "Short on time? Switch to Cram Mode in the sidebar. Deep Mode is the default.",
    },
    {
        "eyebrow": "Step 2 · Pick a mode",
        "title": "Quiz",
        "intro": "Multiple-choice questions made from your notes, with an explanation for every answer.",
        "images": [
            ("04a_quiz_button.png", (3, "Click Quiz in the sidebar.")),
            ("04b_quiz_page.png", (4, "Choose how many questions you want, then click Generate Quiz.")),
        ],
    },
    {
        "eyebrow": "Step 2 · Pick a mode",
        "title": "Adaptive Study",
        "intro": "Not sure where to start? Adaptive Study finds your weak spots for you.",
        "images": [
            ("05a_adaptive_button.png", (3, "Click Adaptive Study in the sidebar.")),
            ("05b_adaptive_page.png", (4, "Click Start Diagnostic Quiz. It finds your weak spots, then builds practice rounds focused on them.")),
        ],
    },
]


def _track(event: str, username: str, props: dict | None = None) -> None:
    try:
        from utils.analytics import capture
        capture(event, username, props or {})
    except Exception:
        logger.warning("Analytics failed for event '%s'", event, exc_info=True)


def _badge(label) -> str:
    return (
        f"<span style='display:inline-flex;align-items:center;justify-content:center;"
        f"min-width:34px;height:34px;padding:0 9px;border-radius:999px;"
        f"background:{_BADGE_BG};color:{_INK};font-weight:800;font-size:0.95rem;"
        f"flex-shrink:0;margin-right:12px;'>{label}</span>"
    )


def _caption(number, text: str) -> None:
    st.markdown(
        f"<div style='display:flex;align-items:flex-start;margin:0.5rem 0 0.25rem;"
        f"color:{_INK};font-size:1rem;line-height:1.35;'>{_badge(number)}"
        f"<span style='padding-top:5px;'>{text}</span></div>",
        unsafe_allow_html=True,
    )


def _show_image(name: str) -> None:
    path = _TOUR_DIR / name
    if not path.exists():
        logger.warning("Tour screenshot missing: %s", path)
        st.info("Screenshot unavailable.")
        return
    # Newer Streamlit wants width="stretch"; older versions only know
    # use_container_width. Try the new spelling first so recent versions don't log
    # a deprecation warning, then fall back.
    try:
        st.image(str(path), width="stretch")
    except Exception:
        try:
            st.image(str(path), use_container_width=True)
        except Exception:
            st.image(str(path))


def _dots(step: int, total: int) -> str:
    dots = "".join(
        f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
        f"margin:0 4px;background:{_YELLOW if i == step else _LINE};'></span>"
        for i in range(total)
    )
    return (
        f"<div style='text-align:center;margin:0.25rem 0 0.75rem;'>{dots}"
        f"<div style='color:{_MUTED};font-size:0.8rem;margin-top:4px;'>"
        f"{step + 1} of {total}</div></div>"
    )


def _go_to_dashboard(username: str, step: int, completed: bool) -> None:
    _track("tour_completed" if completed else "tour_skipped", username, {"last_step": step + 1})
    st.session_state["current_page"] = "Dashboard"
    st.session_state["_tour_step"] = 0
    st.rerun()


def render_how_it_works() -> None:
    username = st.session_state.get("username", "anonymous")
    total = len(SLIDES)
    step = max(0, min(int(st.session_state.get("_tour_step", 0)), total - 1))
    slide = SLIDES[step]
    is_last = step == total - 1

    st.markdown(_dots(step, total), unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            f"<div style='font-size:0.72rem;font-weight:700;letter-spacing:1.6px;"
            f"text-transform:uppercase;color:{_MUTED};margin-top:0.25rem;'>"
            f"{slide['eyebrow']}</div>"
            f"<h2 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
            f"color:{_INK};margin:0.1rem 0 0.35rem;'>{slide['title']}</h2>"
            f"<p style='color:{_MUTED};font-size:1.05rem;margin:0 0 0.9rem;'>"
            f"{slide['intro']}</p>",
            unsafe_allow_html=True,
        )

        images = slide["images"]
        if len(images) == 1:
            _show_image(images[0][0])
        else:
            # Narrow sidebar crop on the left, the wider page on the right.
            col_left, col_right = st.columns([1, 2.3], gap="large")
            for col, (name, cap) in zip((col_left, col_right), images):
                with col:
                    _show_image(name)
                    if cap:
                        _caption(*cap)

        for number, text in slide.get("legend", []):
            st.markdown(
                f"<div style='display:flex;align-items:center;margin:0.45rem 0;"
                f"color:{_INK};font-size:1rem;'>{_badge(number)}<span>{text}</span></div>",
                unsafe_allow_html=True,
            )

        if slide.get("tip"):
            st.markdown(
                f"<div style='background:#FFFBEF;border:1.5px solid {_YELLOW};"
                f"border-radius:12px;padding:0.6rem 0.9rem;margin-top:0.8rem;"
                f"color:{_INK};font-size:0.95rem;'>💡 {slide['tip']}</div>",
                unsafe_allow_html=True,
            )

        if is_last:
            st.markdown(
                f"<p style='color:{_INK};font-weight:700;font-size:1.05rem;"
                f"margin:1rem 0 0;'>That's it. Add your first notes to get started.</p>",
                unsafe_allow_html=True,
            )

    st.write("")
    c_back, c_skip, _spacer, c_next = st.columns([1, 1, 3, 1.6])
    with c_back:
        if step > 0 and st.button("← Back", key="_tour_back", use_container_width=True):
            st.session_state["_tour_step"] = step - 1
            st.rerun()
    with c_skip:
        if not is_last and st.button("Skip tour", key="_tour_skip", use_container_width=True):
            _go_to_dashboard(username, step, completed=False)
    with c_next:
        if is_last:
            if st.button("Get started →", key="_tour_done", type="primary", use_container_width=True):
                _go_to_dashboard(username, step, completed=True)
        elif st.button("Next →", key="_tour_next", type="primary", use_container_width=True):
            st.session_state["_tour_step"] = step + 1
            st.rerun()

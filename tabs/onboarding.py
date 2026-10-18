import logging

import streamlit as st

from utils.persistence import save_user_profile
from utils.student_profile import EDU_LEVELS, FIELDS, STUDY_STYLES, needs_field

logger = logging.getLogger(__name__)


def _track(event: str, username: str, props: dict | None = None) -> None:
    try:
        from utils.analytics import capture
        capture(event, username, props or {})
    except Exception:
        logger.warning("Analytics failed for event '%s'", event, exc_info=True)


def _save_and_continue(username: str, level, field, style, *, skipped: bool = False) -> None:
    try:
        save_user_profile(username, level, field, style, onboarding_done=True)
    except Exception:
        logger.error("save_user_profile failed for '%s'", username, exc_info=True)
        st.error("Couldn't save your answers. Please try again.")
        return

    st.session_state["student_profile"] = {
        "edu_level": level,
        "edu_field": field,
        "study_style": style,
        "onboarding_done": True,
    }
    st.session_state.pop(f"_onb_step_{username}", None)
    st.session_state.pop(f"_onb_draft_{username}", None)
    _track(
        "onboarding_skipped" if skipped else "onboarding_completed",
        username,
        {"edu_level": level, "edu_field": field, "study_style": style},
    )
    st.rerun()


def render_onboarding(username: str) -> None:
    """3-screen wizard shown right after login until the user finishes or skips.

    Screen 1: education level. Screen 2: field (undergrad and above only).
    Screen 3: study style. Each choice is one click and advances automatically.
    """
    step_key  = f"_onb_step_{username}"
    draft_key = f"_onb_draft_{username}"
    step  = st.session_state.get(step_key, 1)
    draft = st.session_state.setdefault(draft_key, {})

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(
            "<h1 style='font-family:\"Truculenta\",sans-serif;font-weight:900;"
            "color:#242B18;text-align:center;margin:1.5rem 0 0.2rem;'>"
            "Let's set up your study buddy</h1>"
            "<p style='text-align:center;color:#5C6A48;margin-bottom:1.5rem;'>"
            "Takes about 10 seconds. You can change this anytime in Settings.</p>",
            unsafe_allow_html=True,
        )

        if step == 1:
            question = "What's your education level?"
        elif step == 2:
            question = "What's your field of study?"
        else:
            question = "How do you like to study?"
        st.markdown(
            f"<h3 style='font-family:\"Truculenta\",sans-serif;color:#242B18;"
            f"text-align:center;margin-bottom:0.75rem;'>{question}</h3>",
            unsafe_allow_html=True,
        )

        if step == 1:
            for key, label in EDU_LEVELS.items():
                if st.button(label, key=f"_onb_lvl_{key}", use_container_width=True):
                    draft["edu_level"] = key
                    draft["edu_field"] = None
                    # Middle/high school skip the field question entirely.
                    st.session_state[step_key] = 2 if needs_field(key) else 3
                    st.rerun()

        elif step == 2:
            for key, label in FIELDS.items():
                if st.button(label, key=f"_onb_field_{key}", use_container_width=True):
                    draft["edu_field"] = key
                    st.session_state[step_key] = 3
                    st.rerun()

        else:
            for key, label in STUDY_STYLES.items():
                if st.button(label, key=f"_onb_style_{key}", use_container_width=True):
                    _save_and_continue(
                        username,
                        draft.get("edu_level"),
                        draft.get("edu_field"),
                        key,
                    )

        st.write("")
        c_back, c_skip = st.columns(2)
        with c_back:
            if step > 1 and st.button("← Back", key="_onb_back", use_container_width=True):
                if step == 3 and needs_field(draft.get("edu_level")):
                    st.session_state[step_key] = 2
                else:
                    st.session_state[step_key] = 1
                st.rerun()
        with c_skip:
            if st.button("Skip for now", key="_onb_skip", use_container_width=True):
                _save_and_continue(username, None, None, None, skipped=True)


def render_profile_settings(username: str) -> None:
    """Editable version of the onboarding answers, used on the Settings page.

    Deliberately not an st.form: the field-of-study dropdown has to appear or
    disappear the moment the education level changes, and forms only update on
    submit.
    """
    profile = st.session_state.get("student_profile") or {}

    level_keys = list(EDU_LEVELS)
    cur_level  = profile.get("edu_level")
    level = st.selectbox(
        "Education level",
        level_keys,
        index=level_keys.index(cur_level) if cur_level in EDU_LEVELS else None,
        format_func=EDU_LEVELS.get,
        placeholder="Choose one…",
        key="_prof_level",
    )

    field = None
    if needs_field(level):
        field_keys = list(FIELDS)
        cur_field  = profile.get("edu_field")
        field = st.selectbox(
            "Field of study",
            field_keys,
            index=field_keys.index(cur_field) if cur_field in FIELDS else None,
            format_func=FIELDS.get,
            placeholder="Choose one…",
            key="_prof_field",
        )

    style_keys = list(STUDY_STYLES)
    cur_style  = profile.get("study_style")
    style = st.selectbox(
        "Study style",
        style_keys,
        index=style_keys.index(cur_style) if cur_style in STUDY_STYLES else None,
        format_func=STUDY_STYLES.get,
        placeholder="Choose one…",
        key="_prof_style",
    )

    if st.button("Save study profile", type="primary", key="_prof_save"):
        if not level or not style or (needs_field(level) and not field):
            st.error("Please answer every question shown above.")
            return
        try:
            save_user_profile(username, level, field, style, onboarding_done=True)
        except Exception:
            logger.error("save_user_profile failed for '%s'", username, exc_info=True)
            st.error("Couldn't save your profile. Please try again.")
            return
        st.session_state["student_profile"] = {
            "edu_level": level,
            "edu_field": field,
            "study_style": style,
            "onboarding_done": True,
        }
        _track("profile_updated", username, {
            "edu_level": level, "edu_field": field, "study_style": style,
        })
        st.success("Study profile updated. Your next guide or quiz will use it.")

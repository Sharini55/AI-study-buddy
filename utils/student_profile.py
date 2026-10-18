"""Student profile (education level / field / study style) -> LLM prompt context.

Stored values are stable keys (e.g. "middle_school"), not display labels, so the
UI wording can change later without orphaning profiles already saved in the DB.
"""

EDU_LEVELS = {
    "middle_school": "Middle School (6th–8th grade)",
    "high_school":   "High School (9th–12th grade)",
    "undergrad":     "Undergraduate",
    "grad":          "Graduate / Postgrad",
    "professional":  "Professional (pre-med, law, CPA, etc.)",
}

# Only these levels are asked for a field of study.
COLLEGE_PLUS = ("undergrad", "grad", "professional")

FIELDS = {
    "stem":       "STEM",
    "business":   "Business",
    "humanities": "Humanities",
    "medicine":   "Medicine",
    "law":        "Law",
    "other":      "Other",
}

STUDY_STYLES = {
    "detailed": "I like detailed explanations with examples",
    "concise":  "Give me the key points fast",
    "test_me":  "Test me, don't just tell me",
}

# Undergrad and above intentionally have no entry: they get the default behavior.
LEVEL_GUIDANCE = {
    "middle_school": (
        "Explain concepts simply, avoid jargon (briefly define any term you must "
        "use), use relatable everyday examples, and keep sentences short."
    ),
    "high_school": (
        "Use clear, accessible language, briefly define technical terms the first "
        "time they appear, and keep examples at a moderate level of complexity."
    ),
}

STYLE_GUIDANCE = {
    "detailed": "Detailed explanations, each backed by a concrete example.",
    "concise":  "Key points first, with minimal elaboration.",
    "test_me":  "Active recall: favor practice problems and challenge questions over exposition.",
}


def needs_field(level: str | None) -> bool:
    return level in COLLEGE_PLUS


def build_student_context(profile: dict | None) -> str:
    """Return a prompt block describing the student, or "" if nothing is known.

    Returning "" for an empty profile means skipped/legacy users get exactly the
    prompts they get today.
    """
    if not profile:
        return ""

    level = profile.get("edu_level")
    field = profile.get("edu_field")
    style = profile.get("study_style")
    if level not in EDU_LEVELS and style not in STUDY_STYLES:
        return ""

    lines = ["STUDENT PROFILE (this changes HOW you explain, never WHAT is true):"]
    if level in EDU_LEVELS:
        lines.append(f"- Education level: {EDU_LEVELS[level]}")
        if needs_field(level) and field in FIELDS:
            lines.append(f"- Field of study: {FIELDS[field]}")
        if level in LEVEL_GUIDANCE:
            lines.append(f"- {LEVEL_GUIDANCE[level]}")
    if style in STUDY_STYLES:
        lines.append(f"- Preferred style: {STYLE_GUIDANCE[style]}")
    lines.append("- Adjust vocabulary, depth, and examples to match this profile.")
    lines.append(
        "- Every fact must still come from the workspace materials. If this profile "
        "conflicts with the length or format rules in the task below, the task's "
        "rules win."
    )
    return "\n".join(lines)


def with_student_context(prompt: str, profile: dict | None = None) -> str:
    """Prepend the student-context block to any prompt. No-op if no profile.

    Wrap at the call site, e.g. with_student_context(guide_prompt(...)).
    """
    if profile is None:
        import streamlit as st
        profile = st.session_state.get("student_profile")
    ctx = build_student_context(profile)
    return f"{ctx}\n\n{prompt}" if ctx else prompt


def load_profile_into_session(username: str) -> None:
    """Load this user's profile into session_state once per user.

    Keyed by username so a different account logging in within the same browser
    session never inherits the previous user's profile.
    """
    import streamlit as st
    if st.session_state.get("_profile_user") != username:
        from utils.persistence import get_user_profile
        st.session_state["student_profile"] = get_user_profile(username)
        st.session_state["_profile_user"] = username

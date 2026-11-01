"""
utils/content_quality.py
Checks whether indexed workspace text is rich enough to generate a
study guide, quiz, or adaptive study session without hallucinating.

Two failure modes are detected:
  1. Too short  — fewer than MIN_CHARS characters of total text.
  2. Keyword-list — text is long enough but made up of very short lines
     (1–4 words each) with almost no full sentences.  This catches the
     "biology keywords without definitions" pattern that caused the model
     to hallucinate earlier.

Public API
----------
check_content_quality(workspace) -> (is_usable: bool, reason: str)
    Call after every index_materials() call and store the result in
    session state.  Returns True + empty reason when the content is fine.
"""

from __future__ import annotations

# Minimum total characters of indexed text required.
MIN_CHARS = 400

# A "sentence-like" line has at least this many words.
SENTENCE_MIN_WORDS = 6

# If more than this fraction of non-blank lines are short (< SENTENCE_MIN_WORDS
# words), we flag the content as a keyword list.
MAX_SHORT_LINE_RATIO = 0.72

# We need at least this many non-blank lines to make the ratio meaningful.
MIN_LINES_FOR_RATIO_CHECK = 8


def check_content_quality(workspace: dict) -> tuple[bool, str]:
    """
    Returns (is_usable, reason).

    is_usable = True  → content is good, reason = ""
    is_usable = False → reason contains a user-facing explanation
    """
    text: str = workspace.get("processed_text", "") or ""
    text = text.strip()

    # ── Check 1: absolute length ──────────────────────────────────────────────
    if len(text) < MIN_CHARS:
        if not workspace.get("files"):
            return False, (
                "No materials indexed yet. Upload a file or paste your notes "
                "in the Ingest Material tab before generating."
            )
        return False, (
            f"Your indexed notes are too short ({len(text)} characters). "
            "AI Study Buddy works purely from the notes you provide — it does not "
            "browse the internet — so it needs enough material to generate from. "
            "Please add more text: full sentences, definitions, or a textbook "
            "passage work best."
        )

    # ── Check 2: keyword-list detection ──────────────────────────────────────
    lines = [ln.strip() for ln in text.splitlines()]
    non_blank = [ln for ln in lines if ln]

    if len(non_blank) >= MIN_LINES_FOR_RATIO_CHECK:
        short_lines = [ln for ln in non_blank if len(ln.split()) < SENTENCE_MIN_WORDS]
        ratio = len(short_lines) / len(non_blank)

        if ratio >= MAX_SHORT_LINE_RATIO:
            return False, (
                "Your notes look like a list of keywords or very short phrases "
                f"({int(ratio * 100)}% of lines have fewer than {SENTENCE_MIN_WORDS} words). "
                "AI Study Buddy does not use the internet — it generates entirely from "
                "what you index — so keyword lists without definitions or explanations "
                "aren't enough to produce a reliable study guide or quiz.\n\n"
                "**What to add:** paste notes with full sentences, definitions, "
                "or upload a PDF/PPTX with actual explanations. Even a few paragraphs "
                "from your textbook make a big difference."
            )

    return True, ""

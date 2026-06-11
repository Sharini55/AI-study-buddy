import re
from textwrap import dedent

import streamlit as st


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def guide_prompt(subject: str, workspace: dict, mode: str, has_images: bool = False) -> str:
    visual_instruction = ""
    if has_images:
        visual_instruction = (
            "Attached images may include slides, diagrams, figures, or visual examples. "
            "Incorporate and explain visual material where it supports the topic."
        )

    if mode == "Deep Dive":
        mode_instruction = dedent("""
            MODE: DEEP DIVE
            - Cover the 6 most important topics from the materials. No more than 6.
            - For each topic: full definition, one worked example with step-by-step annotation,
              one edge case or common mistake, and key implications.
            - Each section: 200-350 words maximum. Be thorough but tight.
        """).strip()
    else:
        mode_instruction = dedent("""
            MODE: CRAM MODE
            - Cover the 8 most important topics. No more than 8.
            - For each topic: one-line definition, key formula or rule, and one exam pitfall.
            - Each section: 60 words maximum. No prose. Bullets only.
        """).strip()

    return dedent(
        f"""
        You are an expert study guide writer. Create a study guide based STRICTLY on
        the workspace materials below. Do not add anything not present in the materials.
        Do not assume the subject domain — derive everything from the content.
        Never default to code unless the materials themselves contain code.

        {mode_instruction}

        {visual_instruction}

        For each topic output exactly this format:

        ## [Topic Name]
        **THE RULE**: Core concept and why it works.
        **THE GUIDED SOLVE**: A fully worked example matching the subject matter.
        **THE CHALLENGE**: A practice problem testing the concept.
        **[ANSWER]**: Complete worked answer.

        Workspace materials:
        {workspace["processed_text"] if workspace["processed_text"] else "No text extracted. Use attached images."}
        """
    ).strip()


def quiz_prompt(subject: str, workspace: dict) -> str:
    return dedent(
        f"""
        You are an expert quiz writer.
        Generate exactly 5 multiple-choice questions using ONLY the workspace materials below.
        Base every question strictly on content present in the materials.

        Return strict JSON only. No Markdown fences.
        Format:
        {{
          "questions": [
            {{
              "question": "Question text",
              "choices": ["A. ...", "B. ...", "C. ...", "D. ..."],
              "answer_index": 0,
              "topic": "Topic name",
              "explanation": "Why the correct answer is right"
            }}
          ]
        }}

        Workspace materials:
        {workspace["processed_text"] if workspace["processed_text"] else "No text extracted. Use attached images."}
        """
    ).strip()


def weak_area_guide_prompt(subject: str, workspace: dict, missed_questions: list[dict]) -> str:
    missed_text = "\n".join(
        f"- Topic: {q.get('topic','?')} | Question: {q.get('question','?')}" for q in missed_questions
    )
    return dedent(
        f"""
        You are an expert study guide writer.

        The student missed these questions:
        {missed_text}

        Generate a targeted remediation guide covering ONLY these weak areas,
        using ONLY content from the workspace materials below.
        Each section: 150-250 words maximum.

        ## [Topic Name]
        **THE RULE**: ...
        **THE GUIDED SOLVE**: ...
        **THE CHALLENGE**: ...
        **[ANSWER]**: ...

        Workspace materials:
        {workspace["processed_text"] if workspace["processed_text"] else "No text extracted. Use attached images."}
        """
    ).strip()


def targeted_quiz_prompt(subject: str, workspace: dict, missed_questions: list[dict]) -> str:
    topics = list({q.get("topic", "General") for q in missed_questions})
    return dedent(
        f"""
        You are an expert quiz writer.
        The student is weak on: {', '.join(topics)}.
        Generate exactly 5 multiple-choice questions targeting ONLY these topics,
        using ONLY content from the workspace materials below.

        Return strict JSON only. No Markdown fences.
        {{
          "questions": [
            {{
              "question": "Question text",
              "choices": ["A. ...", "B. ...", "C. ...", "D. ..."],
              "answer_index": 0,
              "topic": "Topic name",
              "explanation": "Why the correct answer is right"
            }}
          ]
        }}

        Workspace materials:
        {workspace["processed_text"] if workspace["processed_text"] else "No text extracted. Use attached images."}
        """
    ).strip()


# ---------------------------------------------------------------------------
# Guide rendering
# ---------------------------------------------------------------------------

def split_topics(markdown: str) -> list[dict[str, str]]:
    topics, current_title, current_lines = [], "", []
    for line in markdown.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            if current_title:
                topics.append(topic_from_lines(current_title, current_lines))
            current_title = heading.group(1).strip()
            current_lines = []
        elif current_title:
            current_lines.append(line)
    if current_title:
        topics.append(topic_from_lines(current_title, current_lines))
    return topics


def topic_from_lines(title: str, lines: list[str]) -> dict[str, str]:
    body = "\n".join(lines).strip()
    answer_match = re.search(
        r"(?:\*{0,2})\[ANSWER\](?:\*{0,2})\s*:?\s*|^#{1,3}\s*\[?ANSWER\]?\s*:?\s*",
        body,
        re.IGNORECASE | re.MULTILINE,
    )
    if not answer_match:
        return {"title": title, "body": body, "answer": "_No answer section returned._"}
    return {
        "title": title,
        "body": body[: answer_match.start()].strip(),
        "answer": body[answer_match.end():].strip(),
    }


def render_guide(markdown: str) -> None:
    topics = split_topics(markdown)
    if not topics:
        st.markdown(markdown)
        return
    for topic in topics:
        with st.expander(f"📖 {topic['title']}", expanded=False):
            st.markdown(topic["body"])
            st.divider()
            st.markdown("**✅ Answer**")
            if topic["answer"] and topic["answer"] != "_No answer section returned._":
                st.markdown(topic["answer"])
            else:
                st.caption("No answer section found for this topic.")

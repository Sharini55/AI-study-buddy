import datetime
import hashlib
import logging
import re
import time

import streamlit as st

from utils.gemini import call_gemini, describe_gemini_error
from utils.files import parse_json_response
from utils.guide import diagnostic_quiz_prompt, topic_quiz_prompt
from utils.agent import compute_mastery, decide_next_target, dynamic_question_count, MASTERY_THRESHOLD
from utils.metrics import log_metric

logger = logging.getLogger(__name__)

_PREFIX_RE = re.compile(r'^[A-Da-d]\.\s*')

_DIAGNOSTIC_QUESTIONS = 15


def _keys(wid: str) -> dict:
    return {
        "quiz":      f"adaptive_quiz_{wid}",
        "answers":   f"adaptive_answers_{wid}",
        "submitted": f"adaptive_submitted_{wid}",
        "target":    f"adaptive_target_{wid}",
        "attempt":   f"adaptive_attempt_{wid}",
    }


def _init_state(k: dict) -> None:
    st.session_state.setdefault(k["quiz"], [])
    st.session_state.setdefault(k["answers"], {})
    st.session_state.setdefault(k["submitted"], False)
    st.session_state.setdefault(k["target"], None)
    st.session_state.setdefault(k["attempt"], 0)


def _clear_round(k: dict) -> None:
    st.session_state[k["quiz"]] = []
    st.session_state[k["answers"]] = {}
    st.session_state[k["submitted"]] = False
    st.session_state[k["target"]] = None


def _render_progress_overview(mastery: dict, weak_topics: list, mastered_topics: list) -> None:
    total = len(mastery)
    if total == 0:
        return
    overall = len(mastered_topics) / total
    st.markdown(f"**Overall progress: {len(mastered_topics)}/{total} topics mastered**")
    st.progress(overall)

    with st.expander("Per-topic breakdown", expanded=False):
        for topic in sorted(mastery, key=lambda t: mastery[t].score):
            m = mastery[topic]
            label = f"{topic} — {m.score:.0f}/{MASTERY_THRESHOLD:.0f}"
            if m.score >= MASTERY_THRESHOLD:
                label += " ✅"
            st.caption(label)
            st.progress(min(1.0, m.score / MASTERY_THRESHOLD))


def _grade_and_store(workspace: dict, k: dict, quiz: list, topic: str) -> dict:
    answers = st.session_state[k["answers"]]
    correct, missed = 0, []
    for i, q in enumerate(quiz):
        if answers.get(str(i)) == q.get("answer_index"):
            correct += 1
        else:
            missed.append(q)
    score = round((correct / len(quiz)) * 100) if quiz else 0

    workspace.setdefault("quiz_history", []).append({
        "score": score,
        "questions": quiz,
        "answers": dict(answers),
        "missed_questions": missed,
    })
    st.session_state["is_dirty"] = True
    log_metric("adaptive_round_submitted", {
        "topic": topic, "score": score, "question_count": len(quiz),
    })
    return {"score": score, "correct": correct, "missed": missed}


def render_adaptive_study_tab(api_key: str, subject: str, workspace: dict) -> None:
    wid = workspace.get("id", subject)
    k = _keys(wid)
    _init_state(k)

    st.markdown("### 🎯 Adaptive Study")

    if not workspace.get("files"):
        st.warning("Add material in the Ingest Material tab first.")
        return
    if not api_key:
        st.warning("⚙ Enter your Gemini API key in Settings first.")
        return

    quiz_history = workspace.get("quiz_history", [])
    active_quiz = st.session_state[k["quiz"]]

    # ── Active round in progress: render it and stop ───────────────────────
    if active_quiz:
        _render_active_round(api_key, subject, workspace, k)
        return

    # ── No history yet: need the baseline diagnostic first ─────────────────
    if not quiz_history:
        st.caption(
            "This material hasn't been assessed yet. Run a quick diagnostic covering "
            "all its topics so the agent knows where to start."
        )
        if st.button("▶ Start Diagnostic Quiz", type="primary"):
            _start_diagnostic(api_key, subject, workspace, k)
        return

    # ── Have history: perceive + score + decide ─────────────────────────────
    mastery = compute_mastery(quiz_history)
    target = decide_next_target(mastery)
    mastered_topics = [t for t, m in mastery.items() if m.score >= MASTERY_THRESHOLD]
    weak_topics = [t for t, m in mastery.items() if m.score < MASTERY_THRESHOLD]

    _render_progress_overview(mastery, weak_topics, mastered_topics)
    st.divider()

    if target is None:
        st.success(
            "🎉 Great job — you've mastered every topic found in this material! "
            "Add more material if you'd like to keep going."
        )
        st.balloons()
        return

    n_questions = dynamic_question_count(target.score)
    st.info(
        f"**Focus: {target.topic}** — currently {target.score:.0f}/{MASTERY_THRESHOLD:.0f}. "
        f"Next round: **{n_questions} question(s)** (more questions while there's more ground to cover)."
    )
    if st.button(f"▶ Start round on \"{target.topic}\"", type="primary"):
        _start_focus_round(api_key, subject, workspace, k, target.topic, n_questions)


def _start_diagnostic(api_key: str, subject: str, workspace: dict, k: dict) -> None:
    username = st.session_state.get("username", "anonymous")
    with st.spinner(f"Generating a {_DIAGNOSTIC_QUESTIONS}-question diagnostic across your material…"):
        try:
            response_text = call_gemini(
                api_key,
                diagnostic_quiz_prompt(subject, workspace, _DIAGNOSTIC_QUESTIONS),
                workspace,
                metric_label="adaptive_diagnostic",
                username=username,
            )
            questions = parse_json_response(response_text).get("questions", [])[:_DIAGNOSTIC_QUESTIONS]
        except Exception as exc:
            logger.error("Diagnostic quiz generation failed: %s", exc, exc_info=True)
            st.error(describe_gemini_error(exc))
            return

    st.session_state[k["quiz"]] = questions
    st.session_state[k["answers"]] = {}
    st.session_state[k["submitted"]] = False
    st.session_state[k["target"]] = None  # None marks this as the diagnostic round
    st.session_state[k["attempt"]] += 1
    st.rerun()


def _start_focus_round(api_key: str, subject: str, workspace: dict, k: dict, topic: str, n_questions: int) -> None:
    username = st.session_state.get("username", "anonymous")
    with st.spinner(f"Generating {n_questions} question(s) on {topic}…"):
        try:
            response_text = call_gemini(
                api_key,
                topic_quiz_prompt(topic, subject, workspace, n_questions),
                workspace,
                metric_label="adaptive_focus_round",
                username=username,
            )
            questions = parse_json_response(response_text).get("questions", [])[:n_questions]
            # Force the exact topic label regardless of what the model returns —
            # otherwise this attempt could get bucketed under a different topic
            # string and the agent's own progress bar for `topic` would never move.
            for q in questions:
                q["topic"] = topic
        except Exception as exc:
            logger.error("Focus round generation failed: %s", exc, exc_info=True)
            st.error(describe_gemini_error(exc))
            return

    st.session_state[k["quiz"]] = questions
    st.session_state[k["answers"]] = {}
    st.session_state[k["submitted"]] = False
    st.session_state[k["target"]] = topic
    st.session_state[k["attempt"]] += 1
    st.rerun()


def _render_active_round(api_key: str, subject: str, workspace: dict, k: dict) -> None:
    quiz = st.session_state[k["quiz"]]
    topic = st.session_state[k["target"]]
    submitted = st.session_state[k["submitted"]]
    attempt_no = st.session_state[k["attempt"]]

    header = "Diagnostic Quiz" if topic is None else f"Focus Round — {topic}"
    st.markdown(f"#### {header}")
    st.caption(f"{len(quiz)} question(s)")

    for index, question in enumerate(quiz):
        choices = question.get("choices", [])
        st.markdown(f"**Q{index + 1}. {question.get('question', '')}**")
        if not choices:
            st.warning("This generated question did not include choices.")
            continue

        if submitted:
            user_idx = st.session_state[k["answers"]].get(str(index))
            correct_idx = question.get("answer_index", 0)
            is_correct = user_idx == correct_idx
            for ci, choice in enumerate(choices):
                marker = "✅" if ci == correct_idx else ("❌" if ci == user_idx else "⬜")
                st.markdown(f"{marker}&ensp;{_PREFIX_RE.sub('', choice)}")
            st.success("Correct!") if is_correct else st.error(f"Incorrect — correct answer: option {correct_idx + 1}")
            explanation = question.get("explanation", "")
            if explanation:
                st.info("💡 " + explanation)
        else:
            display_choices = [f"{chr(65 + i)}. {_PREFIX_RE.sub('', c)}" for i, c in enumerate(choices)]
            radio_key = f"adaptive_q_{k['quiz']}_{index}_attempt_{attempt_no}"
            selected = st.radio(
                "Choose one", display_choices, index=None, key=radio_key, label_visibility="collapsed",
            )
            if selected is not None:
                idx = next((i for i, d in enumerate(display_choices) if d == selected), None)
                if idx is not None:
                    st.session_state[k["answers"]][str(index)] = idx
        st.markdown("---")

    if not submitted:
        if st.button("Submit", type="primary"):
            unanswered = [i for i in range(len(quiz)) if str(i) not in st.session_state[k["answers"]]]
            if unanswered:
                st.warning(f"Answer all questions first. Unanswered: Q{', Q'.join(str(u + 1) for u in unanswered)}")
                return

            if topic is None:
                # Diagnostic: just record it, no single-topic grading needed —
                # compute_mastery() will bucket every question by its own topic.
                answers = st.session_state[k["answers"]]
                correct = sum(
                    1 for i, q in enumerate(quiz) if answers.get(str(i)) == q.get("answer_index")
                )
                score = round((correct / len(quiz)) * 100) if quiz else 0
                missed = [q for i, q in enumerate(quiz) if answers.get(str(i)) != q.get("answer_index")]
                workspace.setdefault("quiz_history", []).append({
                    "score": score, "questions": quiz, "answers": dict(answers), "missed_questions": missed,
                })
                st.session_state["is_dirty"] = True
                log_metric("adaptive_diagnostic_submitted", {"score": score, "question_count": len(quiz)})
            else:
                _grade_and_store(workspace, k, quiz, topic)

            st.session_state[k["submitted"]] = True
            st.rerun()
    else:
        st.divider()
        if st.button("🎯 Continue", type="primary"):
            _clear_round(k)
            st.rerun()

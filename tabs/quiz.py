import datetime
import hashlib
import logging
import os
import re
import time

import streamlit as st

_PREFIX_RE = re.compile(r'^[A-Da-d]\.\s*')

from utils.gemini import call_gemini, generate_remediation_pooled, describe_gemini_error
from utils.files import parse_json_response
from utils.guide import quiz_prompt, targeted_quiz_prompt, render_guide
from utils.metrics import log_metric, report_generation_metrics
from utils.agent import loop_status, MASTERY_THRESHOLD

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared key + quota helpers (same pattern as study.py)
# ---------------------------------------------------------------------------
_SHARED_KEY = os.environ.get("SHARED_GEMINI_KEY", "")

# ---------------------------------------------------------------------------
# Question count selection
# ---------------------------------------------------------------------------
QUESTION_COUNT_OPTIONS = [5, 10, 15, 20]
_DEFAULT_QUESTION_COUNT = 5


def _max_supported_questions(workspace: dict) -> int:
    """
    Rough content-length heuristic for how many quiz questions the uploaded
    material can reasonably support without questions repeating or the
    model stretching thin/fabricating. Uses workspace['processed_text'],
    the same field every prompt in utils.guide actually sends to Gemini.

    ~4 chars/token is the same rule of thumb utils.metrics._count_tokens
    uses elsewhere in this app. Thresholds below are a starting heuristic,
    not derived from testing — tune once you see how real material sizes
    map to question quality.
    """
    text = workspace.get("processed_text") or ""
    tokens = len(text) // 4
    if tokens < 400:
        return 5
    if tokens < 1000:
        return 10
    if tokens < 2000:
        return 15
    return QUESTION_COUNT_OPTIONS[-1]


def _render_question_count_selector(wid: str, workspace: dict) -> int:
    """Renders the 5/10/15/20 picker, greying out counts the material can't
    support, and returns the currently selected (and clamped) count."""
    count_key = f"_quiz_count_{wid}"
    max_supported = _max_supported_questions(workspace)

    st.session_state.setdefault(count_key, _DEFAULT_QUESTION_COUNT)
    if st.session_state[count_key] > max_supported:
        st.session_state[count_key] = max_supported

    st.markdown(
        "<p style='font-weight:600;color:#242B18;font-family:Truculenta,sans-serif;"
        "margin-bottom:4px;'>Number of questions</p>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(QUESTION_COUNT_OPTIONS))
    for i, n in enumerate(QUESTION_COUNT_OPTIONS):
        with cols[i]:
            is_selected = st.session_state[count_key] == n
            is_disabled = n > max_supported
            if st.button(
                str(n),
                key=f"_qcount_{wid}_{n}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
                disabled=is_disabled,
            ):
                st.session_state[count_key] = n
                st.rerun()

    if max_supported < QUESTION_COUNT_OPTIONS[-1]:
        st.caption(
            f"📄 Your uploaded material looks fairly short — {max_supported} "
            f"question{'s' if max_supported != 1 else ''} is the most we'd recommend "
            f"right now. Add more material to unlock higher counts."
        )

    return st.session_state[count_key]


def _get_effective_api_key() -> tuple[str, bool]:
    user_key = st.session_state.get("gemini_api_key", "").strip()
    if user_key:
        return user_key, True
    return _SHARED_KEY, False


def _quota_banner(usage: dict) -> None:
    remaining = usage["quizzes_remaining"]
    total     = usage["quiz_limit"]
    if remaining == total:
        color, msg = "#ABC270", f"✨ You have {remaining} free quiz generation{'s' if remaining != 1 else ''} today"
    elif remaining > 0:
        color, msg = "#D9A441", f"⚡ {remaining} of {total} free quiz generation{'s' if remaining != 1 else ''} left today"
    else:
        color, msg = "#C0392B", "🔒 Daily quiz limit reached"
    st.markdown(
        f"<div style='display:inline-block;background:{color}22;border:1.5px solid {color};"
        f"border-radius:999px;padding:4px 14px;font-size:0.82rem;font-weight:600;"
        f"color:{color};margin-bottom:0.75rem;font-family:Truculenta,sans-serif;'>"
        f"{msg}</div>",
        unsafe_allow_html=True,
    )


def _limit_reached_ui() -> None:
    st.markdown(
        """
        <div style="background:#FFF8F8;border:2px solid #C0392B;border-radius:14px;
                    padding:1.25rem 1.5rem;margin-bottom:1rem;">
          <strong style="color:#C0392B;font-family:'Truculenta',sans-serif;font-size:1rem;">
            🔒 You've used your 2 free quiz generations for today
          </strong>
          <p style="color:#5C6A48;font-family:'Truculenta',sans-serif;font-size:0.9rem;
                    margin:0.5rem 0 0;">
            Come back tomorrow — or paste your own free Gemini API key in
            <strong>Settings</strong> to generate unlimited quizzes.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Go to Settings →", type="primary", key="quota_settings_quiz"):
        st.session_state["current_page"] = "Settings"
        st.rerun()


def _missed_questions_for_topic(quiz_history: list[dict], topic: str) -> list[dict]:
    found = [
        q for attempt in quiz_history
        for q in attempt.get("missed_questions", [])
        if q.get("topic", "General") == topic
    ]
    return found or [{"topic": topic, "question": f"General review of {topic}"}]


def _save_agent_guide(subject: str, topic: str, content: str) -> None:
    guide_id = f"agent-{hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]}"
    existing_ids = {g["id"] for g in st.session_state.get("saved_guides", [])}
    if guide_id not in existing_ids:
        st.session_state.setdefault("saved_guides", []).append({
            "id": guide_id,
            "title": f"{subject} — 🤖 Agent: {topic}",
            "subject": subject,
            "content": content,
            "saved_at": datetime.datetime.now().strftime("%b %d, %H:%M"),
        })


def render_agent_panel(api_key: str, subject: str, workspace: dict) -> None:
    quiz_history = workspace.get("quiz_history", [])
    status = loop_status(quiz_history)

    st.markdown("#### 🤖 Autonomous Study Agent")

    if not quiz_history:
        st.caption("Take a quiz first — the agent needs at least one attempt to perceive weak areas.")
        return

    if not status["should_continue"]:
        st.success("✅ Agent found nothing below mastery threshold — every topic seen so far is solid.")
        return

    target = status["next_target"]
    score = status["next_target_score"]
    mastered_n = len(status["mastered_topics"])
    weak_n = len(status["weak_topics"])

    st.info(
        f"**Next target: {target}** (mastery {score:.0f}/{MASTERY_THRESHOLD:.0f}) — "
        f"chosen autonomously from {mastered_n + weak_n} topic(s) seen so far "
        f"({mastered_n} mastered, {weak_n} still weak)."
    )

    if st.button(f"🤖 Act: Generate targeted guide + quiz for \"{target}\"", type="primary"):
        effective_key, _ = _get_effective_api_key()
        if not workspace.get("files"):
            st.warning("Add material in the Ingest Material tab first.")
        elif not effective_key:
            st.warning("No API key available. Go to Settings and paste your free Gemini key.")
        else:
            missed_for_topic = _missed_questions_for_topic(quiz_history, target)
            username = st.session_state.get("username", "anonymous")

            with st.spinner(f"Generating targeted guide for {target}…"):
                try:
                    guide = generate_remediation_pooled(
                        effective_key, subject, workspace, missed_for_topic,
                        batch_size=1, username=username,
                    )
                    _save_agent_guide(subject, target, guide)
                except Exception as exc:
                    logger.error("Agent guide generation failed: %s", exc, exc_info=True)
                    st.error(describe_gemini_error(exc))
                    return

            with st.spinner(f"Generating follow-up quiz on {target}…"):
                try:
                    response_text = call_gemini(
                        effective_key,
                        targeted_quiz_prompt(subject, workspace, missed_for_topic),
                        workspace,
                        metric_label="agent_quiz",
                        username=username,
                    )
                    new_questions = parse_json_response(response_text).get("questions", [])[:5]
                except Exception as exc:
                    logger.error("Agent quiz generation failed: %s", exc, exc_info=True)
                    st.error(describe_gemini_error(exc))
                    return

            wid = workspace.get("id", subject)
            st.session_state[f"quiz_{wid}"] = new_questions
            st.session_state[f"answers_{wid}"] = {}
            st.session_state[f"submitted_{wid}"] = False
            st.session_state[f"post_quiz_{wid}"] = None
            st.session_state[f"agent_quiz_{wid}"] = True
            workspace["quiz_attempt_counter"] = workspace.get("quiz_attempt_counter", 0) + 1

            log_metric("agent_decision", {
                "subject": subject,
                "target_topic": target,
                "mastery_score": score,
                "mastered_count": mastered_n,
                "weak_count": weak_n,
            }, username=username)

            st.success(f"Guide generated and saved. Quiz on **{target}** is ready below — take it to close the loop.")
            st.rerun()

    st.divider()


def render_quiz_tab(api_key_unused: str, subject: str, workspace: dict) -> None:
    """api_key_unused kept for signature compatibility — resolved internally."""
    from utils.metrics import get_daily_usage

    wid = workspace.get("id", subject)
    quiz_key      = f"quiz_{wid}"
    answer_key    = f"answers_{wid}"
    submitted_key = f"submitted_{wid}"
    post_quiz_key = f"post_quiz_{wid}"

    st.session_state.setdefault(quiz_key, [])
    st.session_state.setdefault(answer_key, {})
    st.session_state.setdefault(submitted_key, False)
    st.session_state.setdefault(post_quiz_key, None)
    st.session_state.setdefault(f"agent_quiz_{wid}", False)

    effective_key, using_own_key = _get_effective_api_key()
    username = st.session_state.get("username", "anonymous")

    # ── Question count picker ────────────────────────────────────────────────
    selected_count = _render_question_count_selector(wid, workspace)

    # ── Quota gate ─────────────────────────────────────────────────────────
    if not using_own_key:
        usage = get_daily_usage(username)
        _quota_banner(usage)
        quiz_blocked = usage["quizzes_remaining"] <= 0
    else:
        usage = None
        quiz_blocked = False

    # ── Generate quiz ───────────────────────────────────────────────────────
    if quiz_blocked:
        _limit_reached_ui()
    elif st.button("Generate Quiz", type="primary"):
        if not effective_key:
            st.warning("No API key available. Go to Settings and paste your free Gemini key.")
        elif not workspace["files"]:
            st.warning("Add material in the Ingest Material tab first.")
        else:
            with st.spinner(f"Generating {selected_count}-question quiz..."):
                try:
                    t_start = time.perf_counter()
                    _qprompt = quiz_prompt(subject, workspace, num_questions=selected_count)
                    response_text = call_gemini(
                        effective_key, _qprompt, workspace,
                        metric_label="quiz_generation",
                    )
                    ttv = round(time.perf_counter() - t_start, 2)

                    st.session_state[quiz_key] = parse_json_response(response_text).get("questions", [])[:selected_count]
                    st.session_state[answer_key] = {}
                    st.session_state[submitted_key] = False
                    st.session_state[post_quiz_key] = None
                    st.session_state[f"agent_quiz_{wid}"] = False
                    workspace["quiz_attempt_counter"] = workspace.get("quiz_attempt_counter", 0) + 1

                    report_generation_metrics(
                        label="Quiz Generation", subject=subject, mode="N/A",
                        prompt_text=_qprompt, output_text=response_text, elapsed_s=ttv,
                    )
                    st.rerun()
                except Exception as exc:
                    logger.error("Quiz generation failed: %s", exc, exc_info=True)
                    st.error(describe_gemini_error(exc))

    quiz = st.session_state[quiz_key]
    if not quiz:
        st.caption("Generate a quiz from the active workspace.")
        return

    submitted  = st.session_state[submitted_key]
    attempt_no = workspace.get("quiz_attempt_counter", 0)

    # ── Render questions ────────────────────────────────────────────────────
    for index, question in enumerate(quiz):
        choices = question.get("choices", [])
        st.markdown(f"**Q{index + 1}. {question.get('question', '')}**")
        if not choices:
            st.warning("This generated question did not include choices.")
            continue

        if submitted:
            user_idx    = st.session_state[answer_key].get(str(index))
            correct_idx = question.get("answer_index", 0)
            is_correct  = user_idx == correct_idx

            for ci, choice in enumerate(choices):
                if ci == correct_idx:
                    marker = "✅"
                elif ci == user_idx and not is_correct:
                    marker = "❌"
                else:
                    marker = "⬜"
                st.markdown(f"{marker}&ensp;{_PREFIX_RE.sub('', choice)}")

            if is_correct:
                st.success("Correct!")
            else:
                st.error(f"Incorrect — correct answer: option {correct_idx + 1}")
                st.markdown(f"&ensp;{_PREFIX_RE.sub('', choices[correct_idx])}")

            explanation = question.get("explanation", "")
            if explanation:
                st.info("💡 Explanation:")
                st.write(explanation)
        else:
            display_choices = [f"{chr(65 + i)}. {_PREFIX_RE.sub('', c)}" for i, c in enumerate(choices)]
            radio_key = f"q_{wid}_{index}_attempt_{attempt_no}"
            selected_display = st.radio(
                "Choose one",
                display_choices,
                index=None,
                key=radio_key,
                label_visibility="collapsed",
            )
            if selected_display is not None:
                selected_idx = next(
                    (i for i, d in enumerate(display_choices) if d == selected_display),
                    None,
                )
                if selected_idx is not None:
                    st.session_state[answer_key][str(index)] = selected_idx

        st.markdown("---")

    # ── Submit ──────────────────────────────────────────────────────────────
    if not submitted:
        if st.button("Submit Quiz", type="primary"):
            unanswered = [i for i in range(len(quiz)) if str(i) not in st.session_state[answer_key]]
            if unanswered:
                st.warning(
                    f"Please answer all questions before submitting. "
                    f"Unanswered: Q{', Q'.join(str(u + 1) for u in unanswered)}"
                )
            else:
                correct, missed = 0, []
                for index, question in enumerate(quiz):
                    if st.session_state[answer_key].get(str(index)) == question.get("answer_index"):
                        correct += 1
                    else:
                        missed.append(question)

                score = round((correct / len(quiz)) * 100) if quiz else 0
                workspace["quiz_history"].append({
                    "score": score,
                    "questions": quiz,
                    "answers": dict(st.session_state[answer_key]),
                    "missed_questions": missed,
                })
                st.session_state[submitted_key] = True
                st.session_state[post_quiz_key] = {"score": score, "missed": missed}
                st.session_state["is_dirty"] = True
                log_metric("quiz_submitted", {"subject": subject, "score": score, "missed_count": len(missed)})
                st.rerun()

    # ── Post-quiz adaptive menu ─────────────────────────────────────────────
    if submitted and st.session_state[post_quiz_key]:
        result = st.session_state[post_quiz_key]
        score  = result["score"]
        missed = result["missed"]

        st.success(f"🎯 You scored **{score}%** ({len(quiz) - len(missed)}/{len(quiz)} correct)")

        if st.session_state.get(f"agent_quiz_{wid}"):
            st.info("🤖 Result recorded. Mastery updated — scroll up to see the agent's next move.")
            if score == 100:
                st.balloons()
            if st.button("🤖 Continue Agent Loop", type="primary"):
                st.rerun()
        elif missed:
            weak_topics = list({q.get("topic", "General") for q in missed})
            st.info(f"Weak areas identified: **{', '.join(weak_topics)}**")

            st.markdown("### What would you like to do next?")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📚 Review Weak Areas", type="primary", use_container_width=True):
                    n = len(weak_topics)
                    with st.spinner(f"Batching {n} weak topic(s) — generating remediation guide…"):
                        try:
                            guide = generate_remediation_pooled(
                                effective_key, subject, workspace, missed,
                                username=username,
                            )
                            workspace["weak_area_report"] = guide
                            log_metric("weak_area_guide_generated", {
                                "subject": subject,
                                "topics": weak_topics,
                                "topic_count": n,
                            })
                        except Exception as exc:
                            logger.error("Weak area guide failed: %s", exc, exc_info=True)
                            st.error(describe_gemini_error(exc))

            with col2:
                if st.button("🔄 Full Retake", use_container_width=True):
                    st.session_state[answer_key] = {}
                    st.session_state[submitted_key] = False
                    st.session_state[post_quiz_key] = None
                    workspace["quiz_attempt_counter"] = workspace.get("quiz_attempt_counter", 0) + 1
                    st.rerun()

            with col3:
                if st.button("🎯 Targeted Quiz", use_container_width=True):
                    with st.spinner("Generating targeted quiz..."):
                        try:
                            t_start = time.perf_counter()
                            response_text = call_gemini(
                                effective_key,
                                targeted_quiz_prompt(subject, workspace, missed),
                                workspace,
                                metric_label="targeted_quiz",
                            )
                            ttv = round(time.perf_counter() - t_start, 2)
                            log_metric("targeted_quiz_ttv", {"subject": subject, "ttv_seconds": ttv})
                            new_questions = parse_json_response(response_text).get("questions", [])[:5]
                            st.session_state[quiz_key] = new_questions
                            st.session_state[answer_key] = {}
                            st.session_state[submitted_key] = False
                            st.session_state[post_quiz_key] = None
                            workspace["quiz_attempt_counter"] = workspace.get("quiz_attempt_counter", 0) + 1
                            st.rerun()
                        except Exception as exc:
                            logger.error("Targeted quiz failed: %s", exc, exc_info=True)
                            st.error(describe_gemini_error(exc))

            if workspace.get("weak_area_report"):
                st.markdown("---")
                st.subheader(f"📖 Remediation Guide — {len(weak_topics)} Topic(s)")
                st.download_button(
                    "⬇ Download Remediation Guide (.md)",
                    data=workspace["weak_area_report"].encode("utf-8"),
                    file_name=f"{subject.lower().replace(' ', '_')}_remediation.md",
                    mime="text/markdown",
                )
                render_guide(workspace["weak_area_report"])
        else:
            st.balloons()
            st.success("Perfect score! 🎉 Try a new topic or upload more material.")

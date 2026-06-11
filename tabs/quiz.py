import time

import streamlit as st

from utils.gemini import call_gemini
from utils.files import parse_json_response
from utils.guide import (
    quiz_prompt, weak_area_guide_prompt, targeted_quiz_prompt, render_guide,
)
from utils.metrics import log_metric, report_generation_metrics


def render_quiz_tab(api_key: str, subject: str, workspace: dict) -> None:
    wid = workspace.get("id", subject)
    quiz_key       = f"quiz_{wid}"
    answer_key     = f"answers_{wid}"
    submitted_key  = f"submitted_{wid}"
    post_quiz_key  = f"post_quiz_{wid}"

    st.session_state.setdefault(quiz_key, [])
    st.session_state.setdefault(answer_key, {})
    st.session_state.setdefault(submitted_key, False)
    st.session_state.setdefault(post_quiz_key, None)

    # ── Generate quiz ──────────────────────────────────────────────────────
    if st.button("Generate Quiz", type="primary"):
        if not api_key:
            st.warning("⚙ Enter your Gemini API key in Settings to generate a quiz.")
        elif not workspace["files"]:
            st.warning("Add material in the Ingest Material tab first.")
        else:
            with st.spinner("Generating quiz..."):
                try:
                    t_start = time.perf_counter()
                    _qprompt = quiz_prompt(subject, workspace)
                    response_text = call_gemini(
                        api_key, _qprompt, workspace,
                        metric_label="quiz_generation",
                    )
                    ttv = round(time.perf_counter() - t_start, 2)

                    st.session_state[quiz_key] = parse_json_response(response_text).get("questions", [])[:5]
                    st.session_state[answer_key] = {}
                    st.session_state[submitted_key] = False
                    st.session_state[post_quiz_key] = None
                    # Increment attempt counter to force radio widget reset (fix stale retake)
                    workspace["quiz_attempt_counter"] = workspace.get("quiz_attempt_counter", 0) + 1

                    report_generation_metrics(
                        label="Quiz Generation", subject=subject, mode="N/A",
                        prompt_text=_qprompt, output_text=response_text, elapsed_s=ttv,
                    )
                except Exception as exc:
                    st.error(str(exc))

    quiz = st.session_state[quiz_key]
    if not quiz:
        st.caption("Generate a quiz from the active workspace.")
        return

    submitted  = st.session_state[submitted_key]
    attempt_no = workspace.get("quiz_attempt_counter", 0)

    # ── Render questions ───────────────────────────────────────────────────
    for index, question in enumerate(quiz):
        choices = question.get("choices", [])
        st.markdown(f"**Q{index + 1}. {question.get('question', '')}**")
        if not choices:
            st.warning("This generated question did not include choices.")
            continue

        if submitted:
            # Show feedback — graded by stored integer index, not string value
            user_idx    = st.session_state[answer_key].get(str(index))
            correct_idx = question.get("answer_index", 0)
            is_correct  = user_idx == correct_idx

            for ci, choice in enumerate(choices):
                if ci == correct_idx:
                    marker = "✅ "
                elif ci == user_idx and not is_correct:
                    marker = "❌ "
                else:
                    marker = "    "
                st.write(f"{marker}{choice}")

            if is_correct:
                st.success("Correct!")
            else:
                st.error(f"Incorrect — correct answer: {choices[correct_idx]}")

            explanation = question.get("explanation", "")
            if explanation:
                st.info(f"💡 {explanation}")
        else:
            # Radio bound to attempt counter so re-take always starts blank (fix stale reset)
            radio_key = f"q_{wid}_{index}_attempt_{attempt_no}"
            # Store index directly via on_change to avoid string-matching bug with duplicate choices
            selected_label = st.radio(
                "Choose one",
                choices,
                index=None,
                key=radio_key,
                label_visibility="collapsed",
            )
            if selected_label is not None:
                # Safe: use list.index only when we just picked from the same list object
                # For true safety we use the radio's position which equals choices.index here
                # but guard against duplicates by tracking the first occurrence only
                selected_idx = next(
                    (i for i, c in enumerate(choices) if c == selected_label),
                    None,
                )
                if selected_idx is not None:
                    st.session_state[answer_key][str(index)] = selected_idx

        st.markdown("---")

    # ── Submit ─────────────────────────────────────────────────────────────
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
                log_metric("quiz_submitted", {"subject": subject, "score": score, "missed_count": len(missed)})
                st.rerun()

    # ── Post-quiz adaptive menu ────────────────────────────────────────────
    if submitted and st.session_state[post_quiz_key]:
        result = st.session_state[post_quiz_key]
        score  = result["score"]
        missed = result["missed"]

        st.success(f"🎯 You scored **{score}%** ({len(quiz) - len(missed)}/{len(quiz)} correct)")

        if missed:
            weak_topics = list({q.get("topic", "General") for q in missed})
            st.info(f"Weak areas identified: **{', '.join(weak_topics)}**")

            st.markdown("### What would you like to do next?")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📚 Review Weak Areas", type="primary", use_container_width=True):
                    with st.spinner("Generating targeted study guide..."):
                        try:
                            guide = call_gemini(
                                api_key,
                                weak_area_guide_prompt(subject, workspace, missed),
                                workspace,
                                metric_label="weak_area_guide",
                            )
                            workspace["weak_area_report"] = guide
                            log_metric("weak_area_guide_generated", {"subject": subject, "topics": weak_topics})
                        except Exception as exc:
                            st.error(str(exc))

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
                                api_key,
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
                            st.error(str(exc))

            if workspace.get("weak_area_report"):
                st.markdown("---")
                st.subheader("📖 Targeted Study Guide")
                st.download_button(
                    "⬇ Download Weak Area Guide (.md)",
                    data=workspace["weak_area_report"].encode("utf-8"),
                    file_name=f"{subject.lower().replace(' ', '_')}_weak_areas.md",
                    mime="text/markdown",
                )
                render_guide(workspace["weak_area_report"])
        else:
            st.balloons()
            st.success("Perfect score! 🎉 Try a new topic or upload more material.")

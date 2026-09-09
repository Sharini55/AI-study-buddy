import streamlit as st

SUPPORTED_UPLOADS = ["pdf", "pptx", "jpg", "jpeg", "png"]


def workspace_summary(workspace: dict) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Pages / Slides", workspace["stats"]["slides"])
    col2.metric("Sections",       workspace["stats"]["chapters"])
    col3.metric("Sources",        len(workspace["files"]))


def render_ingest_tab(subject: str, workspace: dict, api_key: str) -> None:
    from utils.files import index_materials, blank_workspace

    left, right = st.columns([1, 1], gap="large")
    with left:
        uploaded_files = st.file_uploader(
            "Upload source files",
            type=SUPPORTED_UPLOADS,
            accept_multiple_files=True,
            key=f"uploader_{subject}",
            help="Accepted: PDF, PPTX, JPG, PNG · 200 MB per file",
        )

        # Show filenames immediately after selection so users know files landed
        if uploaded_files:
            st.markdown(
                "<div style='margin-top:8px;'>"
                + "".join(
                    f"<div style='display:flex;align-items:center;gap:6px;"
                    f"padding:4px 0;font-size:0.85rem;color:#5C6A48;'>"
                    f"<span style='color:#ABC270;font-size:1rem;'>✓</span> {f.name}"
                    f"</div>"
                    for f in uploaded_files
                )
                + "</div>",
                unsafe_allow_html=True,
            )

    with right:
        pasted_text = st.text_area(
            "Paste Text",
            height=240,
            placeholder="Paste textbook or notes content here...",
            key=f"textbook_{subject}",
        )

    col_index, col_reset = st.columns([2, 1])

    with col_index:
        if st.button("Index Materials", type="primary", use_container_width=True):
            from utils.analytics import capture
            username   = st.session_state.get("username", "anonymous")
            prev_count = len(workspace.get("files", []))
            index_materials(uploaded_files, pasted_text, workspace, subject, api_key)
            new_files = workspace.get("files", [])[prev_count:]
            for f in new_files:
                capture("document_uploaded", username, {
                    "subject":    subject,
                    "file_type":  f.get("type", "unknown"),
                    "file_name":  f.get("name", "unknown"),
                    "size_bytes": f.get("size", 0),
                })
            if pasted_text and pasted_text.strip():
                capture("document_uploaded", username, {
                    "subject":    subject,
                    "file_type":  "text_paste",
                    "file_name":  "pasted_text",
                    "size_bytes": len(pasted_text.encode("utf-8")),
                })

            # Just set a flag here — don't render the nav buttons inside this
            # block. st.button() only returns True on the single rerun where
            # it was clicked, so on the rerun triggered by clicking one of the
            # nav buttons below, THIS "Index Materials" button is False again
            # and this whole block (including the nav buttons' own click
            # handling) would never execute. The flag survives reruns; the
            # button click doesn't.
            if workspace.get("files"):
                st.session_state[f"_just_indexed_{subject}"] = True

    with col_reset:
        if st.button("🗑 Reset Workspace", use_container_width=True):
            st.session_state[f"_confirm_reset_{subject}"] = True
            st.session_state[f"_just_indexed_{subject}"] = False

    # ── Next-step guidance with navigation buttons ──────────────────────────
    # Lives OUTSIDE the "Index Materials" button's if-block on purpose (see
    # comment above) so each nav button's own click can actually be handled
    # on the rerun it triggers, instead of the whole section just disappearing.
    if st.session_state.get(f"_just_indexed_{subject}"):
        st.success("Materials indexed! What would you like to do next?")
        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button(
                "📖 Study Guide",
                use_container_width=True,
                type="primary",
                key="ingest_goto_guide",
            ):
                st.session_state["current_page"] = "Study guide"
                st.session_state[f"_just_indexed_{subject}"] = False
                st.rerun()
        with btn2:
            if st.button(
                "❓ Take a Quiz",
                use_container_width=True,
                type="primary",
                key="ingest_goto_quiz",
            ):
                st.session_state["current_page"] = "Quiz"
                st.session_state[f"_just_indexed_{subject}"] = False
                st.rerun()
        with btn3:
            if st.button(
                "🎯 Adaptive Study",
                use_container_width=True,
                key="ingest_goto_adaptive",
            ):
                st.session_state["current_page"] = "Adaptive Study"
                st.session_state[f"_just_indexed_{subject}"] = False
                st.rerun()

    # Two-step confirmation so a misclick doesn't nuke everything
    if st.session_state.get(f"_confirm_reset_{subject}"):
        st.warning(
            f"This will clear all indexed files, the study guide, and quiz history "
            f"for **{subject}**. This cannot be undone."
        )
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button(
                "Yes, reset everything",
                type="primary",
                use_container_width=True,
                key=f"confirm_yes_{subject}",
            ):
                fresh = blank_workspace()
                fresh["id"] = workspace.get("id", fresh["id"])
                workspace.clear()
                workspace.update(fresh)
                st.session_state.pop(f"_confirm_reset_{subject}", None)
                st.session_state[f"_just_indexed_{subject}"] = False
                st.toast(f"Workspace '{subject}' has been reset.", icon="🗑")
                st.rerun()
        with no_col:
            if st.button(
                "Cancel",
                use_container_width=True,
                key=f"confirm_no_{subject}",
            ):
                st.session_state.pop(f"_confirm_reset_{subject}", None)
                st.rerun()

    workspace_summary(workspace)

    for warning in sorted(set(workspace.get("visual_warnings", []))):
        st.warning(warning)

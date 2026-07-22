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

        # ── Show uploaded filenames clearly so users know files were received ──
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
            username  = st.session_state.get("username", "anonymous")
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

            # ── Guide user to next step after indexing ──
            if workspace.get("files"):
                st.success(
                    "Materials indexed! Head to **Study Guide** or **Quiz** in the sidebar to get started."
                )

    with col_reset:
        if st.button("🗑 Reset Workspace", use_container_width=True):
            st.session_state[f"_confirm_reset_{subject}"] = True

    if st.session_state.get(f"_confirm_reset_{subject}"):
        st.warning(
            f"This will clear all indexed files, the study guide, and quiz history "
            f"for **{subject}**. This cannot be undone."
        )
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button("Yes, reset everything", type="primary",
                         use_container_width=True, key=f"confirm_yes_{subject}"):
                fresh = blank_workspace()
                fresh["id"] = workspace.get("id", fresh["id"])
                workspace.clear()
                workspace.update(fresh)
                st.session_state.pop(f"_confirm_reset_{subject}", None)
                st.toast(f"Workspace '{subject}' has been reset.", icon="🗑")
                st.rerun()
        with no_col:
            if st.button("Cancel", use_container_width=True,
                         key=f"confirm_no_{subject}"):
                st.session_state.pop(f"_confirm_reset_{subject}", None)
                st.rerun()

    workspace_summary(workspace)

    for warning in sorted(set(workspace.get("visual_warnings", []))):
        st.warning(warning)

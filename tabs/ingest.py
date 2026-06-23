import streamlit as st

SUPPORTED_UPLOADS = ["pdf", "pptx", "jpg", "jpeg", "png"]


def workspace_summary(workspace: dict) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Pages / Slides", workspace["stats"]["slides"])
    col2.metric("Sections", workspace["stats"]["chapters"])
    col3.metric("Sources", len(workspace["files"]))


def render_ingest_tab(subject: str, workspace: dict, api_key: str) -> None:
    from utils.files import index_materials, blank_workspace

    left, right = st.columns([1, 1], gap="large")
    with left:
        uploaded_files = st.file_uploader(
            "Upload source files", type=SUPPORTED_UPLOADS, accept_multiple_files=True,
            key=f"uploader_{subject}", help="Accepted: PDF, PPTX, JPG, PNG.",
        )
    with right:
        pasted_text = st.text_area(
            "Paste Text", height=240,
            placeholder="Paste textbook or notes content here...",
            key=f"textbook_{subject}",
        )

    col_index, col_reset = st.columns([2, 1])
    with col_index:
        if st.button("Index Materials", type="primary", use_container_width=True):
            index_materials(uploaded_files, pasted_text, workspace, subject, api_key)

    with col_reset:
        if st.button("🗑 Reset Workspace", use_container_width=True):
            st.session_state[f"_confirm_reset_{subject}"] = True

    # Two-step confirmation so a misclick doesn't nuke everything
    if st.session_state.get(f"_confirm_reset_{subject}"):
        st.warning(
            f"This will clear all indexed files, the study guide, and quiz history "
            f"for **{subject}**. This cannot be undone."
        )
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button("Yes, reset everything", type="primary", use_container_width=True,
                         key=f"confirm_yes_{subject}"):
                from utils.persistence import delete_workspace_storage
                fresh = blank_workspace()
                # Preserve the workspace id so DB sync can still find the row
                workspace_id = workspace.get("id", fresh["id"])
                fresh["id"] = workspace_id
                # Remove DB file rows and physical images before clearing memory
                delete_workspace_storage(workspace_id)
                workspace.clear()
                workspace.update(fresh)
                st.session_state.pop(f"_confirm_reset_{subject}", None)
                st.session_state["is_dirty"] = True
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

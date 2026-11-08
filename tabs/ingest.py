import streamlit as st

SUPPORTED_UPLOADS = ["pdf", "pptx", "jpg", "jpeg", "png"]


def workspace_summary(workspace: dict) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Pages / Slides", workspace["stats"]["slides"])
    col2.metric("Sections",       workspace["stats"]["chapters"])
    col3.metric("Sources",        len(workspace["files"]))


def _run_quality_check(workspace: dict, subject: str) -> None:
    """Run the content quality check and store the result in session state."""
    from utils.content_quality import check_content_quality
    is_usable, reason = check_content_quality(workspace)
    st.session_state[f"_content_usable_{subject}"] = is_usable
    st.session_state[f"_content_reason_{subject}"] = reason


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

            # Images require a Gemini OCR call per file — show a spinner so
            # the UI doesn't appear frozen during the API call(s).
            image_files = [
                f for f in (uploaded_files or [])
                if f.name.rsplit(".", 1)[-1].lower() in {"jpg", "jpeg", "png"}
            ]
            if image_files:
                n = len(image_files)
                label = (
                    f"Reading {image_files[0].name}…"
                    if n == 1
                    else f"Analyzing {n} images with Gemini — this takes ~10–20 s per photo…"
                )
                with st.spinner(label):
                    index_materials(uploaded_files, pasted_text, workspace, subject, api_key)
            else:
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

            # Run quality check immediately after indexing so the flag is set
            # before the next-step nav buttons render.
            _run_quality_check(workspace, subject)

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
            # Clear quality flags on reset
            st.session_state.pop(f"_content_usable_{subject}", None)
            st.session_state.pop(f"_content_reason_{subject}", None)

    # ── Content quality warning ──────────────────────────────────────────────
    # Shown whenever the workspace has files but the quality check failed.
    # This persists across reruns because it reads from session_state flags
    # set by _run_quality_check() above.
    content_usable = st.session_state.get(f"_content_usable_{subject}", True)
    content_reason = st.session_state.get(f"_content_reason_{subject}", "")

    if workspace.get("files") and not content_usable and content_reason:
        st.markdown(
            f"""
            <div style="background:#FFF8F0;border:2px solid #D9A441;border-radius:14px;
                        padding:1rem 1.25rem;margin:0.75rem 0;">
              <strong style="color:#7A4E00;font-family:'Truculenta',sans-serif;font-size:0.95rem;">
                ⚠️ Notes need more detail to generate from
              </strong>
              <p style="color:#5C3B00;font-family:'Truculenta',sans-serif;font-size:0.88rem;
                        margin:0.4rem 0 0;white-space:pre-line;">
                {content_reason}
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Next-step guidance with navigation buttons ──────────────────────────
    # Lives OUTSIDE the "Index Materials" button's if-block on purpose (see
    # comment above) so each nav button's own click can actually be handled
    # on the rerun it triggers, instead of the whole section just disappearing.
    if st.session_state.get(f"_just_indexed_{subject}"):
        if content_usable:
            st.success("Materials indexed! What would you like to do next?")
        else:
            st.info("Materials indexed — add more detailed notes to unlock Study Guide, Quiz, and Adaptive Study.")

        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button(
                "📖 Study Guide",
                use_container_width=True,
                type="primary",
                key="ingest_goto_guide",
                disabled=not content_usable,
                help=None if content_usable else "Add more detailed notes first — see the warning above.",
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
                disabled=not content_usable,
                help=None if content_usable else "Add more detailed notes first — see the warning above.",
            ):
                st.session_state["current_page"] = "Quiz"
                st.session_state[f"_just_indexed_{subject}"] = False
                st.rerun()
        with btn3:
            if st.button(
                "🎯 Adaptive Study",
                use_container_width=True,
                key="ingest_goto_adaptive",
                disabled=not content_usable,
                help=None if content_usable else "Add more detailed notes first — see the warning above.",
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
                st.session_state.pop(f"_content_usable_{subject}", None)
                st.session_state.pop(f"_content_reason_{subject}", None)
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

    # ── Indexed sources list ─────────────────────────────────────────────────
    # Shows every file currently in the workspace so users know exactly what's
    # indexed. Each source can be removed individually without resetting everything.
    files = workspace.get("files", [])
    if files:
        st.markdown(
            "<div style='margin-top:1.2rem;margin-bottom:0.3rem;"
            "font-size:0.68rem;font-weight:700;color:#5C6A48;"
            "letter-spacing:1.6px;text-transform:uppercase;"
            "font-family:Truculenta,sans-serif;'>Indexed sources</div>",
            unsafe_allow_html=True,
        )
        for i, file_item in enumerate(list(files)):  # copy so removal during iteration is safe
            fname = file_item.get("name", "Unknown")
            ftype = file_item.get("type", "").upper()
            fsize = file_item.get("size", 0)
            size_str = f"{fsize / 1024:.0f} KB" if fsize < 1_048_576 else f"{fsize / 1_048_576:.1f} MB"
            icon = {
                "pdf": "📄", "pptx": "📊", "png": "🖼", "jpg": "🖼", "jpeg": "🖼",
                "text_paste": "📝",
            }.get(file_item.get("type", ""), "📎")

            col_name, col_remove = st.columns([9, 1])
            with col_name:
                st.markdown(
                    f"<div style='padding:6px 10px;border-radius:8px;"
                    f"border:1px solid #C5D99A;background:#FFFFFF;"
                    f"font-family:Truculenta,sans-serif;font-size:0.85rem;"
                    f"color:#242B18;display:flex;align-items:center;gap:8px;'>"
                    f"{icon} <strong>{fname}</strong>"
                    f"<span style='color:#5C6A48;font-size:0.78rem;margin-left:auto;'>{ftype} · {size_str}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_remove:
                if st.button("✕", key=f"_rm_src_{subject}_{i}", help=f"Remove {fname}"):
                    workspace["files"] = [f for f in workspace["files"] if f.get("id") != file_item.get("id")]
                    from utils.files import refresh_processed_text
                    refresh_processed_text(workspace)
                    st.session_state["is_dirty"] = True
                    # Clear quality flags so they re-evaluate on next index
                    st.session_state.pop(f"_content_usable_{subject}", None)
                    st.session_state.pop(f"_content_reason_{subject}", None)
                    st.session_state.pop(f"_just_indexed_{subject}", None)
                    st.toast(f"Removed {fname}")
                    st.rerun()

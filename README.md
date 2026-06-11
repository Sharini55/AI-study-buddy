# SunDevil AI

A professional Streamlit workspace for uploading course material and generating Gemini-powered study guides and quizzes with the unified `google-genai` SDK.

## Features

- Notion-style subject workspaces stored in `st.session_state["workspaces"]`.
- Sidebar workspace creation, switching, and deletion.
- Warm cream/sage UI with rounded panels and muted gold actions.
- Gemini key is hidden in the sidebar Settings expander.
- Uses `models/gemini-3.5-flash`.
- Tabs: Ingest Material, Study Guide, and Interactive Quiz.
- Workspace-scoped upload for PDF, PPTX, JPG, and PNG files.
- Image uploads are resized to 1024px max before Gemini slide/code/diagram analysis.
- Zybooks/textbook content can be pasted directly into the ingest workflow.
- Each workspace stores `files`, `processed_text`, `quiz_history`, and `generated_notes`.
- Raw extracted text is not displayed in the UI; users see a workspace-loaded summary instead.
- Study Mode selection:
  - Deep Dive: practice problems, theory, and step-by-step reasoning.
  - Cram Mode: summaries, shortcuts, and "The Rule".
- Topic sections render THE RULE, THE GUIDED SOLVE, THE CHALLENGE, and a hidden answer expander.
- Quiz mode generates five multiple-choice questions and flags weak areas below 60%.
- Study guides export as Markdown.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Add your Gemini API key in the sidebar, or set `GEMINI_API_KEY` before running.

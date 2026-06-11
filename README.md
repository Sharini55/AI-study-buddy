# SunDevil AI ☀️😈

SunDevil AI is a specialized educational platform designed to bridge the gap between static STEM slide decks (CSE 230, MAT 243, and beyond) and active recall learning. Unlike general AI chat interfaces, SunDevil AI isolates subject contexts into Notion-style workspaces and uses an adaptive remediation loop to zero in on a student's weak areas — then attack them.

---

## 📊 Real-World Performance Metrics

These numbers come from live usage logs captured by the built-in metrics pipeline, aggregated across actual student sessions.

### Document Ingestion
| Metric | Value |
|---|---|
| Avg parse completeness | **101.1%** (cleaning never loses content) |
| Avg content density | **1,428 chars / page** |
| Avg parse time per file | **~48ms** |
| Avg pages indexed per session | **~10 pages** |

### AI Generation (Deep Dive Mode)
| Metric | Value |
|---|---|
| Avg study guide length | **~10,300 words** per guide |
| Avg output / input token ratio | **4.6×** (model expands on your material, not just summarizes) |
| Avg generation latency | **~91s** (long-form; expected for full guides) |
| Avg cost per study guide | **~$0.004** |
| Estimated cost per 1,000 guides | **~$4.38** |

> These metrics are logged automatically per user under `.metrics/<username>/metrics_report.md` and surfaced in the Admin Dashboard.

---

## 🚀 Key Features

### 🗂 Subject Workspaces
Each course lives in its own isolated workspace (e.g., CSE 230, MAT 243, Physics). Files, guides, and quiz history never bleed across subjects. Workspaces persist to SQLite and reload on next login — no re-uploading needed.

### 📄 Multimodal Ingestion
Drag in PDFs, PowerPoints, or raw images (JPG/PNG). The pipeline extracts and cleans text from every page or slide, validates embedded images, and feeds both to the model. Pasting textbook excerpts directly is also supported.

Supported formats: `PDF`, `PPTX`, `JPG`, `PNG`

### 📚 Study Guide Generation (Deep Dive + Cram Mode)
Two generation modes built around cognitive science:

- **Deep Dive** — 6 core topics, each with a full definition, a worked example, an edge case, and a practice problem with answer. Avg output: ~10,300 words.
- **Cram Mode** — 8 topics, each in ≤60 words: one-line definition, key formula, one exam pitfall. Bullets only.

Guides are saved per workspace in the database and can be downloaded as `.md` files.

### 🧠 Adaptive Quiz + Remediation Loop
Generate a 5-question multiple-choice quiz from your indexed material. After submitting:
- The app identifies weak topics from missed questions
- You can immediately generate a **targeted remediation study guide** covering only those topics
- Or fire a **targeted quiz** that drills the same weak areas with fresh questions
- Full quiz history (score, questions, your answers) is persisted to the database

### 🔐 Authentication & Secure Accounts
Full username/password auth with PBKDF2-SHA256 salted hashing (100,000 iterations). Password requirements enforced at registration: 8+ characters, at least one number, at least one special character. Each user's data is fully isolated — no cross-account access possible.

Profile page includes:
- Account stats (workspaces, guides generated, quizzes taken)
- In-app password change
- Full account deletion with username-confirmation guard

### 🗄 Persistent SQLite Database
Six tables tracked via SQLAlchemy ORM:

| Table | Purpose |
|---|---|
| `users` | Credentials and account metadata |
| `workspaces` | Per-subject containers tied to a user |
| `source_files` | Extracted + cleaned text from every uploaded file |
| `source_images` | Slide image locations on disk (faux object storage) |
| `study_guides` | Generated guide markdown, versioned per workspace |
| `quiz_attempts` | Score, full question JSON, and student answer JSON |

Images are stored to disk at `./.storage/images/` rather than bloating the database with binary blobs.

### 📊 Built-In Metrics Pipeline
Every parse and every AI generation appends a structured entry to a per-user markdown report under `.metrics/<username>/metrics_report.md`. Tracked automatically:
- Parse completeness, density, and timing per file
- AI latency (time-to-value), token counts, and estimated cost per call
- Quiz submissions with subject and score

### 🛠 Admin Dashboard
A privileged admin account gets a full dashboard with three tabs:
- **Database Inspector** — spreadsheet audit of all six SQL tables live
- **User Metrics** — per-user metrics report viewer with download
- **Users** — list of all registered users with workspace counts and registration dates

### 🎨 Sanctuary UI Theme
Warm pastel palette (cream backgrounds, maroon and gold accents — ASU colors) intentionally designed to reduce pre-exam cognitive fatigue. All color tokens are CSS variables; dark-mode artifacts are explicitly overridden.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend / UI | Streamlit |
| LLM Engine | Google Gemini 2.5 Flash |
| SDK | `google-genai` (unified) |
| PDF extraction | PyMuPDF (`fitz`) |
| PPTX extraction | `python-pptx` |
| Image processing | Pillow |
| Database ORM | SQLAlchemy + SQLite |
| Password security | PBKDF2-HMAC-SHA256 (100k iterations) |
| State management | Streamlit Session State + SQLite sync |

---

## 🚀 Running Locally

### Step 1 — Install Python 3.9+
**Mac:** Verify with `python3 --version`. Install via [Homebrew](https://brew.sh) or [python.org](https://python.org) if needed.  
**Windows:** Download from [python.org](https://python.org). During install, check **"Add Python to PATH"**.

### Step 2 — Get the code
```bash
git clone https://github.com/YOUR_USERNAME/sundevil-ai.git
cd sundevil-ai
```
Or click **Code → Download ZIP** on GitHub and extract it.

### Step 3 — Create and activate a virtual environment
**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```
You'll see `(venv)` appear in your terminal when it's active.

### Step 4 — Install dependencies
```bash
pip install streamlit google-genai pymupdf pillow python-pptx sqlalchemy
```

### Step 5 — Launch
```bash
streamlit run app.py
```
Opens automatically at `http://localhost:8501`.

---

## ⚙️ Getting a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Sign in with any Google account
3. Click **Get API Key → Create API Key** and copy the string
4. In SunDevil AI, open **⚙ Settings** in the sidebar and paste your key

The free tier is sufficient for personal study use.

---

## 🗂 Project Structure

```
sundevil-ai/
├── app.py              # Main entry point, routing, sidebar, DB sync
├── tabs/
│   ├── ingest.py       # File upload + text paste UI
│   ├── study.py        # Study guide generation tab
│   └── quiz.py         # Quiz generation, grading, remediation loop
├── utils/
│   ├── auth.py         # Login, signup, password validation, session management
│   ├── persistence.py  # SQLAlchemy models, password hashing, image storage
│   ├── files.py        # PDF/PPTX/image parsers, workspace helpers
│   ├── guide.py        # Prompt templates, guide renderer
│   ├── gemini.py       # Gemini client, retry logic, image payload builder
│   └── metrics.py      # Per-user parse + generation metrics logging
├── sundevil_ai.db      # SQLite database (auto-created on first run)
└── .metrics/           # Per-user metrics reports (auto-created)
```

---

## 🔒 Security Notes

- Passwords are never stored in plaintext. PBKDF2-HMAC-SHA256 with a random 16-byte salt and 100,000 iterations.
- Each user's workspaces, files, guides, and quiz history are scoped to their account at the database level.
- API keys are entered per-session and never persisted to disk or the database.

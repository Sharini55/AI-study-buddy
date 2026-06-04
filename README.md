# SunDevil AI ☀️😈

SunDevil AI is a specialized educational ecosystem designed to bridge the gap between heavy, static STEM slide decks (like CSE 230/240) and active recall learning. Unlike general AI chat interfaces, SunDevil AI isolates subject contexts into Notion-style workspaces and uses an adaptive remediation loop to narrow down a student's weak areas.

---

## 🚀 Key Features

* **Workspaces:** Switch dynamically between subjects (e.g., Physics, CSE 240) without data bleeding or cross-contamination of AI context.
* **Multimodal Ingestion:** Powered by Gemini 3.5 Flash to automatically process text and break down complex visual structures like memory layouts and logic gate diagrams.
* **Sanctuary UI Theme:** Built with a warm, accessible pastel palette intentionally designed to reduce pre-exam cognitive fatigue and anxiety.

---

## 🛠️ Tech Stack & Architecture

* **LLM Engine:** Google Gemini 3.5 Flash API
* **SDK:** Latest unified `google-genai` library
* **State Management:** Core Python dictionaries mapped into Streamlit Session State for seamless dynamic multitenancy.

---

### Configure Authentication
To run the reasoning engine, this application requires a free Gemini API key from Google AI Studio. 

1. **Get a Key:** Head over to [Google AI Studio](https://aistudio.google.com/) and generate a free API key.
2. **Launch the App:** Run `streamlit run app.py` to open the interface in your browser.
3. **Insert Key:** Look at the left sidebar, click to open the **⚙️ Settings** section, paste your key into the text field, and press Enter.

Once the key is entered, you are all set to create workspaces, parse materials, and run quizzes!

---

## 💻 How to Run the App Locally

Follow these quick steps to get the app running on your machine:

### Clone the Repository
```bash
git clone (https://github.com/Sharini55/AI-study-buddy.git)



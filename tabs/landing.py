import streamlit as st
import streamlit.components.v1 as components


def render_landing_page(on_login_click=None):
    """
    Renders the AI Study Buddy marketing landing page.
    Uses st.components.v1.html() so the full HTML/CSS is parsed by a real
    browser engine inside an iframe — no Markdown pre-processing that would
    print <style> blocks as visible text.

    on_login_click: optional callback; if supplied, the CTA buttons call it
    via Streamlit's component messaging.  If None the buttons just scroll the
    parent page to whatever element has id="login-section".
    """

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:         #F5F8EE;
    --ink:        #242B18;
    --muted:      #5C6A48;
    --line:       #C5D99A;
    --green:      #ABC270;
    --green-dark: #8BA552;
    --yellow:     #D9A441;
    --panel:      #FFFFFF;
    --sans:       'Inter', system-ui, sans-serif;
  }

  html { scroll-behavior: smooth; }

  body {
    background: var(--bg);
    color: var(--ink);
    font-family: var(--sans);
    font-size: 16px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }

  /* ── NAV ── */
  nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 48px;
    border-bottom: 1px solid var(--line);
    background: var(--bg);
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .nav-logo {
    font-size: 1rem;
    font-weight: 700;
    color: var(--ink);
    display: flex;
    align-items: center;
    gap: 7px;
    text-decoration: none;
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 28px;
    list-style: none;
  }

  .nav-links a {
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--muted);
    text-decoration: none;
    transition: color 0.15s;
  }

  .nav-links a:hover { color: var(--ink); }

  .btn-login {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--ink);
    background: var(--yellow);
    border: none;
    border-radius: 100px;
    padding: 8px 20px;
    cursor: pointer;
    font-family: var(--sans);
    transition: background 0.15s;
  }

  .btn-login:hover { background: #C4922E; }

  /* ── SECTIONS ── */
  section {
    max-width: 1080px;
    margin: 0 auto;
    padding: 80px 48px;
  }

  /* ── HERO ── */
  .hero {
    text-align: center;
    padding-top: 96px;
    padding-bottom: 80px;
  }

  .hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--green-dark);
    background: rgba(171,194,112,0.15);
    border-radius: 100px;
    padding: 4px 12px;
    margin-bottom: 24px;
  }

  h1 {
    font-size: clamp(2.4rem, 6vw, 4rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -1.5px;
    color: var(--ink);
    margin-bottom: 20px;
  }

  .hero-sub {
    font-size: 1.05rem;
    color: var(--muted);
    max-width: 520px;
    margin: 0 auto 36px;
    line-height: 1.65;
  }

  .hero-ctas {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 14px;
  }

  .btn-primary {
    font-family: var(--sans);
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--ink);
    background: var(--yellow);
    border: none;
    border-radius: 100px;
    padding: 12px 28px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-primary:hover { background: #C4922E; }

  .btn-ghost {
    font-family: var(--sans);
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--muted);
    background: transparent;
    border: 1.5px solid var(--line);
    border-radius: 100px;
    padding: 11px 24px;
    cursor: pointer;
    text-decoration: none;
    transition: border-color 0.15s, color 0.15s;
  }

  .btn-ghost:hover { border-color: var(--ink); color: var(--ink); }

  .hero-note {
    font-size: 0.78rem;
    color: var(--muted);
  }

  /* ── MOCKUP WINDOW ── */
  .mockup-window {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 8px 40px rgba(36,43,24,0.08);
    margin-top: 56px;
    max-width: 780px;
    margin-left: auto;
    margin-right: auto;
  }

  .mockup-bar {
    background: #F0F4E8;
    border-bottom: 1px solid var(--line);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot-r { background: #FF6B6B; }
  .dot-y { background: #FFD93D; }
  .dot-g { background: #6BCB77; }

  .mockup-grid {
    display: grid;
    grid-template-columns: 180px 1fr;
    min-height: 280px;
  }

  .mockup-sidebar {
    background: #F7F9F2;
    border-right: 1px solid var(--line);
    padding: 16px 12px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .mockup-nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border-radius: 7px;
    font-size: 0.78rem;
    color: var(--muted);
    font-weight: 500;
  }

  .mockup-nav-item.active {
    background: var(--yellow);
    color: var(--ink);
    font-weight: 700;
  }

  .mockup-main {
    padding: 20px 24px;
  }

  .mockup-main h4 {
    font-family: var(--sans);
    font-weight: 800;
    font-size: 1.02rem;
    margin: 0 0 4px;
  }

  .mockup-main .sdai-sub {
    color: var(--muted);
    font-size: 0.83rem;
    margin-bottom: 20px;
  }

  .mockup-panel {
    background: #fff;
    border: 1.5px solid var(--line);
    border-radius: 14px;
    padding: 16px 18px;
  }

  .mockup-target {
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 10px;
  }

  .mockup-target span {
    color: var(--muted);
    font-weight: 500;
  }

  .sdai-mastery-card {
    background: #fff;
    border: 1.5px solid var(--line);
    border-radius: 14px;
    padding: 16px 18px;
  }

  .sdai-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--green-dark);
    background: rgba(171,194,112,0.15);
    border-radius: 100px;
    padding: 3px 9px;
    margin-bottom: 12px;
  }

  .sdai-m-row {
    margin-bottom: 10px;
  }

  .sdai-m-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    color: var(--ink);
    margin-bottom: 4px;
    font-weight: 500;
  }

  .sdai-score {
    color: var(--muted);
    font-size: 0.72rem;
  }

  .sdai-m-track {
    height: 6px;
    background: #E8EEE0;
    border-radius: 100px;
    overflow: hidden;
  }

  .sdai-m-fill {
    height: 100%;
    background: var(--green);
    border-radius: 100px;
    transition: width 1.2s ease;
  }

  .sdai-m-fill.done { background: var(--green-dark); }
  .sdai-m-fill.active { background: var(--yellow); }

  .sdai-agent-line {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-top: 12px;
    font-size: 0.78rem;
    color: var(--muted);
  }

  .sdai-agent-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--green);
    flex-shrink: 0;
    animation: pulse 1.8s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(0.8); }
  }

  .mockup-act-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--yellow);
    color: var(--ink);
    border: none;
    border-radius: 999px;
    padding: 8px 15px;
    font-size: 0.8rem;
    font-weight: 700;
    margin-top: 14px;
    cursor: default;
  }

  /* ── FEATURES ── */
  .features-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--green-dark);
    margin-bottom: 12px;
  }

  .features-heading {
    font-size: clamp(1.7rem, 4vw, 2.4rem);
    font-weight: 800;
    letter-spacing: -0.8px;
    color: var(--ink);
    margin-bottom: 12px;
  }

  .features-intro {
    font-size: 1rem;
    color: var(--muted);
    max-width: 520px;
    margin-bottom: 52px;
    line-height: 1.65;
  }

  .features-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 18px;
  }

  .f-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 22px 22px 24px;
  }

  .f-icon {
    font-size: 1.4rem;
    margin-bottom: 12px;
  }

  .f-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--ink);
    margin-bottom: 6px;
  }

  .f-desc {
    font-size: 0.86rem;
    color: var(--muted);
    line-height: 1.6;
  }

  /* ── HOW IT WORKS ── */
  .how-bg {
    background: #EFF4E6;
    border-radius: 20px;
    padding: clamp(40px, 6vw, 64px) clamp(28px, 5vw, 56px);
  }

  .how-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--green-dark);
    margin-bottom: 12px;
  }

  .how-heading {
    font-size: clamp(1.5rem, 3.5vw, 2rem);
    font-weight: 800;
    letter-spacing: -0.6px;
    color: var(--ink);
    margin-bottom: 6px;
  }

  .how-sub {
    font-size: 0.95rem;
    color: var(--muted);
    margin-bottom: 36px;
    max-width: 480px;
  }

  .steps {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .sdai-step {
    display: grid;
    grid-template-columns: 42px 1fr;
    gap: 14px;
    align-items: start;
  }

  .step-num {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: var(--panel);
    border: 2px solid var(--line);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--ink);
    flex-shrink: 0;
  }

  .step-text strong {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--ink);
    display: block;
    margin-bottom: 2px;
  }

  .step-text span {
    font-size: 0.85rem;
    color: var(--muted);
  }

  /* ── AGENT SECTION ── */
  .agent-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 48px;
    align-items: center;
  }

  .agent-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--green-dark);
    margin-bottom: 12px;
  }

  .agent-heading {
    font-size: clamp(1.5rem, 3.5vw, 2rem);
    font-weight: 800;
    letter-spacing: -0.6px;
    color: var(--ink);
    margin-bottom: 14px;
  }

  .agent-body {
    font-size: 0.95rem;
    color: var(--muted);
    line-height: 1.7;
    margin-bottom: 20px;
  }

  .agent-loop {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .loop-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.86rem;
    color: var(--ink);
    font-weight: 500;
  }

  .loop-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    flex-shrink: 0;
  }

  .agent-card {
    background: var(--panel);
    border: 1.5px solid var(--line);
    border-radius: 16px;
    padding: 24px;
  }

  .agent-card-tag {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--green-dark);
    margin-bottom: 16px;
  }

  /* ── FAQ ── */
  .faq-heading {
    font-size: clamp(1.5rem, 3.5vw, 2rem);
    font-weight: 800;
    letter-spacing: -0.6px;
    color: var(--ink);
    margin-bottom: 32px;
  }

  .sdai-faq-item {
    border-top: 1px solid var(--line);
  }

  .sdai-faq-list {
    border-bottom: 1px solid var(--line);
  }

  .sdai-faq-q {
    width: 100%;
    background: none;
    border: none;
    text-align: left;
    cursor: pointer;
    padding: 20px 4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: var(--sans);
    font-size: 0.97rem;
    font-weight: 600;
    color: var(--ink);
  }

  .sdai-faq-q i {
    color: var(--green-dark);
    transition: transform 0.2s;
    flex-shrink: 0;
    margin-left: 16px;
    font-size: 1.1rem;
  }

  .sdai-faq-item[open] .sdai-faq-q i {
    transform: rotate(180deg);
  }

  .sdai-faq-a {
    padding: 0 4px 22px;
    color: var(--muted);
    font-size: 0.96rem;
    max-width: 68ch;
  }

  /* ── CTA BAND ── */
  .sdai-cta-band {
    background: var(--green);
    border-radius: 20px;
    padding: clamp(34px, 5vw, 60px);
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 36px;
    align-items: center;
  }

  .sdai-cta-band h2 {
    font-size: clamp(1.7rem, 3.4vw, 2.3rem);
    color: var(--ink) !important;
  }

  .sdai-cta-band p {
    color: #2E3A1E !important;
    font-size: 1.02rem;
    margin-top: 12px;
    max-width: 44ch;
  }

  .sdai-cta-band .sdai-btn-primary {
    background: var(--ink);
    color: #fff !important;
  }

  .sdai-cta-band .sdai-btn-primary:hover {
    background: #10150A;
  }

  /* ── FOOTER ── */
  .sdai-footer {
    padding: 44px 0 8px;
    border-top: 1px solid var(--line);
  }

  .sdai-footer-inner {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 20px;
    align-items: center;
    max-width: 1080px;
    margin: 0 auto;
    padding: 0 48px;
  }

  .sdai-footer-note {
    color: var(--muted) !important;
    font-size: 0.86rem;
    max-width: 46ch;
  }

  .sdai-footer-links {
    display: flex;
    gap: 20px;
    font-size: 0.86rem;
    color: var(--muted) !important;
  }

  .sdai-footer-links a {
    color: var(--muted);
    text-decoration: none;
  }

  .sdai-footer-links a:hover { color: var(--ink); }

  /* ── SCROLL REVEAL ── */
  .sdai-reveal {
    opacity: 0;
    transform: translateY(18px);
    transition: opacity 0.6s ease, transform 0.6s ease;
  }

  .sdai-reveal.sdai-reveal-in {
    opacity: 1;
    transform: translateY(0);
  }

  /* ── RESPONSIVE ── */
  @media (max-width: 900px) {
    .sdai-hero-grid { grid-template-columns: 1fr; }
    .features-grid { grid-template-columns: 1fr; }
    .mockup-grid { grid-template-columns: 1fr; }
    .mockup-window { grid-template-columns: 1fr; }
    .sdai-cta-band { grid-template-columns: 1fr; }
    .agent-grid { grid-template-columns: 1fr; }
  }

  @media (max-width: 560px) {
    .sdai-wrap { padding: 0 20px; }
    .sdai-nav-inner { padding: 14px 20px; }
    .sdai-hero { padding: 44px 0 36px; }
    section { padding: 48px 0; }
    .sdai-step { grid-template-columns: 42px 1fr; gap: 14px; }
  }
</style>
</head>
<body>

<!-- ── NAV ── -->
<nav>
  <a href="#" class="nav-logo">📚 AI Study Buddy</a>
  <ul class="nav-links">
    <li><a href="#features">Features</a></li>
    <li><a href="#how-it-works">How it works</a></li>
    <li><a href="#faq">FAQ</a></li>
  </ul>
  <button class="btn-login" onclick="notifyLogin()">Log in →</button>
</nav>

<!-- ── HERO ── -->
<section class="hero">
  <div class="hero-tag">Active-recall study workspaces</div>
  <h1>Study what you actually<br/>don't know yet.</h1>
  <p class="hero-sub">
    Upload your slides, PDFs, or notes. Get study guides grounded only in
    your material, quiz yourself, and let an agent quietly find your weak
    spots and keep at them until they're not weak anymore.
  </p>
  <div class="hero-ctas">
    <button class="btn-primary" onclick="notifyLogin()">Start studying free →</button>
    <a href="#how-it-works" class="btn-ghost">See how it works</a>
  </div>
  <p class="hero-note">No credit card. Works with PDF, PPTX, and pasted text.</p>

  <!-- live mockup preview -->
  <div class="mockup-window sdai-reveal">
    <div class="mockup-bar">
      <div class="dot dot-r"></div>
      <div class="dot dot-y"></div>
      <div class="dot dot-g"></div>
    </div>
    <div class="mockup-grid">
      <div class="mockup-sidebar">
        <div class="mockup-nav-item">⊞ Dashboard</div>
        <div class="mockup-nav-item">📖 Study guide</div>
        <div class="mockup-nav-item">◎ Quiz</div>
        <div class="mockup-nav-item active">◎ Adaptive Study</div>
        <div class="mockup-nav-item">🔖 Saved Guides</div>
      </div>
      <div class="mockup-main">
        <div class="sdai-mastery-card">
          <div class="sdai-tag">⚡ Agent-picked focus</div>
          <div class="sdai-m-row">
            <div class="sdai-m-label">
              <span>Cellular Respiration</span>
              <span class="sdai-score" data-target="88">0/80</span>
            </div>
            <div class="sdai-m-track"><div class="sdai-m-fill done" data-width="100"></div></div>
          </div>
          <div class="sdai-m-row">
            <div class="sdai-m-label">
              <span>Elasticity of Demand</span>
              <span class="sdai-score" data-target="61">0/80</span>
            </div>
            <div class="sdai-m-track"><div class="sdai-m-fill" data-width="76"></div></div>
          </div>
          <div class="sdai-m-row">
            <div class="sdai-m-label">
              <span>Class Visibility Modifiers</span>
              <span class="sdai-score" data-target="24">0/80</span>
            </div>
            <div class="sdai-m-track"><div class="sdai-m-fill active" data-width="30"></div></div>
          </div>
          <div class="sdai-agent-line">
            <span class="sdai-agent-dot" aria-hidden="true"></span>
            Next up: 8 questions on Visibility Modifiers — chosen automatically.
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ── FEATURES ── -->
<section id="features">
  <div class="features-label">Built from what you upload</div>
  <h2 class="features-heading">Nothing here is generic.</h2>
  <p class="features-intro">
    Every guide, explanation, and quiz question is pulled from the material
    you actually gave it — not a general knowledge dump.
  </p>
  <div class="features-grid">
    <div class="f-card sdai-reveal">
      <div class="f-icon">📄</div>
      <div class="f-title">Grounded in your material</div>
      <p class="f-desc">Drop in a PDF, a slide deck, or pasted notes. Guides and quizzes are built strictly from that content — if it's not in your material, it's not in the answer.</p>
    </div>
    <div class="f-card sdai-reveal">
      <div class="f-icon">💡</div>
      <div class="f-title">Guides that make you work</div>
      <p class="f-desc">Every topic gets a concept, a worked example, and a challenge problem with the answer hidden until you're ready to check yourself.</p>
    </div>
    <div class="f-card sdai-reveal">
      <div class="f-icon">◎</div>
      <div class="f-title">An agent that finds the gaps</div>
      <p class="f-desc">After a quiz, the agent scores every topic, picks the weakest one on its own, and keeps quizzing you on it — with more questions while there's more ground to cover, fewer as you close in.</p>
    </div>
  </div>
</section>

<!-- ── HOW IT WORKS ── -->
<section id="how-it-works">
  <div class="how-bg sdai-reveal">
    <div class="how-label">The loop</div>
    <h2 class="how-heading">From upload to mastered — in order.</h2>
    <p class="how-sub">This is the actual sequence, not a marketing metaphor: each step feeds the next one.</p>
    <div class="steps">
      <div class="sdai-step">
        <div class="step-num">01</div>
        <div class="step-text">
          <strong>Upload your material</strong>
          <span>PDF, PPTX, images, or pasted text — indexed into a workspace for that subject.</span>
        </div>
      </div>
      <div class="sdai-step">
        <div class="step-num">02</div>
        <div class="step-text">
          <strong>Get a study guide, or take a quiz</strong>
          <span>Read a grounded guide with gated challenge questions, or jump straight into a multiple-choice quiz.</span>
        </div>
      </div>
      <div class="sdai-step">
        <div class="step-num">03</div>
        <div class="step-text">
          <strong>The agent scores every topic</strong>
          <span>Each quiz attempt updates a mastery score per topic — recent performance counts more than an old mistake.</span>
        </div>
      </div>
      <div class="sdai-step">
        <div class="step-num">04</div>
        <div class="step-text">
          <strong>It picks your next round automatically</strong>
          <span>No deciding what to study. The agent surfaces your weakest topic and queues the right number of questions for it.</span>
        </div>
      </div>
      <div class="sdai-step">
        <div class="step-num">05</div>
        <div class="step-text">
          <strong>One place, every subject</strong>
          <span>Each workspace holds its own material, guides, and quiz history — switch subjects without losing progress on the last one.</span>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ── AGENT DEEP DIVE ── -->
<section>
  <div class="agent-grid">
    <div class="sdai-reveal">
      <div class="agent-label">How the agent works</div>
      <h2 class="agent-heading">An agent that finds the gaps.</h2>
      <p class="agent-body">
        After every quiz, the agent reads your performance, picks the topic
        where you're furthest from mastery, and queues a focused round —
        automatically. You don't choose what to study next. It does.
      </p>
      <div class="agent-loop">
        <div class="loop-item"><div class="loop-dot"></div> Perceive — reads quiz history and scores every topic</div>
        <div class="loop-item"><div class="loop-dot"></div> Decide — picks the weakest topic without input from you</div>
        <div class="loop-item"><div class="loop-dot"></div> Act — generates a targeted quiz round for that topic</div>
        <div class="loop-item"><div class="loop-dot"></div> Adapt — updates the score, adjusts question count, loops</div>
      </div>
    </div>
    <div class="agent-card sdai-reveal">
      <div class="agent-card-tag">⚡ Agent-picked focus · Biology 201</div>
      <div class="sdai-m-row" style="margin-bottom:12px;">
        <div class="sdai-m-label"><span>Cellular Respiration</span><span class="sdai-score">88/80 ✓</span></div>
        <div class="sdai-m-track"><div class="sdai-m-fill done" style="width:100%"></div></div>
      </div>
      <div class="sdai-m-row" style="margin-bottom:12px;">
        <div class="sdai-m-label"><span>Elasticity of Demand</span><span class="sdai-score">61/80</span></div>
        <div class="sdai-m-track"><div class="sdai-m-fill" style="width:76%"></div></div>
      </div>
      <div class="sdai-m-row" style="margin-bottom:12px;">
        <div class="sdai-m-label"><span>Class Visibility Modifiers</span><span class="sdai-score">24/80</span></div>
        <div class="sdai-m-track"><div class="sdai-m-fill active" style="width:30%"></div></div>
      </div>
      <div class="sdai-agent-line">
        <span class="sdai-agent-dot"></span>
        Next up: 8 questions on Visibility Modifiers — chosen automatically.
      </div>
      <button class="mockup-act-btn">▶ Start round (8 questions)</button>
      <p style="font-size:0.72rem;color:var(--muted);margin-top:8px;">Good questions</p>
    </div>
  </div>
</section>

<!-- ── FAQ ── -->
<section id="faq">
  <h2 class="faq-heading">A few things you might be wondering.</h2>
  <div class="sdai-faq-list">
    <details class="sdai-faq-item">
      <summary class="sdai-faq-q">Can it work with my actual course material? <i>▾</i></summary>
      <p class="sdai-faq-a">Yes — upload a syllabus, slides, PDFs, or paste notes directly. Guides, explanations, and quiz questions are built strictly from what you give it, not general knowledge about the subject.</p>
    </details>
    <details class="sdai-faq-item">
      <summary class="sdai-faq-q">Will it just give me answers? <i>▾</i></summary>
      <p class="sdai-faq-a">No. Challenge problems in the study guide are hidden until you attempt them. The quiz doesn't show explanations until after you submit. The point is to make you retrieve the answer, not read it.</p>
    </details>
    <details class="sdai-faq-item">
      <summary class="sdai-faq-q">What file types are supported? <i>▾</i></summary>
      <p class="sdai-faq-a">PDF, PPTX, JPG, and PNG up to 200 MB per file. You can also paste text directly — useful for copying from a textbook or your own notes.</p>
    </details>
    <details class="sdai-faq-item">
      <summary class="sdai-faq-q">Is my data private? <i>▾</i></summary>
      <p class="sdai-faq-a">Your material and quiz history are stored in a tenant-isolated database — no other user can access your workspaces. Your Gemini API key is stored only in your browser and is never sent to our servers.</p>
    </details>
    <details class="sdai-faq-item">
      <summary class="sdai-faq-q">Can I use it on my phone? <i>▾</i></summary>
      <p class="sdai-faq-a">Yes — the app is responsive and works in a mobile browser. File upload works best from a desktop, but reviewing guides and taking quizzes works fine on mobile.</p>
    </details>
  </div>
</section>

<!-- ── CTA BAND ── -->
<section>
  <div class="sdai-cta-band sdai-reveal">
    <div>
      <h2>Stop cramming. Start understanding.</h2>
      <p>Upload your first set of slides and see your first study guide in about two minutes.</p>
    </div>
    <div style="display:flex;justify-content:flex-end;">
      <button class="btn-primary sdai-btn-primary" onclick="notifyLogin()" style="background:var(--ink);color:#fff;font-size:1rem;padding:14px 32px;">
        Start studying free →
      </button>
    </div>
  </div>
</section>

<!-- ── FOOTER ── -->
<div class="sdai-footer">
  <div class="sdai-footer-inner">
    <p class="sdai-footer-note">AI Study Buddy — Active-Recall Study Workspaces.<br/>Built by a student, for students.</p>
    <div class="sdai-footer-links">
      <a href="#features">Features</a>
      <a href="#how-it-works">How it works</a>
      <a href="#faq">FAQ</a>
      <a href="#" onclick="notifyLogin();return false;">Log in</a>
    </div>
  </div>
</div>

<script>
  // ── Notify Streamlit to switch to the login view ──
  function notifyLogin() {
    // Streamlit components communicate via window.parent.postMessage
    window.parent.postMessage({ type: 'sdai_login' }, '*');
  }

  // ── Animate mastery bar fills on load ──
  window.addEventListener('load', function () {
    document.querySelectorAll('.sdai-m-fill[data-width]').forEach(function (el) {
      var w = el.getAttribute('data-width');
      setTimeout(function () { el.style.width = w + '%'; }, 200);
    });

    // Animate score counters
    document.querySelectorAll('.sdai-score[data-target]').forEach(function (el) {
      var target = parseInt(el.getAttribute('data-target'), 10);
      var start  = 0;
      var dur    = 1200;
      var step   = 16;
      var inc    = target / (dur / step);
      var iv = setInterval(function () {
        start = Math.min(start + inc, target);
        el.textContent = Math.round(start) + '/80';
        if (start >= target) clearInterval(iv);
      }, step);
    });

    // Scroll reveal
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('sdai-reveal-in');
          observer.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });

    document.querySelectorAll('.sdai-reveal').forEach(function (el) {
      observer.observe(el);
    });
  });

  // ── Auto-resize the iframe height so Streamlit shows it fully ──
  function resizeParent() {
    var h = document.body.scrollHeight;
    window.parent.postMessage({ type: 'sdai_height', height: h }, '*');
  }

  window.addEventListener('load', resizeParent);
  window.addEventListener('resize', resizeParent);
  new MutationObserver(resizeParent).observe(document.body, {
    childList: true, subtree: true, attributes: true
  });
</script>
</body>
</html>
"""

    # Render inside a real iframe — no Markdown pre-processing
    components.html(html, height=4200, scrolling=False)

    # ── Listen for messages from the iframe ──
    # Streamlit doesn't natively relay postMessage, so we use a tiny JS shim
    # injected into the PARENT page that listens for our custom events and
    # sets a query param to trigger a rerun.
    st.markdown("""
    <script>
    (function () {
      if (window._sdaiListenerAttached) return;
      window._sdaiListenerAttached = true;
      window.addEventListener('message', function (e) {
        if (e.data && e.data.type === 'sdai_login') {
          // Set a flag in sessionStorage so Streamlit can read it on next rerun
          sessionStorage.setItem('sdai_goto_login', '1');
          // Force a Streamlit rerun by clicking the hidden rerun button
          var btn = window.parent.document.querySelector(
            '[data-testid="stBaseButton-headerNoPadding"]'
          );
          if (btn) btn.click();
        }
        if (e.data && e.data.type === 'sdai_height') {
          var iframe = window.document.querySelector(
            'iframe[title="components.html"]'
          );
          if (iframe) iframe.style.height = e.data.height + 'px';
        }
      });
    })();
    </script>
    """, unsafe_allow_html=True)

    # Check if the iframe signalled a login click
    check_js = """
    <script>
    (function () {
      if (sessionStorage.getItem('sdai_goto_login') === '1') {
        sessionStorage.removeItem('sdai_goto_login');
        window.parent.postMessage({ type: 'sdai_login_confirmed' }, '*');
      }
    })();
    </script>
    """
    st.markdown(check_js, unsafe_allow_html=True)

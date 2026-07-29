"""
Marketing landing content, embedded directly above the login/signup form on
the unauthenticated screen (Option B: same page, no separate domain needed).

This is adapted from the standalone landing/index.html built for optional
separate hosting (e.g. GitHub Pages) later. Two differences from that file:

  1. Every CSS rule is scoped under #sdai-landing (including bare-tag resets
     like `h1`, `body`, `*`) so nothing here leaks onto the rest of the app,
     and critical properties carry !important so they reliably win against
     apply_theme()'s own blanket !important rules on h1-h6/p/span/etc, which
     would otherwise force Truculenta onto body copy that's meant to be Inter.
  2. CTA buttons link to #sdai-login (an anchor placed just above the login
     form in app.py) instead of an external URL, since this version already
     lives on the same page as that form.
"""

import streamlit as st

_LANDING_HTML = r"""
<div id="sdai-landing">
<style>
  #sdai-landing {
    --sdai-bg:          #F5F8EE;
    --sdai-sidebar:     #ECF1E2;
    --sdai-panel:       #FFFFFF;
    --sdai-ink:         #242B18;
    --sdai-muted:       #5C6A48;
    --sdai-line:        #C5D99A;
    --sdai-green:       #ABC270;
    --sdai-green-dark:  #8BA552;
    --sdai-yellow:      #D9A441;
    --sdai-orange:      #C18A2A;
    --sdai-glow:        rgba(171, 194, 112, 0.22);

    font-family: 'Inter', -apple-system, sans-serif !important;
    background: var(--sdai-bg) !important;
    color: var(--sdai-ink) !important;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    display: block;
    margin: -1rem -1rem 2.5rem -1rem;
    padding: 0 0 4px 0;
  }
  #sdai-landing * { box-sizing: border-box; }
  #sdai-landing img, #sdai-landing svg { display: block; max-width: 100%; }
  #sdai-landing a { color: inherit; text-decoration: none; }

  #sdai-landing h1, #sdai-landing h2, #sdai-landing h3, #sdai-landing .display {
    font-family: 'Truculenta', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    line-height: 1.04 !important;
    margin: 0 !important;
    color: var(--sdai-ink) !important;
  }
  #sdai-landing p { font-family: 'Inter', sans-serif !important; margin: 0; }

  @media (prefers-reduced-motion: reduce) {
    #sdai-landing *, #sdai-landing *::before, #sdai-landing *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }

  #sdai-landing :focus-visible {
    outline: 3px solid var(--sdai-orange) !important;
    outline-offset: 2px;
    border-radius: 4px;
  }

  #sdai-landing .sdai-wrap { max-width: 1180px; margin: 0 auto; padding: 0 32px; }

  /* Nav */
  #sdai-landing .sdai-nav {
    background: rgba(245, 248, 238, 0.9);
    border-bottom: 1px solid var(--sdai-line);
  }
  #sdai-landing .sdai-nav-inner {
    max-width: 1180px; margin: 0 auto; padding: 16px 32px;
    display: flex; align-items: center; justify-content: space-between;
  }
  #sdai-landing .sdai-brand { display: flex; align-items: center; gap: 10px; font-weight: 800 !important; font-size: 1.15rem; font-family: 'Truculenta', sans-serif !important; }
  #sdai-landing .sdai-brand-mark {
    width: 34px; height: 34px; border-radius: 9px; background: var(--sdai-ink);
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  }
  #sdai-landing .sdai-nav-links { display: flex; gap: 30px; font-size: 0.95rem; color: var(--sdai-muted); }
  #sdai-landing .sdai-nav-links a:hover { color: var(--sdai-ink); }
  #sdai-landing .sdai-nav-cta {
    background: var(--sdai-ink); color: #fff !important; padding: 10px 20px;
    border-radius: 999px; font-weight: 700 !important; font-size: 0.92rem;
    display: inline-flex; align-items: center; gap: 6px;
    transition: background 0.15s, transform 0.15s;
  }
  #sdai-landing .sdai-nav-cta:hover { background: var(--sdai-green-dark); transform: translateY(-1px); }

  /* Hero */
  #sdai-landing .sdai-hero { padding: 72px 0 56px; }
  #sdai-landing .sdai-hero-grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 56px; align-items: center; }
  #sdai-landing .sdai-eyebrow {
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--sdai-muted); margin-bottom: 18px; display: block;
  }
  #sdai-landing .sdai-hero h1 { font-size: clamp(2.3rem, 4.4vw, 3.6rem); }
  #sdai-landing .sdai-hero h1 .sdai-accent { color: var(--sdai-green-dark) !important; }
  #sdai-landing .sdai-hero p.sdai-lede { font-size: 1.15rem; color: var(--sdai-muted) !important; margin: 20px 0 30px; max-width: 46ch; }
  #sdai-landing .sdai-cta-row { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; }
  #sdai-landing .sdai-btn {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 15px 26px; border-radius: 999px; font-weight: 700 !important; font-size: 1rem;
    border: none; cursor: pointer; transition: transform 0.15s, background 0.15s, border-color 0.15s;
    font-family: 'Inter', sans-serif !important;
  }
  #sdai-landing .sdai-btn-primary { background: var(--sdai-yellow); color: var(--sdai-ink) !important; }
  #sdai-landing .sdai-btn-primary:hover { background: var(--sdai-orange); transform: translateY(-1px); }
  #sdai-landing .sdai-btn-ghost { background: transparent; color: var(--sdai-ink) !important; border: 1.5px solid var(--sdai-line); }
  #sdai-landing .sdai-btn-ghost:hover { border-color: var(--sdai-green); background: #fff; }
  #sdai-landing .sdai-hero-note { font-size: 0.85rem; color: var(--sdai-muted) !important; margin-top: 14px; }

  #sdai-landing .sdai-mastery-card {
    background: var(--sdai-panel); border: 1.5px solid var(--sdai-line); border-radius: 22px;
    padding: 26px; box-shadow: 0 24px 60px -30px rgba(36, 43, 24, 0.35);
  }
  #sdai-landing .sdai-tag {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--sdai-sidebar); color: var(--sdai-muted) !important; font-size: 0.78rem; font-weight: 700 !important;
    padding: 5px 12px; border-radius: 999px; margin-bottom: 18px;
  }
  #sdai-landing .sdai-tag i { color: var(--sdai-green-dark); font-size: 0.9rem; }
  #sdai-landing .sdai-m-row { margin-bottom: 16px; }
  #sdai-landing .sdai-m-row:last-child { margin-bottom: 0; }
  #sdai-landing .sdai-m-label { display: flex; justify-content: space-between; font-size: 0.87rem; font-weight: 600; margin-bottom: 7px; color: var(--sdai-ink) !important; }
  #sdai-landing .sdai-m-label .sdai-score { color: var(--sdai-muted) !important; font-weight: 500; }
  #sdai-landing .sdai-m-track { height: 10px; border-radius: 999px; background: var(--sdai-sidebar); overflow: hidden; }
  #sdai-landing .sdai-m-fill { height: 100%; border-radius: 999px; background: var(--sdai-green); width: 0%; transition: width 1.1s cubic-bezier(.2,.8,.2,1); }
  #sdai-landing .sdai-m-fill.done { background: var(--sdai-green-dark); }
  #sdai-landing .sdai-m-fill.active { background: var(--sdai-yellow); }
  #sdai-landing .sdai-agent-line {
    margin-top: 20px; padding-top: 16px; border-top: 1px dashed var(--sdai-line);
    display: flex; align-items: center; gap: 10px; font-size: 0.85rem; color: var(--sdai-muted) !important;
  }
  #sdai-landing .sdai-agent-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--sdai-green-dark); box-shadow: 0 0 0 4px var(--sdai-glow); }

  #sdai-landing section { padding: 72px 0; }
  #sdai-landing .sdai-section-head { max-width: 640px; margin-bottom: 44px; }
  #sdai-landing .sdai-section-head .sdai-eyebrow { margin-bottom: 14px; }
  #sdai-landing .sdai-section-head h2 { font-size: clamp(1.7rem, 3vw, 2.3rem); }
  #sdai-landing .sdai-section-head p { color: var(--sdai-muted) !important; font-size: 1.05rem; margin-top: 14px; }

  #sdai-landing .sdai-features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
  #sdai-landing .sdai-feature-card { background: var(--sdai-panel); border: 1.5px solid var(--sdai-line); border-radius: 18px; padding: 28px; transition: transform 0.18s, box-shadow 0.18s; }
  #sdai-landing .sdai-feature-card:hover { transform: translateY(-3px); box-shadow: 0 18px 40px -24px rgba(36,43,24,0.3); }
  #sdai-landing .sdai-feature-icon { width: 44px; height: 44px; border-radius: 12px; margin-bottom: 16px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; }
  #sdai-landing .sdai-feature-icon.i1 { background: #E4EDD1; color: var(--sdai-green-dark); }
  #sdai-landing .sdai-feature-icon.i2 { background: #FBEBD0; color: var(--sdai-orange); }
  #sdai-landing .sdai-feature-icon.i3 { background: #DDE6F5; color: #4C6FA6; }
  #sdai-landing .sdai-feature-card h3 { font-size: 1.12rem; margin-bottom: 8px !important; }
  #sdai-landing .sdai-feature-card p { color: var(--sdai-muted) !important; font-size: 0.95rem; }

  #sdai-landing .sdai-steps { display: flex; flex-direction: column; }
  #sdai-landing .sdai-step { display: grid; grid-template-columns: 80px 1fr; gap: 24px; padding: 28px 0; border-top: 1px solid var(--sdai-line); }
  #sdai-landing .sdai-steps .sdai-step:last-child { border-bottom: 1px solid var(--sdai-line); }
  #sdai-landing .sdai-step-num { font-family: 'Truculenta', sans-serif !important; font-weight: 800 !important; font-size: 1.5rem; color: var(--sdai-green-dark) !important; opacity: 0.55; }
  #sdai-landing .sdai-step h3 { font-size: 1.15rem; margin-bottom: 6px !important; }
  #sdai-landing .sdai-step p { color: var(--sdai-muted) !important; max-width: 60ch; }

  #sdai-landing .sdai-mockup-shell { background: var(--sdai-ink); border-radius: 24px; padding: clamp(18px, 4vw, 40px); color: #fff !important; }
  #sdai-landing .sdai-mockup-shell .sdai-section-head h2 { color: #fff !important; }
  #sdai-landing .sdai-mockup-shell .sdai-section-head p { color: rgba(255,255,255,0.72) !important; }
  #sdai-landing .sdai-mockup-window { background: var(--sdai-bg); border-radius: 16px; overflow: hidden; margin-top: 10px; display: grid; grid-template-columns: 210px 1fr; box-shadow: 0 30px 70px -30px rgba(0,0,0,0.5); }
  #sdai-landing .sdai-mockup-sidebar { background: var(--sdai-sidebar); padding: 20px 14px; }
  #sdai-landing .sdai-mockup-nav-item { display: flex; align-items: center; gap: 9px; padding: 9px 11px; border-radius: 9px; font-size: 0.86rem; font-weight: 600; color: var(--sdai-ink) !important; margin-bottom: 4px; }
  #sdai-landing .sdai-mockup-nav-item.active { background: var(--sdai-yellow); }
  #sdai-landing .sdai-mockup-nav-item i { font-size: 1rem; color: var(--sdai-muted); }
  #sdai-landing .sdai-mockup-nav-item.active i { color: var(--sdai-ink); }
  #sdai-landing .sdai-mockup-main { padding: 24px 26px; }
  #sdai-landing .sdai-mockup-main h4 { font-family: 'Truculenta', sans-serif !important; font-weight: 800 !important; font-size: 1.3rem; margin: 0 0 4px !important; }
  #sdai-landing .sdai-mockup-main .sdai-sub { color: var(--sdai-muted) !important; font-size: 0.83rem; margin-bottom: 20px; }
  #sdai-landing .sdai-mockup-panel { background: #fff; border: 1.5px solid var(--sdai-line); border-radius: 14px; padding: 16px 18px; }
  #sdai-landing .sdai-mockup-target { font-size: 0.9rem; font-weight: 600; margin-bottom: 10px; }
  #sdai-landing .sdai-mockup-target span { color: var(--sdai-muted) !important; font-weight: 500; }
  #sdai-landing .sdai-mockup-act-btn { display: inline-flex; align-items: center; gap: 6px; background: var(--sdai-yellow); color: var(--sdai-ink) !important; padding: 8px 15px; border-radius: 999px; font-size: 0.8rem; font-weight: 700 !important; }

  #sdai-landing .sdai-faq-item { border-top: 1px solid var(--sdai-line); }
  #sdai-landing .sdai-faq-list { border-bottom: 1px solid var(--sdai-line); }
  #sdai-landing .sdai-faq-q {
    width: 100%; background: none; border: none; text-align: left; cursor: pointer;
    padding: 20px 4px; display: flex; align-items: center; justify-content: space-between;
    font-family: 'Inter', sans-serif !important; font-size: 1.02rem; font-weight: 700 !important; color: var(--sdai-ink) !important;
  }
  #sdai-landing .sdai-faq-q i { color: var(--sdai-green-dark); transition: transform 0.2s; flex-shrink: 0; margin-left: 16px; }
  #sdai-landing .sdai-faq-item[open] .sdai-faq-q i { transform: rotate(180deg); }
  #sdai-landing .sdai-faq-a { padding: 0 4px 22px; color: var(--sdai-muted) !important; font-size: 0.96rem; max-width: 68ch; }

  #sdai-landing .sdai-cta-band { background: var(--sdai-green); border-radius: 26px; padding: clamp(34px, 5vw, 60px); display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 36px; align-items: center; }
  #sdai-landing .sdai-cta-band h2 { font-size: clamp(1.7rem, 3.4vw, 2.3rem); color: var(--sdai-ink) !important; }
  #sdai-landing .sdai-cta-band p { color: #2E3A1E !important; font-size: 1.02rem; margin-top: 12px; max-width: 44ch; }
  #sdai-landing .sdai-cta-band .sdai-btn-primary { background: var(--sdai-ink); color: #fff !important; }
  #sdai-landing .sdai-cta-band .sdai-btn-primary:hover { background: #10150A; }

  #sdai-landing .sdai-footer { padding: 44px 0 8px; border-top: 1px solid var(--sdai-line); }
  #sdai-landing .sdai-footer-inner { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 20px; align-items: center; }
  #sdai-landing .sdai-footer-note { color: var(--sdai-muted) !important; font-size: 0.86rem; max-width: 46ch; }
  #sdai-landing .sdai-footer-links { display: flex; gap: 20px; font-size: 0.86rem; color: var(--sdai-muted) !important; }
  #sdai-landing .sdai-footer-links a:hover { color: var(--sdai-ink) !important; }

  #sdai-landing .sdai-reveal { opacity: 0; transform: translateY(18px); transition: opacity 0.6s ease, transform 0.6s ease; }
  #sdai-landing .sdai-reveal.in { opacity: 1; transform: translateY(0); }

  @media (max-width: 900px) {
    #sdai-landing .sdai-hero-grid { grid-template-columns: 1fr; }
    #sdai-landing .sdai-features-grid { grid-template-columns: 1fr; }
    #sdai-landing .sdai-mockup-window { grid-template-columns: 1fr; }
    #sdai-landing .sdai-mockup-sidebar { display: flex; overflow-x: auto; gap: 6px; padding: 12px; }
    #sdai-landing .sdai-mockup-nav-item { white-space: nowrap; }
    #sdai-landing .sdai-cta-band { grid-template-columns: 1fr; }
    #sdai-landing .sdai-nav-links { display: none; }
  }
  @media (max-width: 560px) {
    #sdai-landing .sdai-wrap { padding: 0 20px; }
    #sdai-landing .sdai-nav-inner { padding: 14px 20px; }
    #sdai-landing .sdai-hero { padding: 44px 0 36px; }
    #sdai-landing section { padding: 48px 0; }
    #sdai-landing .sdai-step { grid-template-columns: 42px 1fr; gap: 14px; }
  }
</style>

<nav class="sdai-nav">
  <div class="sdai-nav-inner">
    <a href="#sdai-landing" class="sdai-brand">
      <span class="sdai-brand-mark" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M4 5.5C4 4.67 4.67 4 5.5 4H11V19H5.5C4.67 19 4 18.33 4 17.5V5.5Z" stroke="#D9A441" stroke-width="1.6" stroke-linejoin="round"/>
          <path d="M20 5.5C20 4.67 19.33 4 18.5 4H13V19H18.5C19.33 19 20 18.33 20 17.5V5.5Z" stroke="#D9A441" stroke-width="1.6" stroke-linejoin="round"/>
        </svg>
      </span>
      AI Study Buddy
    </a>
    <div class="sdai-nav-links">
      <a href="#sdai-features">Features</a>
      <a href="#sdai-how">How it works</a>
      <a href="#sdai-faq">FAQ</a>
    </div>
    <a class="sdai-nav-cta" href="#sdai-login">Log in <i class="ti ti-arrow-right"></i></a>
  </div>
</nav>

<header class="sdai-hero">
  <div class="sdai-wrap sdai-hero-grid">
    <div>
      <span class="sdai-eyebrow">Active-recall study workspaces</span>
      <h1>Study what you<br>actually don't<br>know <span class="sdai-accent">yet.</span></h1>
      <p class="sdai-lede">
        Upload your slides, PDFs, or notes. Get study guides grounded only in
        your material, quiz yourself, and let an agent quietly find your weak
        spots and keep at them until they're not weak anymore.
      </p>
      <div class="sdai-cta-row">
        <a class="sdai-btn sdai-btn-primary" href="#sdai-login">Start studying free <i class="ti ti-arrow-right"></i></a>
        <a class="sdai-btn sdai-btn-ghost" href="#sdai-how">See how it works</a>
      </div>
      <p class="sdai-hero-note">No credit card. Works with PDF, PPTX, and pasted text.</p>
    </div>

    <div class="sdai-mastery-card sdai-reveal" id="sdai-mastery-card">
      <span class="sdai-tag"><i class="ti ti-robot"></i> Agent-picked focus</span>
      <div class="sdai-m-row">
        <div class="sdai-m-label"><span>Cellular Respiration</span><span class="sdai-score" data-target="88">0/80</span></div>
        <div class="sdai-m-track"><div class="sdai-m-fill done" data-width="100"></div></div>
      </div>
      <div class="sdai-m-row">
        <div class="sdai-m-label"><span>Elasticity of Demand</span><span class="sdai-score" data-target="61">0/80</span></div>
        <div class="sdai-m-track"><div class="sdai-m-fill" data-width="76"></div></div>
      </div>
      <div class="sdai-m-row">
        <div class="sdai-m-label"><span>Class Visibility Modifiers</span><span class="sdai-score" data-target="24">0/80</span></div>
        <div class="sdai-m-track"><div class="sdai-m-fill active" data-width="30"></div></div>
      </div>
      <div class="sdai-agent-line">
        <span class="sdai-agent-dot" aria-hidden="true"></span>
        Next up: 8 questions on Visibility Modifiers — chosen automatically.
      </div>
    </div>
  </div>
</header>

<section id="sdai-features">
  <div class="sdai-wrap">
    <div class="sdai-section-head sdai-reveal">
      <span class="sdai-eyebrow">Built from what you upload</span>
      <h2>Nothing here is generic.</h2>
      <p>Every guide, explanation, and quiz question is pulled from the material you actually gave it — not a general knowledge dump.</p>
    </div>
    <div class="sdai-features-grid">
      <div class="sdai-feature-card sdai-reveal">
        <div class="sdai-feature-icon i1"><i class="ti ti-file-text"></i></div>
        <h3>Grounded in your material</h3>
        <p>Drop in a PDF, a slide deck, or pasted notes. Guides and quizzes are built strictly from that content — if it's not in your material, it's not in the answer.</p>
      </div>
      <div class="sdai-feature-card sdai-reveal">
        <div class="sdai-feature-icon i2"><i class="ti ti-bulb"></i></div>
        <h3>Guides that make you work</h3>
        <p>Every topic gets a concept, a worked example, and a challenge problem with the answer hidden until you're ready to check yourself.</p>
      </div>
      <div class="sdai-feature-card sdai-reveal">
        <div class="sdai-feature-icon i3"><i class="ti ti-target-arrow"></i></div>
        <h3>An agent that finds the gaps</h3>
        <p>After a quiz, the agent scores every topic, picks the weakest one on its own, and keeps quizzing you on it — with more questions while there's more ground to cover, fewer as you close in.</p>
      </div>
    </div>
  </div>
</section>

<section id="sdai-how">
  <div class="sdai-wrap">
    <div class="sdai-section-head sdai-reveal">
      <span class="sdai-eyebrow">The loop</span>
      <h2>From upload to mastered — in order.</h2>
      <p>This is the actual sequence, not a marketing metaphor: each step feeds the next one.</p>
    </div>
    <div class="sdai-steps">
      <div class="sdai-step sdai-reveal">
        <div class="sdai-step-num">01</div>
        <div><h3>Upload your material</h3><p>PDF, PPTX, images, or pasted text — indexed into a workspace for that subject.</p></div>
      </div>
      <div class="sdai-step sdai-reveal">
        <div class="sdai-step-num">02</div>
        <div><h3>Get a study guide, or take a quiz</h3><p>Read a grounded guide with gated challenge questions, or jump straight into a multiple-choice quiz.</p></div>
      </div>
      <div class="sdai-step sdai-reveal">
        <div class="sdai-step-num">03</div>
        <div><h3>The agent scores every topic</h3><p>Each quiz attempt updates a mastery score per topic — recent performance counts more than an old mistake.</p></div>
      </div>
      <div class="sdai-step sdai-reveal">
        <div class="sdai-step-num">04</div>
        <div><h3>It picks your next focus — you don't have to</h3><p>The weakest topic gets targeted automatically, with a round sized to how much ground is actually left to cover.</p></div>
      </div>
    </div>
  </div>
</section>

<section id="sdai-product">
  <div class="sdai-wrap">
    <div class="sdai-mockup-shell sdai-reveal">
      <div class="sdai-section-head" style="margin-bottom: 24px;">
        <span class="sdai-eyebrow" style="color: rgba(255,255,255,0.6) !important;">Inside the workspace</span>
        <h2>One place, every subject.</h2>
        <p>Each workspace holds its own material, guides, and quiz history — switch subjects without losing progress on the last one.</p>
      </div>
      <div class="sdai-mockup-window">
        <div class="sdai-mockup-sidebar">
          <div class="sdai-mockup-nav-item"><i class="ti ti-layout-dashboard"></i> Dashboard</div>
          <div class="sdai-mockup-nav-item"><i class="ti ti-book"></i> Study guide</div>
          <div class="sdai-mockup-nav-item"><i class="ti ti-help-circle"></i> Quiz</div>
          <div class="sdai-mockup-nav-item active"><i class="ti ti-target-arrow"></i> Adaptive Study</div>
          <div class="sdai-mockup-nav-item"><i class="ti ti-bookmark"></i> Saved Guides</div>
        </div>
        <div class="sdai-mockup-main">
          <h4>🎯 Adaptive Study</h4>
          <div class="sdai-sub">Biology 201 — Overall: 6/9 topics mastered</div>
          <div class="sdai-mockup-panel">
            <div class="sdai-mockup-target">Focus: Cellular Respiration <span>— currently 24/80</span></div>
            <a class="sdai-mockup-act-btn" href="#sdai-login"><i class="ti ti-player-play"></i> Start round (14 questions)</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section id="sdai-faq">
  <div class="sdai-wrap">
    <div class="sdai-section-head sdai-reveal">
      <span class="sdai-eyebrow">Good questions</span>
      <h2>A few things you might be wondering.</h2>
    </div>
    <div class="sdai-faq-list sdai-reveal">
      <details class="sdai-faq-item" open>
        <summary class="sdai-faq-q">Can it work with my actual course material?<i class="ti ti-chevron-down"></i></summary>
        <div class="sdai-faq-a">Yes — upload a syllabus, slides, PDFs, or paste notes directly. Guides, explanations, and quiz questions are built strictly from what you give it, not general knowledge about the subject.</div>
      </details>
      <details class="sdai-faq-item">
        <summary class="sdai-faq-q">Will it just give me answers?<i class="ti ti-chevron-down"></i></summary>
        <div class="sdai-faq-a">No — every topic includes a challenge problem first, with the worked answer hidden behind a "Reveal Answer" button, so you attempt it before checking yourself.</div>
      </details>
      <details class="sdai-faq-item">
        <summary class="sdai-faq-q">What file types are supported?<i class="ti ti-chevron-down"></i></summary>
        <div class="sdai-faq-a">PDF, PPTX, JPG, and PNG uploads, plus pasted text. Slide images are analyzed for diagrams and code, not just their text.</div>
      </details>
      <details class="sdai-faq-item">
        <summary class="sdai-faq-q">Is my data private?<i class="ti ti-chevron-down"></i></summary>
        <div class="sdai-faq-a">Your Gemini API key is stored only in your browser and never touches our servers. Your uploaded material and progress are tied to your account and not shared with other users.</div>
      </details>
      <details class="sdai-faq-item">
        <summary class="sdai-faq-q">Can I use it on my phone?<i class="ti ti-chevron-down"></i></summary>
        <div class="sdai-faq-a">Yes — it runs in the browser, so it works on any device with no install.</div>
      </details>
    </div>
  </div>
</section>

<section>
  <div class="sdai-wrap">
    <div class="sdai-cta-band sdai-reveal">
      <div>
        <h2>Stop cramming. Start understanding.</h2>
        <p>Upload your first set of slides and see your first study guide in about two minutes.</p>
      </div>
      <div>
        <a class="sdai-btn sdai-btn-primary" href="#sdai-login">Start studying free <i class="ti ti-arrow-right"></i></a>
      </div>
    </div>
  </div>
</section>

<footer class="sdai-footer">
  <div class="sdai-wrap sdai-footer-inner">
    <p class="sdai-footer-note">AI Study Buddy — built for a calmer, more grounded way to study. Still growing; feedback welcome.</p>
    <div class="sdai-footer-links">
      <a href="#sdai-features">Features</a>
      <a href="#sdai-how">How it works</a>
      <a href="#sdai-faq">FAQ</a>
      <a href="#sdai-login">Log in</a>
    </div>
  </div>
</footer>
</div>

<script>
(function() {
  var root = document.getElementById('sdai-landing');
  if (!root || root.dataset.sdaiInit) return;
  root.dataset.sdaiInit = "1";

  var revealEls = root.querySelectorAll('.sdai-reveal');
  var io = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) { if (e.isIntersecting) e.target.classList.add('in'); });
  }, { threshold: 0.15 });
  revealEls.forEach(function(el) { io.observe(el); });

  var masteryCard = document.getElementById('sdai-mastery-card');
  var masteryPlayed = false;
  if (masteryCard) {
    var masteryIo = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting && !masteryPlayed) {
          masteryPlayed = true;
          masteryCard.querySelectorAll('.sdai-m-fill').forEach(function(bar, i) {
            setTimeout(function() { bar.style.width = bar.dataset.width + '%'; }, 150 + i * 180);
          });
          masteryCard.querySelectorAll('.sdai-score').forEach(function(el, i) {
            var target = parseInt(el.dataset.target, 10);
            setTimeout(function() { el.textContent = target + '/80'; }, 150 + i * 180);
          });
        }
      });
    }, { threshold: 0.4 });
    masteryIo.observe(masteryCard);
  }

  root.querySelectorAll('.sdai-faq-item').forEach(function(item) {
    item.addEventListener('toggle', function() {
      if (item.open) {
        root.querySelectorAll('.sdai-faq-item').forEach(function(other) {
          if (other !== item) other.open = false;
        });
      }
    });
  });
})();
</script>
"""


def render_marketing_landing() -> None:
    """Renders the marketing content above the login form on the
    unauthenticated screen. CTA links point to #sdai-login, an anchor
    app.py places directly above the login/signup form, so clicking
    'Start Free' just scrolls down to it on the same page."""
    st.markdown(_LANDING_HTML, unsafe_allow_html=True)

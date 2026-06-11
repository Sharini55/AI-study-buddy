import datetime
import json
import logging
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Per-user path helpers
# ---------------------------------------------------------------------------

_METRICS_DIR = Path(".metrics")

def _user_dir(username: str) -> Path:
    """Returns (and creates) a per-user metrics directory."""
    d = _METRICS_DIR / username
    d.mkdir(parents=True, exist_ok=True)
    return d

def _report_path(username: str) -> Path:
    return _user_dir(username) / "metrics_report.md"

def _log_path(username: str) -> Path:
    return _user_dir(username) / "metrics.log"

# ---------------------------------------------------------------------------
# Backward-compat shim: METRICS_REPORT still works for the sidebar download,
# but now it resolves against the currently logged-in user from session state.
# ---------------------------------------------------------------------------

def _current_username() -> str:
    """Best-effort: read username from Streamlit session state if available."""
    try:
        import streamlit as st
        return st.session_state.get("username") or "anonymous"
    except Exception:
        return "anonymous"

class _CurrentUserMetricsPath:
    """Descriptor that resolves to the active user's report path on every access."""
    def __fspath__(self):
        return str(_report_path(_current_username()))
    def __str__(self):
        return str(_report_path(_current_username()))
    def exists(self):
        return _report_path(_current_username()).exists()
    def stat(self):
        return _report_path(_current_username()).stat()
    def read_bytes(self):
        return _report_path(_current_username()).read_bytes()

# Sidebar code imports METRICS_REPORT and calls .exists()/.stat()/.read_bytes() on it.
METRICS_REPORT = _CurrentUserMetricsPath()

# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

_PRICE_INPUT_PER_1K  = 0.000075
_PRICE_OUTPUT_PER_1K = 0.000300

# ---------------------------------------------------------------------------
# Per-user logger cache  {username -> Logger}
# ---------------------------------------------------------------------------

_loggers: dict[str, logging.Logger] = {}

def _get_logger(username: str) -> logging.Logger:
    if username not in _loggers:
        logger = logging.getLogger(f"sundevil_raw.{username}")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        if not logger.handlers:
            h = logging.FileHandler(str(_log_path(username)))
            h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            logger.addHandler(h)
        _loggers[username] = logger
    return _loggers[username]


# ---------------------------------------------------------------------------
# Token / cost helpers
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        (input_tokens  / 1000) * _PRICE_INPUT_PER_1K +
        (output_tokens / 1000) * _PRICE_OUTPUT_PER_1K,
        6,
    )


# ---------------------------------------------------------------------------
# Core logging helpers  (username defaults to current session user)
# ---------------------------------------------------------------------------

def log_metric(event: str, data: dict, username: str | None = None) -> None:
    u = username or _current_username()
    _get_logger(u).debug(json.dumps({"event": event, "ts": datetime.datetime.now().isoformat(), **data}))


def _append_report(section: str, username: str) -> None:
    with open(str(_report_path(username)), "a", encoding="utf-8") as f:
        f.write(section + "\n")


def _report_header_once(username: str) -> None:
    p = _report_path(username)
    if not p.exists() or p.stat().st_size == 0:
        _append_report(
            "# SunDevil AI -- Model Metrics Report\n"
            f"_User: {username}_\n"
            "_Auto-generated. Every upload and AI generation appends a new entry._\n"
            "\n---\n",
            username,
        )


# ---------------------------------------------------------------------------
# Public reporting functions  (username optional; falls back to session state)
# ---------------------------------------------------------------------------

def report_parse_metrics(file_name: str, file_type: str, file_size_kb: float,
                          pages_or_slides: int, raw_chars: int, cleaned_chars: int,
                          images_found: int, parse_time_s: float,
                          username: str | None = None) -> None:
    u = username or _current_username()
    _report_header_once(u)
    completeness = round(cleaned_chars / raw_chars * 100, 1) if raw_chars else 0
    density      = round(cleaned_chars / max(pages_or_slides, 1))
    now          = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    section = f"""
## 📄 Document Parse — `{file_name}`
| Metric | Value |
|---|---|
| Timestamp | {now} |
| File type | `{file_type.upper()}` |
| File size | {file_size_kb:.1f} KB |
| Pages / slides | {pages_or_slides} |
| Raw characters extracted | {raw_chars:,} |
| Cleaned characters sent to model | {cleaned_chars:,} |
| **Parse completeness** | **{completeness}%** |
| Avg content density | {density:,} chars / page |
| Images found | {images_found} |
| Estimated tokens in source | ~{_count_tokens(" " * cleaned_chars):,} |
| Parse time | {parse_time_s:.2f}s |

> **What this means:** {completeness}% of extracted text survived cleaning and was passed to the model.
> {"⚠️ Low completeness — the file may be image-only or heavily formatted." if completeness < 60 else "✅ Good extraction quality."}

"""
    _append_report(section, u)
    log_metric("doc_parse", {
        "file": file_name, "type": file_type, "size_kb": file_size_kb,
        "pages": pages_or_slides, "raw_chars": raw_chars, "cleaned_chars": cleaned_chars,
        "completeness_pct": completeness, "images": images_found, "parse_time_s": parse_time_s,
    }, username=u)


def report_generation_metrics(label: str, subject: str, mode: str,
                               prompt_text: str, output_text: str,
                               elapsed_s: float, halluc: dict | None = None,
                               username: str | None = None) -> None:
    u = username or _current_username()
    _report_header_once(u)
    input_tokens  = _count_tokens(prompt_text)
    output_tokens = _count_tokens(output_text)
    cost          = _estimate_cost(input_tokens, output_tokens)
    ratio         = round(output_tokens / max(input_tokens, 1), 3)
    now           = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    halluc_row = ""
    if halluc and halluc.get("hallucination_count", -1) >= 0:
        hcount = halluc["hallucination_count"]
        hflag  = "🟢 None detected" if hcount == 0 else f"🔴 {hcount} flagged claim(s)"
        halluc_row = f"| Hallucination check | {hflag} |\n"

    section = f"""
## 🤖 AI Generation — {label} ({subject})
| Metric | Value |
|---|---|
| Timestamp | {now} |
| Subject | {subject} |
| Mode | {mode} |
| **Latency (time-to-value)** | **{elapsed_s:.2f}s** |
| Input tokens (est.) | ~{input_tokens:,} |
| Output tokens (est.) | ~{output_tokens:,} |
| **Estimated cost** | **${cost:.5f}** |
| Output / input token ratio | {ratio} |
{halluc_row}
> **Latency note:** {"🐢 Study guides are long-form — latency >30s is normal." if "Guide" in label else "⚡ Quiz generation is shorter — latency >15s may indicate prompt is too large."}
> **Cost note:** At this rate, 1,000 generations ≈ ${cost * 1000:.2f}.

"""
    _append_report(section, u)
    log_metric("generation", {
        "label": label, "subject": subject, "mode": mode,
        "elapsed_s": elapsed_s, "input_tokens": input_tokens,
        "output_tokens": output_tokens, "cost_usd": cost,
    }, username=u)

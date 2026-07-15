"""
utils/metrics.py
----------------
Persistent metrics logging for SunDevil AI.

All events are written to the `metric_events` Postgres table so they
survive Azure App Service restarts. The old file-based system wrote to
.metrics/ on disk which is ephemeral on Azure — data was lost on every
restart.

Each event is one row: (username, event_name, subject, properties JSON,
created_at). The admin dashboard queries this table directly.
"""

import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing constants (Gemini 2.5 Flash)
# ---------------------------------------------------------------------------
_PRICE_INPUT_PER_1K  = 0.000075
_PRICE_OUTPUT_PER_1K = 0.000300

# ---------------------------------------------------------------------------
# Backward-compat shims so existing imports don't break
# These are no-ops on Azure (no disk) but won't crash.
# ---------------------------------------------------------------------------
_METRICS_DIR = Path(".metrics")

def _current_username() -> str:
    try:
        import streamlit as st
        return st.session_state.get("username") or "anonymous"
    except Exception:
        return "anonymous"

def _report_path(username: str) -> Path:
    return _METRICS_DIR / username / "metrics_report.md"

def _user_dir(username: str) -> Path:
    return _METRICS_DIR / username

class _CurrentUserMetricsPath:
    def __fspath__(self): return str(_report_path(_current_username()))
    def __str__(self):    return str(_report_path(_current_username()))
    def exists(self):     return False   # always False on Azure
    def stat(self):       raise FileNotFoundError
    def read_bytes(self): raise FileNotFoundError

METRICS_REPORT = _CurrentUserMetricsPath()

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
# Core DB writer — fire-and-forget, never crashes the app
# ---------------------------------------------------------------------------

def _write_event(username: str, event: str, subject: str, props: dict) -> None:
    """Insert one metric event row into Postgres. Silently swallows errors."""
    try:
        from utils.persistence import SessionLocal, MetricEvent
        db = SessionLocal()
        try:
            db.add(MetricEvent(
                username   = username,
                event_name = event,
                subject    = subject or "",
                properties = json.dumps(props),
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.debug("metrics write failed (non-fatal)", exc_info=True)


# ---------------------------------------------------------------------------
# Public API — called throughout the app
# ---------------------------------------------------------------------------

def log_metric(event: str, data: dict, username: str | None = None) -> None:
    """Generic event logger. Called from quiz.py, study.py, ingest.py etc."""
    u = username or _current_username()
    subject = data.pop("subject", "")
    _write_event(u, event, subject, data)


def report_parse_metrics(file_name: str, file_type: str, file_size_kb: float,
                          pages_or_slides: int, raw_chars: int, cleaned_chars: int,
                          images_found: int, parse_time_s: float,
                          username: str | None = None) -> None:
    u = username or _current_username()
    completeness = round(cleaned_chars / raw_chars * 100, 1) if raw_chars else 0
    density      = round(cleaned_chars / max(pages_or_slides, 1))
    _write_event(u, "doc_parse", "", {
        "file_name":       file_name,
        "file_type":       file_type,
        "file_size_kb":    round(file_size_kb, 1),
        "pages":           pages_or_slides,
        "raw_chars":       raw_chars,
        "cleaned_chars":   cleaned_chars,
        "completeness_pct": completeness,
        "density_per_page": density,
        "images_found":    images_found,
        "parse_time_s":    parse_time_s,
    })


def report_generation_metrics(label: str, subject: str, mode: str,
                               prompt_text: str, output_text: str,
                               elapsed_s: float, halluc: dict | None = None,
                               username: str | None = None) -> None:
    u = username or _current_username()
    input_tokens  = _count_tokens(prompt_text)
    output_tokens = _count_tokens(output_text)
    cost          = _estimate_cost(input_tokens, output_tokens)
    props = {
        "label":         label,
        "mode":          mode,
        "elapsed_s":     round(elapsed_s, 2),
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "cost_usd":      cost,
        "output_ratio":  round(output_tokens / max(input_tokens, 1), 3),
    }
    if halluc and halluc.get("hallucination_count", -1) >= 0:
        props["hallucination_count"] = halluc["hallucination_count"]
    _write_event(u, "generation", subject, props)

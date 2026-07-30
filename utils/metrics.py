# ── Paste this block at the BOTTOM of utils/metrics.py ──────────────────────

DAILY_GUIDE_LIMIT = 3
DAILY_QUIZ_LIMIT  = 2


def get_daily_usage(username: str) -> dict:
    """
    Query metric_events to count how many guide and quiz generations
    this user has fired today (UTC day boundary).

    Returns:
        {
            "guides_used":     int,   # generations today
            "quizzes_used":    int,
            "guides_remaining": int,
            "quizzes_remaining": int,
            "guide_limit":     int,
            "quiz_limit":      int,
        }
    Falls back to zeroes if the DB is unreachable so the app never crashes.
    """
    try:
        from utils.persistence import SessionLocal, MetricEvent
        import datetime, sqlalchemy as sa

        today_start = datetime.datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        db = SessionLocal()
        try:
            guides_used = db.query(MetricEvent).filter(
                MetricEvent.username   == username,
                MetricEvent.event_name.in_(["generation", "study_guide_sot"]),
                MetricEvent.created_at >= today_start,
            ).count()

            quizzes_used = db.query(MetricEvent).filter(
                MetricEvent.username   == username,
                MetricEvent.event_name.in_(["quiz_generation", "targeted_quiz_ttv", "agent_quiz"]),
                MetricEvent.created_at >= today_start,
            ).count()
        finally:
            db.close()

        return {
            "guides_used":      guides_used,
            "quizzes_used":     quizzes_used,
            "guides_remaining": max(0, DAILY_GUIDE_LIMIT  - guides_used),
            "quizzes_remaining": max(0, DAILY_QUIZ_LIMIT  - quizzes_used),
            "guide_limit":      DAILY_GUIDE_LIMIT,
            "quiz_limit":       DAILY_QUIZ_LIMIT,
        }
    except Exception:
        logger.debug("get_daily_usage failed (non-fatal)", exc_info=True)
        return {
            "guides_used": 0, "quizzes_used": 0,
            "guides_remaining": DAILY_GUIDE_LIMIT,
            "quizzes_remaining": DAILY_QUIZ_LIMIT,
            "guide_limit": DAILY_GUIDE_LIMIT,
            "quiz_limit": DAILY_QUIZ_LIMIT,
        }
        # ---------------------------------------------------------------------------
# Backward-compat aliases — quiz.py and study.py import these by name
# ---------------------------------------------------------------------------

def log_metric(event: str, data: dict, username: str | None = None) -> None:
    """Generic event logger. Aliases to _write_event for backward compat."""
    u = username or _current_username()
    subject = data.pop("subject", "")
    _write_event(u, event, subject, data)


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


def report_parse_metrics(file_name: str, file_type: str, file_size_kb: float,
                          pages_or_slides: int, raw_chars: int, cleaned_chars: int,
                          images_found: int, parse_time_s: float,
                          username: str | None = None) -> None:
    u = username or _current_username()
    completeness = round(cleaned_chars / raw_chars * 100, 1) if raw_chars else 0
    density      = round(cleaned_chars / max(pages_or_slides, 1))
    _write_event(u, "doc_parse", "", {
        "file_name":        file_name,
        "file_type":        file_type,
        "file_size_kb":     round(file_size_kb, 1),
        "pages":            pages_or_slides,
        "raw_chars":        raw_chars,
        "cleaned_chars":    cleaned_chars,
        "completeness_pct": completeness,
        "density_per_page": density,
        "images_found":     images_found,
        "parse_time_s":     parse_time_s,
    })

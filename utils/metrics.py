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

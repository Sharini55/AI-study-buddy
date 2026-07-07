"""
utils/analytics.py
------------------
Thin PostHog wrapper for SunDevil AI.

Design rules:
  - Import once via get_posthog(); client is cached in module state.
  - Every capture() call is fire-and-forget inside a try/except so a
    PostHog outage or misconfiguration can never crash the app.
  - If POSTHOG_API_KEY is not set (local dev without a key), all calls
    are silently no-ops — no noise, no errors.
  - distinct_id is always the username so funnels are per-student,
    not per-anonymous-session.

Usage
-----
    from utils.analytics import capture

    capture("study_guide_generated", username, {
        "subject": subject,
        "mode": study_mode,
        "output_tokens": 14000,
    })
"""

import logging
import os

logger = logging.getLogger(__name__)

_client = None          # module-level singleton
_disabled = False       # set True once we know the key is missing


def _get_client():
    """Initialise the PostHog client on first use and cache it."""
    global _client, _disabled

    if _disabled:
        return None

    if _client is not None:
        return _client

    api_key = os.environ.get("POSTHOG_API_KEY", "").strip()
    host    = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com").strip()

    if not api_key:
        logger.info("POSTHOG_API_KEY not set — analytics disabled.")
        _disabled = True
        return None

    try:
        import posthog as ph
        ph.api_key = api_key
        ph.host    = host
        # Disable PostHog's own noisy logging unless DEBUG is set
        if not os.environ.get("DEBUG"):
            logging.getLogger("posthog").setLevel(logging.WARNING)
        _client = ph
        logger.info("PostHog analytics initialised (host=%s)", host)
    except ImportError:
        logger.warning("posthog package not installed — analytics disabled.")
        _disabled = True

    return _client


def capture(event: str, username: str, properties: dict | None = None) -> None:
    """
    Fire a PostHog event.

    Parameters
    ----------
    event      : snake_case event name, e.g. "study_guide_generated"
    username   : the logged-in student — used as the PostHog distinct_id
    properties : optional dict of metadata to attach to the event
    """
    client = _get_client()
    if client is None:
        return

    try:
        client.capture(
            distinct_id=username,
            event=event,
            properties=properties or {},
        )
    except Exception:
        # Analytics must never surface errors to students
        logger.exception("PostHog capture failed for event '%s'", event)


def identify(username: str, traits: dict | None = None) -> None:
    """
    Set persistent properties on a PostHog Person record.
    Call once after login to attach traits like account creation date.

    Parameters
    ----------
    username : student username (PostHog distinct_id)
    traits   : dict of person-level properties
    """
    client = _get_client()
    if client is None:
        return

    try:
        client.identify(
            distinct_id=username,
            properties=traits or {},
        )
    except Exception:
        logger.exception("PostHog identify failed for user '%s'", username)

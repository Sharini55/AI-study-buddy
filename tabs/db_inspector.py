"""
tabs/db_inspector.py
--------------------
Admin Dashboard — four tabs:
  1. Database Inspector  — raw table audit
  2. Product Metrics     — the 6 PM metrics pulled from metric_events
  3. Per-User Activity   — per-student breakdown
  4. Users              — account list
"""

import json
import logging
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import text

from utils.persistence import (
    SessionLocal, User, Workspace, SourceFile,
    SourceImage, StudyGuide, QuizAttempt, MetricEvent,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper — load metric_events as a DataFrame
# ---------------------------------------------------------------------------

def _load_events(db) -> pd.DataFrame:
    rows = db.query(MetricEvent).order_by(MetricEvent.created_at.desc()).all()
    if not rows:
        return pd.DataFrame()
    records = []
    for r in rows:
        props = {}
        try:
            props = json.loads(r.properties or "{}")
        except Exception:
            pass
        records.append({
            "id":         r.id,
            "username":   r.username,
            "event_name": r.event_name,
            "subject":    r.subject or "",
            "created_at": r.created_at,
            **props,
        })
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _feature_adoption(df: pd.DataFrame) -> pd.DataFrame:
    """Metric 1 — Feature Adoption Rate."""
    if df.empty:
        return pd.DataFrame()

    # Sessions = unique (username, date) pairs
    df["date"] = pd.to_datetime(df["created_at"]).dt.date
    sessions = df.groupby(["username", "date"]).ngroups
    if sessions == 0:
        return pd.DataFrame()

    feature_map = {
        "Material Upload":        df["event_name"].isin(["doc_parse", "document_uploaded"]),
        "Study Guide Generated":  df["event_name"] == "generation",
        "Quiz Attempted":         df["event_name"] == "quiz_submitted",
        "Settings / API Config":  df["event_name"].isin(["api_key_saved", "settings_opened"]),
    }
    targets    = {"Material Upload": 25, "Study Guide Generated": 85, "Quiz Attempted": 85, "Settings / API Config": 50}
    thresholds = {"Material Upload": None, "Study Guide Generated": 50, "Quiz Attempted": None, "Settings / API Config": None}

    rows = []
    for feature, mask in feature_map.items():
        feature_sessions = df[mask].groupby(["username", "date"]).ngroups
        pct = round(feature_sessions / sessions * 100, 1)
        target = targets[feature]
        threshold = thresholds[feature]
        status = "✅" if pct >= target else ("⚠️" if threshold and pct >= threshold else "🔴")
        rows.append({
            "Feature":          feature,
            "Sessions Used":    feature_sessions,
            "Total Sessions":   sessions,
            "Adoption %":       f"{pct}%",
            "Target":           f">= {target}%",
            "Status":           status,
        })
    return pd.DataFrame(rows)


def _session_duration(df: pd.DataFrame) -> pd.DataFrame:
    """Metric 2 — Average Session Duration (proxy: events per user per day)."""
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["created_at"]).dt.date
    grouped = df.groupby(["username", "date"])
    durations = grouped["created_at"].agg(lambda x: (x.max() - x.min()).total_seconds() / 60)
    avg = round(durations.mean(), 1)
    median = round(durations.median(), 1)
    return pd.DataFrame([{
        "Metric":         "Avg Session Duration",
        "Value":          f"{avg} min",
        "Median":         f"{median} min",
        "Target":         "> 25 min",
        "Status":         "✅" if avg >= 25 else ("⚠️" if avg >= 15 else "🔴"),
    }, {
        "Metric":         "Sessions < 15 min (friction)",
        "Value":          f"{(durations < 15).sum()} sessions",
        "Median":         "—",
        "Target":         "< 20% of sessions",
        "Status":         "✅" if (durations < 15).mean() < 0.2 else "🔴",
    }])


def _funnel_completion(df: pd.DataFrame) -> pd.DataFrame:
    """Metric 4 — Task Completion Rate for each funnel."""
    if df.empty:
        return pd.DataFrame()

    funnels = {
        "Study Flow":      (["doc_parse", "document_uploaded"], "generation"),
        "Evaluation Flow": (["doc_parse", "document_uploaded"], "quiz_submitted"),
        "Onboarding Flow": (["doc_parse", "document_uploaded"], "api_key_saved"),
    }

    rows = []
    for fname, (start_events, end_event) in funnels.items():
        started  = df[df["event_name"].isin(start_events)]["username"].nunique()
        completed = df[df["event_name"] == end_event]["username"].nunique()
        if started == 0:
            rows.append({"Funnel": fname, "Started": 0, "Completed": 0, "Rate": "N/A", "Status": "—"})
            continue
        rate = round(completed / started * 100, 1)
        rows.append({
            "Funnel":    fname,
            "Started":   started,
            "Completed": completed,
            "Rate":      f"{rate}%",
            "Status":    "✅" if rate >= 80 else ("⚠️" if rate >= 50 else "🔴"),
        })
    return pd.DataFrame(rows)


def _retention(df: pd.DataFrame) -> pd.DataFrame:
    """Metric 5 — Session Frequency (returning vs new users, last 7 days)."""
    if df.empty:
        return pd.DataFrame()

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    df["created_at"] = pd.to_datetime(df["created_at"])
    this_week = set(df[df["created_at"] >= week_ago]["username"].unique())
    last_week = set(df[(df["created_at"] >= two_weeks_ago) & (df["created_at"] < week_ago)]["username"].unique())

    returning = len(this_week & last_week)
    new_users = len(this_week - last_week)
    total = returning + new_users

    return pd.DataFrame([{
        "Period":         "Last 7 days",
        "Active Users":   total,
        "Returning":      returning,
        "New":            new_users,
        "Retention %":    f"{round(returning/total*100,1)}%" if total else "N/A",
        "Target":         "80% returning",
        "Status":         "✅" if total and returning/total >= 0.8 else "🔴",
    }])


def _api_health(df: pd.DataFrame) -> pd.DataFrame:
    """Metric 6 — API Success vs Failure Rate.

    Counts explicit `generation_failed` events (logged from gemini.py whenever a
    Gemini call raises, including 503 UNAVAILABLE / quota errors) against
    successful `generation` events. This replaces the old approach of guessing
    failures from a regex over event names, which missed failures that were
    caught and silently replaced with a fallback string in the study guide.
    """
    if df.empty:
        return pd.DataFrame()

    gen_events = df[df["event_name"] == "generation"]
    fail_events = df[df["event_name"] == "generation_failed"]

    total_gen  = len(gen_events)
    total_fail = len(fail_events)
    total      = total_gen + total_fail
    fail_rate  = round(total_fail / total * 100, 1) if total else 0

    return pd.DataFrame([{
        "Metric":         "Generation Requests",
        "Count":          total_gen,
        "Failures":       total_fail,
        "Failure Rate":   f"{fail_rate}%",
        "Target":         "< 30% failure",
        "Status":         "✅" if fail_rate < 30 else "🔴",
    }])


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_db_inspector_tab():
    db = SessionLocal()
    try:
        df = _load_events(db)

        tab_db, tab_metrics, tab_users_activity, tab_users = st.tabs([
            "🕵️ Database Inspector",
            "📊 Product Metrics",
            "👤 Per-User Activity",
            "👥 Users",
        ])

        # ── Tab 1: Database Inspector ──────────────────────────────────────
        with tab_db:
            st.subheader("🕵️ Database Inspector")
            st.caption("Read-only audit of all Postgres tables.")
            table = st.selectbox("Select Table", [
                "Users", "Workspaces", "Source Files",
                "Source Images", "Study Guides", "Quiz Attempts", "Metric Events",
            ])
            st.divider()

            if table == "Users":
                records = db.query(User).all()
                if records:
                    st.dataframe(pd.DataFrame([{
                        "Username": u.username,
                        "Admin": u.is_admin,
                        "Created": u.created_at,
                    } for u in records]), use_container_width=True)
                else:
                    st.info("No users yet.")

            elif table == "Workspaces":
                records = db.query(Workspace).all()
                if records:
                    st.dataframe(pd.DataFrame([{
                        "ID": w.id, "Owner": w.user_id,
                        "Subject": w.subject_name, "Created": w.created_at,
                    } for w in records]), use_container_width=True)
                else:
                    st.info("No workspaces yet.")

            elif table == "Source Files":
                records = db.query(SourceFile).all()
                if records:
                    st.dataframe(pd.DataFrame([{
                        "Name": f.name, "Type": f.file_type,
                        "Chars": len(f.content_text), "Hash": f.file_hash[:8],
                        "Workspace": f.workspace_id[:8], "Created": f.created_at,
                    } for f in records]), use_container_width=True)
                else:
                    st.info("No files indexed yet.")

            elif table == "Source Images":
                records = db.query(SourceImage).all()
                if records:
                    st.dataframe(pd.DataFrame([{
                        "Label": i.label, "Mime": i.mime_type, "Path": i.storage_path,
                    } for i in records]), use_container_width=True)
                else:
                    st.info("No images indexed.")

            elif table == "Study Guides":
                records = db.query(StudyGuide).all()
                if records:
                    st.dataframe(pd.DataFrame([{
                        "Title": g.title, "Chars": len(g.content_md),
                        "Workspace": g.workspace_id[:8], "Created": g.created_at,
                    } for g in records]), use_container_width=True)
                else:
                    st.info("No guides generated yet.")

            elif table == "Quiz Attempts":
                records = db.query(QuizAttempt).all()
                if records:
                    st.dataframe(pd.DataFrame([{
                        "Score": f"{q.score}%", "Workspace": q.workspace_id[:8],
                        "Created": q.created_at,
                    } for q in records]), use_container_width=True)
                else:
                    st.info("No quiz attempts yet.")

            elif table == "Metric Events":
                if not df.empty:
                    st.dataframe(
                        df[["username", "event_name", "subject", "created_at"]].head(200),
                        use_container_width=True,
                    )
                else:
                    st.info("No metric events recorded yet.")

        # ── Tab 2: Product Metrics ─────────────────────────────────────────
        with tab_metrics:
            st.subheader("📊 Product Metrics Dashboard")

            if df.empty:
                st.info("No events recorded yet. Metrics will appear once users interact with the app.")
            else:
                total_events = len(df)
                total_users  = df["username"].nunique()
                date_range   = f"{df['created_at'].min()} → {df['created_at'].max()}" if "created_at" in df.columns else "—"

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Events", total_events)
                c2.metric("Unique Users", total_users)
                c3.metric("Event Types", df["event_name"].nunique())

                st.caption(f"Data range: {date_range}")
                st.divider()

                st.markdown("### Metric 1 — Feature Adoption Rate")
                fa = _feature_adoption(df)
                if not fa.empty:
                    st.dataframe(fa, use_container_width=True, hide_index=True)
                st.divider()

                st.markdown("### Metric 2 — Session Duration")
                sd = _session_duration(df)
                if not sd.empty:
                    st.dataframe(sd, use_container_width=True, hide_index=True)
                st.divider()

                st.markdown("### Metric 4 — Task Completion Funnels")
                fc = _funnel_completion(df)
                if not fc.empty:
                    st.dataframe(fc, use_container_width=True, hide_index=True)
                st.divider()

                st.markdown("### Metric 5 — Retention (Returning vs New)")
                ret = _retention(df)
                if not ret.empty:
                    st.dataframe(ret, use_container_width=True, hide_index=True)
                st.divider()

                st.markdown("### Metric 6 — API Health")
                health = _api_health(df)
                if not health.empty:
                    st.dataframe(health, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("### Raw Event Log")
                event_filter = st.selectbox("Filter by event", ["All"] + sorted(df["event_name"].unique().tolist()))
                filtered = df if event_filter == "All" else df[df["event_name"] == event_filter]
                st.dataframe(
                    filtered[["username", "event_name", "subject", "created_at"]].head(100),
                    use_container_width=True,
                )

        # ── Tab 3: Per-User Activity ───────────────────────────────────────
        with tab_users_activity:
            st.subheader("👤 Per-User Activity")
            if df.empty:
                st.info("No events yet.")
            else:
                users_list = sorted(df["username"].unique().tolist())
                selected   = st.selectbox("Select user", users_list)
                user_df    = df[df["username"] == selected].copy()

                st.markdown(f"**{len(user_df)} events** recorded for `{selected}`")

                c1, c2, c3 = st.columns(3)
                c1.metric("Docs Uploaded",   user_df[user_df["event_name"].isin(["doc_parse","document_uploaded"])].shape[0])
                c2.metric("Guides Generated", user_df[user_df["event_name"] == "generation"].shape[0])
                c3.metric("Quizzes Taken",    user_df[user_df["event_name"] == "quiz_submitted"].shape[0])

                # Quiz scores
                quiz_rows = user_df[user_df["event_name"] == "quiz_submitted"]
                if not quiz_rows.empty and "score" in quiz_rows.columns:
                    scores = quiz_rows["score"].dropna()
                    if not scores.empty:
                        st.metric("Avg Quiz Score", f"{round(scores.mean(), 1)}%")

                st.markdown("#### Event Timeline")
                st.dataframe(
                    user_df[["event_name", "subject", "created_at"]].sort_values("created_at", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )

        # ── Tab 4: Users ──────────────────────────────────────────────────
        with tab_users:
            st.subheader("👥 Registered Users")
            users = db.query(User).all()
            if users:
                st.dataframe(pd.DataFrame([{
                    "Username":   u.username,
                    "Admin":      "✅" if u.is_admin else "—",
                    "Workspaces": len(u.workspaces),
                    "Registered": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "—",
                } for u in users]), use_container_width=True, hide_index=True)
            else:
                st.info("No users yet.")

    except Exception:
        logger.error("Admin dashboard failed", exc_info=True)
        st.error("Something went wrong loading the dashboard.")
    finally:
        db.close()

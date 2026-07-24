"""
Autonomous weak-area study agent — decision logic (Step 1 of 2).

This module is the "brain" of the agent: it PERCEIVES performance from
quiz history, SCOREs mastery per topic, DECIDEs what to target next
without a human picking it, and defines when the LOOP should stop.

It deliberately does NOT call Gemini, touch Streamlit, or write to the
DB — it's pure functions over plain data, so it's trivial to unit test
and trivial to wire into tabs/quiz.py / tabs/study.py in Step 2.

The four agent phases, and where each lives:

    PERCEIVE  -> compute_mastery()      reads workspace["quiz_history"]
    SCORE     -> compute_mastery()      turns raw answers into 0-100/topic
    DECIDE    -> decide_next_target()   autonomously picks the next topic
    ACT       -> (Step 2)               generate_remediation_pooled(topic)
    EVALUATE  -> (Step 2)               grade the follow-up quiz as usual
    ADAPT     -> compute_mastery()      re-run after the new attempt lands
                                         in quiz_history -> score moves
    LOOP      -> should_continue_loop() keep going until nothing's weak
"""

from dataclasses import dataclass

# A topic is considered "mastered" once its score reaches this. Tune this
# to make the agent stricter/looser about when it stops targeting a topic.
MASTERY_THRESHOLD = 80.0

# Topics seen fewer than this many times don't have a reliable score yet
# (e.g. missed 1/1 questions looks identical to missed 1/1 forever). The
# agent treats "not enough data" as its own kind of urgency and prioritizes
# gathering signal on these before trusting a low-attempt score at face value.
MIN_ATTEMPTS_FOR_CONFIDENCE = 3

# How much weight recent evidence gets vs. lifetime history when scoring.
# 0.0 = pure lifetime accuracy (never forgets/forgives an old mistake).
# 1.0 = pure "what happened last" (no memory at all).
# 0.4 means recent performance moves the needle meaningfully without
# letting one lucky/unlucky question overwrite months of evidence.
RECENCY_EMA_ALPHA = 0.4


@dataclass
class TopicMastery:
    topic: str
    score: float          # 0-100 blended mastery estimate
    attempts: int         # total questions ever seen on this topic
    correct: int          # total correct on this topic
    last_occurrence: int  # index of most recent occurrence, for staleness tie-breaks


def _flatten_topic_occurrences(quiz_history: list[dict]) -> dict[str, list[bool]]:
    """
    PERCEIVE step.

    Walk every quiz attempt in chronological order and flatten every
    question into topic -> [was_correct, was_correct, ...], in the order
    it was actually answered. This is the raw evidence the agent reasons
    over — nothing here decides anything yet, it just organizes the facts.
    """
    by_topic: dict[str, list[bool]] = {}
    for attempt in quiz_history:
        questions = attempt.get("questions", [])
        answers = attempt.get("answers", {})
        for idx, question in enumerate(questions):
            topic = question.get("topic", "General")
            was_correct = answers.get(str(idx)) == question.get("answer_index")
            by_topic.setdefault(topic, []).append(was_correct)
    return by_topic


def compute_mastery(quiz_history: list[dict]) -> dict[str, TopicMastery]:
    """
    PERCEIVE + SCORE step.

    Turns raw quiz history into a 0-100 mastery score per topic by
    blending two signals:

      lifetime_accuracy - correct / attempts, all-time. Stable, but slow
                           to reflect recent improvement.
      recency_ema        - exponential moving average over the
                           chronological sequence of right/wrong answers
                           on that topic. This is what makes the score
                           ADAPT: a student who bombed "Recursion" a
                           month ago but has nailed the last two
                           follow-up quizzes sees their score climb,
                           even though their lifetime accuracy is still
                           dragged down by the old misses.

    final score = 50% lifetime_accuracy + 50% recency_ema, so one bad
    early quiz can't permanently cap a topic, and one lucky recent
    answer can't fully erase a real gap either.
    """
    by_topic = _flatten_topic_occurrences(quiz_history)
    mastery: dict[str, TopicMastery] = {}

    for topic, outcomes in by_topic.items():
        attempts = len(outcomes)
        correct = sum(outcomes)
        lifetime_accuracy = (correct / attempts) * 100 if attempts else 0.0

        # Recency-weighted EMA: seed with the first data point, then blend
        # each subsequent right/wrong in with weight RECENCY_EMA_ALPHA.
        ema = 100.0 if outcomes[0] else 0.0
        for was_correct in outcomes[1:]:
            point = 100.0 if was_correct else 0.0
            ema = (RECENCY_EMA_ALPHA * point) + ((1 - RECENCY_EMA_ALPHA) * ema)

        score = round(0.5 * lifetime_accuracy + 0.5 * ema, 1)

        mastery[topic] = TopicMastery(
            topic=topic,
            score=score,
            attempts=attempts,
            correct=correct,
            last_occurrence=attempts - 1,  # position within this topic's own sequence
        )

    return mastery


def decide_next_target(mastery: dict[str, TopicMastery]) -> TopicMastery | None:
    """
    DECIDE step — the actual autonomous decision policy.

    Priority order (this is the part you'd explain in an interview):

      1. Topics with attempts < MIN_ATTEMPTS_FOR_CONFIDENCE come first,
         regardless of their current score. A topic seen once and missed
         isn't necessarily "worse" than one seen five times at 60% — we
         just don't trust the low-attempt score yet, so the agent
         prioritizes gathering more signal on it.
      2. Among topics with enough attempts, pick the single lowest score
         that's still below MASTERY_THRESHOLD.
      3. Ties broken by staleness — whichever topic hasn't been touched
         in the longest time goes first, so the agent doesn't fixate on
         one topic forever while another quietly rots.
      4. If nothing qualifies (everything's mastered, or there's no
         history yet), return None — this is the agent's signal that
         there's nothing left to autonomously target right now.
    """
    if not mastery:
        return None

    low_confidence = [m for m in mastery.values() if m.attempts < MIN_ATTEMPTS_FOR_CONFIDENCE]
    if low_confidence:
        low_confidence.sort(key=lambda m: (m.score, m.last_occurrence))
        return low_confidence[0]

    weak = [m for m in mastery.values() if m.score < MASTERY_THRESHOLD]
    if not weak:
        return None

    weak.sort(key=lambda m: (m.score, m.last_occurrence))
    return weak[0]


def should_continue_loop(mastery: dict[str, TopicMastery]) -> bool:
    """
    LOOP step. True as long as decide_next_target() would find something
    to work on. Step 2 calls this after each ACT+EVALUATE cycle to decide
    whether to keep generating targeted content or tell the user they've
    cleared their weak areas.
    """
    return decide_next_target(mastery) is not None


def loop_status(quiz_history: list[dict]) -> dict:
    """
    Convenience wrapper for Step 2 / the UI: runs the whole
    PERCEIVE -> SCORE -> DECIDE pipeline in one call and returns a plain
    summary dict, so tabs/quiz.py doesn't need to import TopicMastery
    or know about the internals.
    """
    mastery = compute_mastery(quiz_history)
    next_target = decide_next_target(mastery)
    mastered = [m.topic for m in mastery.values() if m.score >= MASTERY_THRESHOLD]
    weak = [m.topic for m in mastery.values() if m.score < MASTERY_THRESHOLD]

    return {
        "mastery": mastery,
        "next_target": next_target.topic if next_target else None,
        "next_target_score": next_target.score if next_target else None,
        "mastered_topics": mastered,
        "weak_topics": weak,
        "should_continue": next_target is not None,
    }

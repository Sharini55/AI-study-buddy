from utils.agent import compute_mastery, decide_next_target, should_continue_loop, loop_status


def _q(topic, answer_index=0):
    return {"question": f"q about {topic}", "choices": ["a", "b", "c", "d"],
            "answer_index": answer_index, "topic": topic}


def _attempt(topic_results: list[tuple[str, bool]]) -> dict:
    """Build one quiz_history entry from [(topic, was_correct), ...]."""
    questions, answers = [], {}
    for i, (topic, correct) in enumerate(topic_results):
        q = _q(topic, answer_index=0)
        questions.append(q)
        answers[str(i)] = 0 if correct else 1
    return {"score": 0, "questions": questions, "answers": answers, "missed_questions": []}


def test_no_history_means_nothing_to_target():
    mastery = compute_mastery([])
    assert decide_next_target(mastery) is None
    assert should_continue_loop(mastery) is False


def test_weak_topic_is_identified_and_prioritized():
    # Recursion missed twice, Loops aced twice -> agent should target Recursion
    history = [
        _attempt([("Recursion", False), ("Loops", True)]),
        _attempt([("Recursion", False), ("Loops", True)]),
        _attempt([("Recursion", False), ("Loops", True)]),
    ]
    mastery = compute_mastery(history)
    target = decide_next_target(mastery)
    assert target is not None
    assert target.topic == "Recursion"
    assert target.score < mastery["Loops"].score


def test_low_attempt_topics_are_prioritized_over_low_score_topics():
    # "Pointers" seen once and missed (low confidence) should outrank
    # "Recursion" which has a stable-but-mediocre score over many attempts.
    history = [
        _attempt([("Recursion", True), ("Recursion", False), ("Recursion", True),
                  ("Recursion", False), ("Recursion", True)]),
        _attempt([("Pointers", False)]),
    ]
    mastery = compute_mastery(history)
    target = decide_next_target(mastery)
    assert target.topic == "Pointers"


def test_adapt_improves_score_after_follow_up_success():
    history = [_attempt([("Recursion", False)])]
    before = compute_mastery(history)["Recursion"].score

    # simulate the student doing well on a follow-up targeted quiz
    history.append(_attempt([("Recursion", True)]))
    history.append(_attempt([("Recursion", True)]))
    after = compute_mastery(history)["Recursion"].score

    assert after > before


def test_loop_terminates_once_everything_is_mastered():
    history = [_attempt([("Recursion", True)]) for _ in range(5)]
    status = loop_status(history)
    assert status["should_continue"] is False
    assert status["next_target"] is None
    assert "Recursion" in status["mastered_topics"]


if __name__ == "__main__":
    import sys
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    sys.exit(1 if failed else 0)

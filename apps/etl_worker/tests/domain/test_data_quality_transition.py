"""Tests de domain/data_quality_transition.py : détection de transition
data_quality par site, en mémoire, cycle par cycle.

Trois zones : good / minor (partial) / alert (degraded, critical).
detect_transition() ne modifie pas l'état : commit() doit être appelé
explicitement pour faire avancer la mémoire (imite EtlJob, qui ne commit
qu'après une publication réussie)."""

from domain.data_quality_transition import (
    EVENT_ALERT,
    EVENT_MINOR_ALERT,
    EVENT_RECOVERY,
    DataQualityTransitionDetector,
)


def test_first_reading_never_triggers_event_even_if_critical():
    detector = DataQualityTransitionDetector()

    event = detector.detect_transition("SITE001", "critical")

    assert event is None


def test_good_to_degraded_triggers_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")

    event = detector.detect_transition("SITE001", "degraded")

    assert event == EVENT_ALERT


def test_good_to_critical_triggers_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")

    event = detector.detect_transition("SITE001", "critical")

    assert event == EVENT_ALERT


def test_partial_to_degraded_triggers_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "partial")
    detector.commit("SITE001", "partial")

    event = detector.detect_transition("SITE001", "degraded")

    assert event == EVENT_ALERT


def test_degraded_to_critical_does_not_retrigger_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "degraded")
    detector.commit("SITE001", "degraded")

    event = detector.detect_transition("SITE001", "critical")

    assert event is None


def test_good_to_partial_triggers_minor_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")

    event = detector.detect_transition("SITE001", "partial")

    assert event == EVENT_MINOR_ALERT


def test_critical_to_partial_triggers_minor_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "critical")
    detector.commit("SITE001", "critical")

    event = detector.detect_transition("SITE001", "partial")

    assert event == EVENT_MINOR_ALERT


def test_degraded_to_partial_triggers_minor_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "degraded")
    detector.commit("SITE001", "degraded")

    event = detector.detect_transition("SITE001", "partial")

    assert event == EVENT_MINOR_ALERT


def test_repeated_partial_does_not_retrigger_minor_alert():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "partial")
    detector.commit("SITE001", "partial")

    event = detector.detect_transition("SITE001", "partial")

    assert event is None


def test_degraded_to_good_triggers_recovery():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "degraded")
    detector.commit("SITE001", "degraded")

    event = detector.detect_transition("SITE001", "good")

    assert event == EVENT_RECOVERY


def test_critical_to_good_triggers_recovery():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "critical")
    detector.commit("SITE001", "critical")

    event = detector.detect_transition("SITE001", "good")

    assert event == EVENT_RECOVERY


def test_partial_to_good_triggers_recovery():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "partial")
    detector.commit("SITE001", "partial")

    event = detector.detect_transition("SITE001", "good")

    assert event == EVENT_RECOVERY


def test_repeated_same_alert_state_no_event():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "critical")
    detector.commit("SITE001", "critical")

    event = detector.detect_transition("SITE001", "critical")

    assert event is None


def test_sites_are_tracked_independently():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "critical")
    detector.commit("SITE001", "critical")

    event = detector.detect_transition("SITE002", "critical")

    assert event is None  # SITE002 vu pour la première fois


def test_without_commit_the_same_transition_is_detected_again():
    """Retry : si l'appelant ne commit pas (ex. échec de publication), la
    même transition doit rester détectable au cycle suivant."""
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")

    first_attempt = detector.detect_transition("SITE001", "critical")
    # pas de commit ici : simule un échec de publication

    second_attempt = detector.detect_transition("SITE001", "critical")

    assert first_attempt == EVENT_ALERT
    assert second_attempt == EVENT_ALERT


def test_commit_after_retry_stops_further_retriggering():
    detector = DataQualityTransitionDetector()
    detector.detect_transition("SITE001", "good")
    detector.commit("SITE001", "good")
    detector.detect_transition("SITE001", "critical")  # échec simulé, pas commité
    detector.detect_transition("SITE001", "critical")
    detector.commit("SITE001", "critical")  # réussi cette fois

    event = detector.detect_transition("SITE001", "critical")

    assert event is None

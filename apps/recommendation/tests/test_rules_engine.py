from application.rules_engine import RecommendationEngine
from domain.entities import PowerFactorReading, Prediction, Site

SITE = Site(site_id="SITE001", capacity_kw=100.0)


def _prediction(consumption_kw=50.0, target_timestamp=None, model_version="v1"):
    return Prediction(
        site_id="SITE001",
        predicted_consumption_kw=consumption_kw,
        target_timestamp=target_timestamp,
        model_version=model_version,
    )


# --- Règle 1 : charge prédite > 90 % de capacity_kw -> décalage de charge ---


def test_load_shifting_triggers_above_ninety_percent_of_capacity():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=95.0)

    recommendations = engine.evaluate(prediction, SITE)

    assert len(recommendations) == 1
    reco = recommendations[0]
    assert reco.site_id == "SITE001"
    assert reco.type == "load_shifting"
    assert reco.estimated_gain_kwh == 5.0  # 95 - (100 * 0.9)
    assert reco.model_version == "v1"


def test_load_shifting_does_not_trigger_exactly_at_ninety_percent():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=90.0)

    recommendations = engine.evaluate(prediction, SITE)

    assert recommendations == []


def test_load_shifting_does_not_trigger_below_ninety_percent():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=80.0)

    recommendations = engine.evaluate(prediction, SITE)

    assert recommendations == []


# --- Règle 2 : pic prédit sur créneau de pointe -> report vers un creux ---


def test_peak_shift_triggers_when_target_timestamp_is_within_peak_hours():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=50.0, target_timestamp="2026-09-17T14:00:00Z")

    recommendations = engine.evaluate(prediction, SITE)

    assert len(recommendations) == 1
    reco = recommendations[0]
    assert reco.type == "peak_shift"
    assert reco.estimated_gain_kwh == 50.0
    assert reco.model_version == "v1"


def test_peak_shift_does_not_trigger_outside_peak_hours():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=50.0, target_timestamp="2026-09-17T23:00:00Z")

    recommendations = engine.evaluate(prediction, SITE)

    assert recommendations == []


def test_peak_shift_does_not_trigger_without_a_target_timestamp():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=50.0, target_timestamp=None)

    recommendations = engine.evaluate(prediction, SITE)

    assert recommendations == []


# --- Règle 3 : power_factor < 0,90 -> compensation ---


def test_power_factor_compensation_triggers_below_threshold():
    engine = RecommendationEngine()
    prediction = _prediction()
    power_factor = PowerFactorReading(site_id="SITE001", power_factor=0.85)

    recommendations = engine.evaluate(prediction, SITE, power_factor=power_factor)

    assert len(recommendations) == 1
    reco = recommendations[0]
    assert reco.type == "power_factor_compensation"
    assert reco.estimated_gain_kwh is None
    assert reco.model_version == "v1"


def test_power_factor_compensation_does_not_trigger_at_or_above_threshold():
    engine = RecommendationEngine()
    prediction = _prediction()
    power_factor = PowerFactorReading(site_id="SITE001", power_factor=0.90)

    recommendations = engine.evaluate(prediction, SITE, power_factor=power_factor)

    assert recommendations == []


def test_power_factor_compensation_does_not_trigger_when_reading_is_unavailable():
    engine = RecommendationEngine()
    prediction = _prediction()

    recommendations = engine.evaluate(prediction, SITE, power_factor=None)

    assert recommendations == []


# --- Plusieurs règles déclenchées simultanément ---


def test_multiple_rules_can_trigger_at_once():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=95.0, target_timestamp="2026-09-17T14:00:00Z")
    power_factor = PowerFactorReading(site_id="SITE001", power_factor=0.80)

    recommendations = engine.evaluate(prediction, SITE, power_factor=power_factor)

    assert {r.type for r in recommendations} == {
        "load_shifting",
        "peak_shift",
        "power_factor_compensation",
    }


def test_returns_an_empty_list_when_no_rule_is_triggered():
    engine = RecommendationEngine()
    prediction = _prediction(consumption_kw=50.0)

    recommendations = engine.evaluate(prediction, SITE)

    assert recommendations == []

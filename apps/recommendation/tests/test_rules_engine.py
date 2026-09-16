from application.rules_engine import RecommendationEngine
from domain.entities import Prediction, Site


def test_returns_a_recommendation_when_input_data_triggers_a_rule():
    engine = RecommendationEngine()
    site = Site(site_id="SITE001", capacity_kw=100.0)
    prediction = Prediction(site_id="SITE001", predicted_consumption_kw=120.0)

    recommendations = engine.evaluate(prediction, site)

    assert len(recommendations) == 1
    assert recommendations[0].site_id == "SITE001"
    assert recommendations[0].type == "load_shedding"


def test_returns_an_empty_list_when_no_rule_is_triggered():
    engine = RecommendationEngine()
    site = Site(site_id="SITE001", capacity_kw=100.0)
    prediction = Prediction(site_id="SITE001", predicted_consumption_kw=80.0)

    recommendations = engine.evaluate(prediction, site)

    assert recommendations == []


def test_predicted_consumption_exactly_at_capacity_does_not_trigger_the_rule():
    engine = RecommendationEngine()
    site = Site(site_id="SITE001", capacity_kw=100.0)
    prediction = Prediction(site_id="SITE001", predicted_consumption_kw=100.0)

    recommendations = engine.evaluate(prediction, site)

    assert recommendations == []

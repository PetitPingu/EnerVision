from unittest.mock import Mock

from application.generate_recommendations import GenerateRecommendations
from domain.entities import Prediction, Site

SITE = Site(site_id="SITE001", capacity_kw=100.0)
PREDICTION = Prediction(site_id="SITE001", predicted_consumption_kw=120.0)


def _use_case(site=SITE, prediction=PREDICTION):
    prediction_api = Mock()
    prediction_api.get_prediction.return_value = prediction
    site_repository = Mock()
    site_repository.get_site.return_value = site
    recommendation_repository = Mock()
    use_case = GenerateRecommendations(prediction_api, site_repository, recommendation_repository)
    return use_case, prediction_api, site_repository, recommendation_repository


def test_returns_none_when_site_is_unknown():
    use_case, _, _, recommendation_repository = _use_case(site=None)

    result = use_case.execute("SITE404")

    assert result is None
    recommendation_repository.save.assert_not_called()


def test_returns_none_when_prediction_is_unavailable():
    use_case, _, _, recommendation_repository = _use_case(prediction=None)

    result = use_case.execute("SITE001")

    assert result is None
    recommendation_repository.save.assert_not_called()


def test_persists_and_returns_triggered_recommendations():
    use_case, _, _, recommendation_repository = _use_case()

    result = use_case.execute("SITE001")

    assert len(result) == 1
    assert result[0].type == "load_shedding"
    recommendation_repository.save.assert_called_once_with(result)


def test_returns_empty_list_and_persists_nothing_when_no_rule_triggers():
    use_case, _, _, recommendation_repository = _use_case(
        prediction=Prediction(site_id="SITE001", predicted_consumption_kw=50.0)
    )

    result = use_case.execute("SITE001")

    assert result == []
    recommendation_repository.save.assert_called_once_with([])

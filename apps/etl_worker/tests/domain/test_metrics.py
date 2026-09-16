from domain.imputation import METHOD_FORWARD_FILL, METHOD_NO_HISTORY
from domain.metrics import imputation_metrics


def _row(site_id: str, method: str | None) -> dict:
    return {"site_id": site_id, "imputation_methods": method}


def test_no_imputation_gives_zero_percent_for_the_site():
    rows = [_row("SITE001", None), _row("SITE001", None)]

    metrics = imputation_metrics(rows)

    assert metrics == {"SITE001": 0.0}


def test_percentage_is_relative_to_the_site_total():
    rows = [
        _row("SITE001", METHOD_FORWARD_FILL),
        _row("SITE001", None),
        _row("SITE001", None),
        _row("SITE001", None),
    ]

    metrics = imputation_metrics(rows)

    assert metrics == {"SITE001": 25.0}


def test_no_history_does_not_count_as_imputed():
    rows = [_row("SITE001", METHOD_NO_HISTORY), _row("SITE001", None)]

    metrics = imputation_metrics(rows)

    assert metrics == {"SITE001": 0.0}


def test_sites_are_tracked_independently():
    rows = [_row("SITE001", METHOD_FORWARD_FILL), _row("SITE002", None)]

    metrics = imputation_metrics(rows)

    assert metrics == {"SITE001": 100.0, "SITE002": 0.0}


def test_empty_input_gives_empty_metrics():
    assert imputation_metrics([]) == {}

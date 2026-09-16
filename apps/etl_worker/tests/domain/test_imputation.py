"""Tests de domain/imputation.py : ConsumptionKwhImputer comble
consumption_kwh par forward-fill, en mémoire, lecture par lecture."""

from domain.imputation import METHOD_FORWARD_FILL, METHOD_NO_HISTORY, ConsumptionKwhImputer


def test_known_value_is_kept_and_remembered():
    imputer = ConsumptionKwhImputer()

    value, method = imputer.impute("SITE001", 10.0)

    assert value == 10.0
    assert method is None


def test_missing_value_takes_the_last_known_one():
    imputer = ConsumptionKwhImputer()
    imputer.impute("SITE001", 10.0)

    value, method = imputer.impute("SITE001", None)

    assert value == 10.0
    assert method == METHOD_FORWARD_FILL


def test_missing_value_with_no_prior_known_value_stays_none_with_no_history():
    imputer = ConsumptionKwhImputer()

    value, method = imputer.impute("SITE001", None)

    assert value is None
    assert method == METHOD_NO_HISTORY


def test_repeated_missing_values_keep_reusing_the_last_known_one():
    imputer = ConsumptionKwhImputer()
    imputer.impute("SITE001", 42.0)

    for _ in range(3):
        value, method = imputer.impute("SITE001", None)
        assert value == 42.0
        assert method == METHOD_FORWARD_FILL


def test_a_new_known_value_replaces_the_remembered_one():
    imputer = ConsumptionKwhImputer()
    imputer.impute("SITE001", 10.0)
    imputer.impute("SITE001", None)  # comblé à 10.0

    value, method = imputer.impute("SITE001", 99.0)

    assert value == 99.0
    assert method is None

    value, method = imputer.impute("SITE001", None)
    assert value == 99.0
    assert method == METHOD_FORWARD_FILL


def test_sites_are_tracked_independently():
    imputer = ConsumptionKwhImputer()
    imputer.impute("SITE001", 10.0)

    value, method = imputer.impute("SITE002", None)

    assert value is None
    assert method == METHOD_NO_HISTORY

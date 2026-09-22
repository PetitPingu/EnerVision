from db_schema import models as orm_models
from db_schema.database import Base


def test_registers_one_table_per_entity_in_the_enervision_schema():
    tables = Base.metadata.tables

    assert set(tables) == {
        "enervision.sites",
        "enervision.alerts",
        "enervision.readings_curated",
        "enervision.recommendations",
        "enervision.predictions_log",
        "enervision.users",
        "enervision.user_sites",
    }
    assert all(table.schema == "enervision" for table in tables.values())


def test_sites_primary_key_is_site_id():
    pk_columns = [c.name for c in orm_models.Site.__table__.primary_key.columns]

    assert pk_columns == ["site_id"]


def test_alerts_primary_key_is_alert_id():
    pk_columns = [c.name for c in orm_models.Alert.__table__.primary_key.columns]

    assert pk_columns == ["alert_id"]


def test_readings_curated_primary_key_is_composite_for_hypertable_partitioning():
    pk_columns = [c.name for c in orm_models.ReadingCurated.__table__.primary_key.columns]

    assert pk_columns == ["site_id", "timestamp"]


def test_readings_curated_has_a_single_column_per_measured_field():
    columns = {c.name for c in orm_models.ReadingCurated.__table__.columns}

    for field in ("consumption_kw", "voltage_v", "temperature_celsius"):
        assert field in columns
        assert f"{field}_imputed" not in columns
    assert "imputation_methods" in columns


def test_recommendations_primary_key_is_id():
    pk_columns = [c.name for c in orm_models.Recommendation.__table__.primary_key.columns]

    assert pk_columns == ["id"]


def test_recommendations_prediction_id_is_nullable():
    column = orm_models.Recommendation.__table__.columns["prediction_id"]

    assert column.nullable


def test_recommendations_references_model_version_and_estimated_gain():
    columns = orm_models.Recommendation.__table__.columns

    assert columns["model_version"].nullable
    assert columns["estimated_gain_kwh"].nullable


def test_users_primary_key_is_id():
    pk_columns = [c.name for c in orm_models.User.__table__.primary_key.columns]

    assert pk_columns == ["id"]


def test_users_email_is_unique_and_not_nullable():
    column = orm_models.User.__table__.columns["email"]

    assert column.unique
    assert not column.nullable


def test_users_role_is_nullable():
    column = orm_models.User.__table__.columns["role"]

    assert column.nullable


def test_user_sites_primary_key_is_composite():
    pk_columns = [c.name for c in orm_models.UserSite.__table__.primary_key.columns]

    assert pk_columns == ["user_id", "site_id"]

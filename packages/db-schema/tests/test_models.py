from db_schema import models as orm_models
from db_schema.database import Base


def test_registers_one_table_per_entity_in_the_enervision_schema():
    tables = Base.metadata.tables

    assert set(tables) == {
        "enervision.sites",
        "enervision.readings",
        "enervision.alerts",
        "enervision.consumption_readings",
    }
    assert all(table.schema == "enervision" for table in tables.values())


def test_sites_primary_key_is_site_id():
    pk_columns = [c.name for c in orm_models.Site.__table__.primary_key.columns]

    assert pk_columns == ["site_id"]


def test_readings_primary_key_is_composite_for_hypertable_partitioning():
    pk_columns = [c.name for c in orm_models.Reading.__table__.primary_key.columns]

    assert pk_columns == ["site_id", "timestamp"]


def test_alerts_primary_key_is_alert_id():
    pk_columns = [c.name for c in orm_models.Alert.__table__.primary_key.columns]

    assert pk_columns == ["alert_id"]


def test_consumption_readings_primary_key_is_composite_for_hypertable_partitioning():
    pk_columns = [c.name for c in orm_models.ConsumptionReading.__table__.primary_key.columns]

    assert pk_columns == ["site_id", "timestamp"]

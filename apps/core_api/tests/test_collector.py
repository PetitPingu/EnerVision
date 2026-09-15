from unittest.mock import Mock

from application.collector import SensorDataCollector
from domain.entities import Reading, Site

SITE = Site(site_id="SITE001", site_name="Bureau Paris")
READING = Reading(site_id="SITE001", timestamp="2024-06-15T14:32:00.123456", data_quality="good")


def test_collect_all_fetches_readings():
    api = Mock()
    api.get_sites.return_value = [SITE]
    api.get_current_reading.return_value = READING

    collector = SensorDataCollector(api=api)
    readings = collector.collect_all()

    assert readings == [READING]
    api.get_current_reading.assert_called_once_with("SITE001")


def test_collect_all_handles_api_unavailable_without_crash():
    api = Mock()
    api.get_sites.return_value = []  # API mock indisponible

    collector = SensorDataCollector(api=api)
    readings = collector.collect_all()

    assert readings == []


def test_collect_all_continues_when_one_site_reading_fails():
    other_site = Site(site_id="SITE002")
    api = Mock()
    api.get_sites.return_value = [SITE, other_site]
    api.get_current_reading.side_effect = [None, READING]  # SITE001 KO, SITE002 OK

    collector = SensorDataCollector(api=api)
    readings = collector.collect_all()

    assert readings == [READING]

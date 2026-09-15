from datetime import datetime, timezone
from unittest.mock import Mock

from infrastructure.bronze_reader import BronzeReader


def _mock_object(name: str):
    obj = Mock()
    obj.object_name = name
    return obj


def test_read_hour_uses_year_month_day_hour_prefix():
    client = Mock()
    client.list_objects.return_value = []
    reader = BronzeReader(client=client, bucket="bronze")

    reader.read_hour(datetime(2026, 9, 15, 10, 30, tzinfo=timezone.utc))

    client.list_objects.assert_called_once_with("bronze", prefix="2026/09/15/10/", recursive=True)


def test_read_hour_returns_content_of_each_object():
    client = Mock()
    client.list_objects.return_value = [
        _mock_object("2026/09/15/10/SITE001_x.json"),
        _mock_object("2026/09/15/10/SITE002_x.json"),
    ]
    response1 = Mock()
    response1.read.return_value = b'{"site_id": "SITE001"}'
    response2 = Mock()
    response2.read.return_value = b'{"site_id": "SITE002"}'
    client.get_object.side_effect = [response1, response2]

    reader = BronzeReader(client=client, bucket="bronze")
    payloads = reader.read_hour(datetime(2026, 9, 15, 10, tzinfo=timezone.utc))

    assert payloads == [b'{"site_id": "SITE001"}', b'{"site_id": "SITE002"}']
    response1.close.assert_called_once()
    response1.release_conn.assert_called_once()


def test_read_hour_returns_empty_list_when_no_objects():
    client = Mock()
    client.list_objects.return_value = []
    reader = BronzeReader(client=client, bucket="bronze")

    payloads = reader.read_hour(datetime(2026, 9, 15, 10, tzinfo=timezone.utc))

    assert payloads == []

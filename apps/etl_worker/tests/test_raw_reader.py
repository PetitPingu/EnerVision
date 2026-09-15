from datetime import date
from unittest.mock import Mock

from infrastructure.raw_reader import RawReader


def _mock_object(name: str):
    obj = Mock()
    obj.object_name = name
    return obj


def test_read_date_uses_date_prefix():
    client = Mock()
    client.list_objects.return_value = []
    reader = RawReader(client=client, bucket="raw")

    reader.read_date(date(2026, 9, 15))

    client.list_objects.assert_called_once_with("raw", prefix="2026-09-15/", recursive=True)


def test_read_date_returns_content_of_each_object():
    client = Mock()
    client.list_objects.return_value = [
        _mock_object("2026-09-15/SITE001.json"),
        _mock_object("2026-09-15/SITE002.json"),
    ]
    response1 = Mock()
    response1.read.return_value = b'{"site_id": "SITE001"}'
    response2 = Mock()
    response2.read.return_value = b'{"site_id": "SITE002"}'
    client.get_object.side_effect = [response1, response2]

    reader = RawReader(client=client, bucket="raw")
    payloads = reader.read_date(date(2026, 9, 15))

    assert payloads == [b'{"site_id": "SITE001"}', b'{"site_id": "SITE002"}']
    response1.close.assert_called_once()
    response1.release_conn.assert_called_once()


def test_read_date_returns_empty_list_when_no_objects():
    client = Mock()
    client.list_objects.return_value = []
    reader = RawReader(client=client, bucket="raw")

    payloads = reader.read_date(date(2026, 9, 15))

    assert payloads == []

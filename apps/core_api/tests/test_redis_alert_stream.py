import json

import pytest
from infrastructure import redis_alert_stream
from infrastructure.redis_alert_stream import RedisAlertStreamReader
from unittest.mock import AsyncMock


def _reader(xread_return):
    client = AsyncMock()
    client.xread.return_value = xread_return
    return RedisAlertStreamReader(client=client), client


@pytest.mark.asyncio
async def test_read_new_parses_entries_into_alert_events():
    xread_return = [
        (
            "alert.detected",
            [
                (
                    "1694950000000-0",
                    {
                        "site_id": "SITE001",
                        "timestamp": "2026-09-15T10:00:00",
                        "data_quality": "critical",
                        "null_reasons": json.dumps(["network_outage"]),
                    },
                )
            ],
        )
    ]
    reader, client = _reader(xread_return)

    events = await reader.read_new("$", block_ms=1000)

    assert len(events) == 1
    event = events[0]
    assert event.event_id == "1694950000000-0"
    assert event.site_id == "SITE001"
    assert event.data_quality == "critical"
    assert event.null_reasons == ["network_outage"]
    assert event.kind == "alert"
    client.xread.assert_called_once_with({"alert.detected": "$"}, block=1000, count=100)


@pytest.mark.asyncio
async def test_read_new_recovery_kind_on_good():
    xread_return = [
        (
            "alert.detected",
            [
                (
                    "1694950000000-1",
                    {
                        "site_id": "SITE001",
                        "timestamp": "2026-09-15T10:05:00",
                        "data_quality": "good",
                        "null_reasons": "[]",
                    },
                )
            ],
        )
    ]
    reader, _ = _reader(xread_return)

    events = await reader.read_new("1694950000000-0", block_ms=1000)

    assert events[0].kind == "recovery"


@pytest.mark.asyncio
async def test_read_new_minor_alert_kind_on_partial():
    xread_return = [
        (
            "alert.detected",
            [
                (
                    "1694950000000-2",
                    {
                        "site_id": "SITE001",
                        "timestamp": "2026-09-15T10:07:00",
                        "data_quality": "partial",
                        "null_reasons": json.dumps(["temperature_sensor_failure"]),
                    },
                )
            ],
        )
    ]
    reader, _ = _reader(xread_return)

    events = await reader.read_new("1694950000000-1", block_ms=1000)

    assert events[0].kind == "minor_alert"


@pytest.mark.asyncio
async def test_read_new_returns_empty_list_on_timeout():
    reader, _ = _reader(None)

    events = await reader.read_new("$", block_ms=1000)

    assert events == []


@pytest.mark.asyncio
async def test_read_new_ignores_malformed_entry():
    xread_return = [("alert.detected", [("1694950000000-2", {"site_id": "SITE001"})])]
    reader, _ = _reader(xread_return)

    events = await reader.read_new("$", block_ms=1000)

    assert events == []


@pytest.mark.asyncio
async def test_read_new_returns_empty_list_when_redis_unavailable():
    client = AsyncMock()
    client.xread.side_effect = RuntimeError("redis down")
    reader = RedisAlertStreamReader(client=client)

    events = await reader.read_new("$", block_ms=1000)

    assert events == []


@pytest.mark.asyncio
async def test_read_new_backs_off_when_redis_unavailable(monkeypatch):
    client = AsyncMock()
    client.xread.side_effect = RuntimeError("connection refused")
    reader = RedisAlertStreamReader(client=client)
    sleep = AsyncMock()
    monkeypatch.setattr(redis_alert_stream.asyncio, "sleep", sleep)

    await reader.read_new("$", block_ms=1000)

    sleep.assert_awaited_once_with(redis_alert_stream.RECONNECT_DELAY_SECONDS)

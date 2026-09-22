"""Tests d'intégration de RedisAlertStreamReader contre un vrai Redis Streams."""

import json
import uuid

import pytest

from infrastructure.redis_alert_stream import STREAM_NAME, RedisAlertStreamReader

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_read_new_returns_events_published_after_the_given_cursor(redis_client):
    site_id = f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}"
    cursor = redis_client.xadd(
        STREAM_NAME,
        {"site_id": "seed", "timestamp": "seed", "data_quality": "good", "null_reasons": "[]"},
    )
    redis_client.xadd(
        STREAM_NAME,
        {
            "site_id": site_id,
            "timestamp": "2026-09-22T10:00:00+00:00",
            "data_quality": "critical",
            "null_reasons": json.dumps(["network_outage"]),
        },
    )

    reader = RedisAlertStreamReader()
    try:
        events = await reader.read_new(cursor, block_ms=1000)
    finally:
        await reader.close()

    assert len(events) == 1
    assert events[0].site_id == site_id
    assert events[0].data_quality == "critical"
    assert events[0].null_reasons == ["network_outage"]


@pytest.mark.asyncio
async def test_read_new_returns_empty_list_when_nothing_new(redis_client):
    cursor = redis_client.xadd(
        STREAM_NAME,
        {"site_id": "seed", "timestamp": "seed", "data_quality": "good", "null_reasons": "[]"},
    )

    reader = RedisAlertStreamReader()
    try:
        events = await reader.read_new(cursor, block_ms=200)
    finally:
        await reader.close()

    assert events == []

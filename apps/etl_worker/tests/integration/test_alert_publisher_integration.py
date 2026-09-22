"""Tests d'intégration de AlertPublisher contre un vrai Redis Streams.

Pas de nettoyage explicite ici : le stream alert.detected est un tampon
temps réel trimmé côté serveur (MAXLEN ~ 500, voir AlertPublisher), pas un
historique - laisser les entrées de test s'y faire éventuellement trimmer
plus tard reflète l'usage réel du stream.
"""

import json

import pytest

from infrastructure.alert_publisher import STREAM_NAME, AlertPublisher

pytestmark = pytest.mark.integration


def test_publish_adds_an_entry_readable_from_the_stream(redis_client):
    publisher = AlertPublisher(client=redis_client)

    publisher.publish(
        site_id="INTEGRATION-TEST-SITE",
        timestamp="2026-09-22T10:00:00+00:00",
        data_quality="critical",
        null_reasons=["network_outage"],
    )

    entries = redis_client.xrevrange(STREAM_NAME, count=1)

    assert len(entries) == 1
    _entry_id, fields = entries[0]
    assert fields["site_id"] == "INTEGRATION-TEST-SITE"
    assert fields["data_quality"] == "critical"
    assert json.loads(fields["null_reasons"]) == ["network_outage"]

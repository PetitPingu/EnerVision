"""Tests d'intégration de MinioModelStore contre un vrai MinIO (roundtrip réel).

Complète tests/model_store/test_minio_store.py (client MagicMock, arguments
passés uniquement) : ici la sérialisation joblib réelle et le
copy_object serveur (promote) sont effectivement exercés.
"""

import uuid

import pytest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from application.ports import SavedModelMetadata
from infrastructure.config import Config
from infrastructure.model_store import MinioModelStore

pytestmark = pytest.mark.integration


def _metadata(model_name: str, trained_at: str = "2026-09-22T10-00-00Z") -> SavedModelMetadata:
    return SavedModelMetadata(
        model_name=model_name,
        trained_at=trained_at,
        metrics={"mae": 1.0, "rmse": 2.0},
        train_size=10,
        test_size=3,
        features=("site_id", "hour"),
    )


@pytest.fixture
def model_name():
    return f"integration-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _cleanup(minio_client, model_name):
    yield
    for obj in minio_client.list_objects(
        Config.MINIO_MODELS_BUCKET, prefix=model_name, recursive=True
    ):
        minio_client.remove_object(Config.MINIO_MODELS_BUCKET, obj.object_name)


def _store(minio_client) -> MinioModelStore:
    return MinioModelStore(
        endpoint=Config.MINIO_ENDPOINT,
        access_key=Config.MINIO_ACCESS_KEY,
        secret_key=Config.MINIO_SECRET_KEY,
        bucket=Config.MINIO_MODELS_BUCKET,
        client=minio_client,
    )


def test_save_then_load_latest_round_trips_pipeline_and_metadata(minio_client, model_name):
    store = _store(minio_client)
    pipeline = Pipeline(steps=[("identity", FunctionTransformer())])

    store.save(pipeline, _metadata(model_name))

    loaded_pipeline, loaded_metadata = store.load_latest(model_name)
    assert isinstance(loaded_pipeline, Pipeline)
    assert loaded_metadata.model_name == model_name
    assert loaded_metadata.metrics == {"mae": 1.0, "rmse": 2.0}
    assert loaded_metadata.features == ("site_id", "hour")


def test_get_current_metadata_returns_none_when_model_was_never_saved(minio_client, model_name):
    assert _store(minio_client).get_current_metadata(model_name) is None


def test_save_twice_promotes_the_second_version_to_latest(minio_client, model_name):
    store = _store(minio_client)
    pipeline = Pipeline(steps=[("identity", FunctionTransformer())])
    store.save(pipeline, _metadata(model_name, trained_at="2026-09-22T10-00-00Z"))

    store.save(pipeline, _metadata(model_name, trained_at="2026-09-22T11-00-00Z"))

    current = store.get_current_metadata(model_name)
    assert current.trained_at == "2026-09-22T11-00-00Z"

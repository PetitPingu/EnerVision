import json
from io import BytesIO
from unittest.mock import MagicMock

import joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from application.ports import SavedModelMetadata
from application.train_and_publish import train_and_publish
from infrastructure.minio_model_store import MinioModelStore
from infrastructure.mock_training_data_reader import MockTrainingDataReader


def _sample_metadata() -> SavedModelMetadata:
    return SavedModelMetadata(
        model_name="energy-consumption",
        trained_at="2026-09-16T14-30-00Z",
        mae=18.2,
        rmse=27.5,
        train_size=100,
        test_size=25,
        features=("site_id", "hour", "minute"),
    )


def test_minio_model_store_save_writes_version_and_latest():
    client = MagicMock()
    store = MinioModelStore(
        endpoint="localhost:9000",
        access_key="user",
        secret_key="pass",
        bucket="models",
        client=client,
    )
    pipeline = Pipeline(steps=[("identity", FunctionTransformer())])

    prefix = store.save(pipeline, _sample_metadata())

    assert prefix == "energy-consumption/2026-09-16T14-30-00Z"
    assert client.put_object.call_count == 4

    keys = [call.args[1] for call in client.put_object.call_args_list]
    assert "energy-consumption/2026-09-16T14-30-00Z/model.joblib" in keys
    assert "energy-consumption/2026-09-16T14-30-00Z/metadata.json" in keys
    assert "energy-consumption/latest/model.joblib" in keys
    assert "energy-consumption/latest/metadata.json" in keys


def test_minio_model_store_load_latest_roundtrip():
    pipeline = Pipeline(steps=[("identity", FunctionTransformer())])
    metadata = _sample_metadata()
    model_buffer = BytesIO()
    joblib.dump(pipeline, model_buffer)
    metadata_buffer = BytesIO(
        json.dumps(
            {
                "model_name": metadata.model_name,
                "trained_at": metadata.trained_at,
                "mae": metadata.mae,
                "rmse": metadata.rmse,
                "train_size": metadata.train_size,
                "test_size": metadata.test_size,
                "features": list(metadata.features),
            }
        ).encode("utf-8")
    )

    client = MagicMock()

    def fake_get_object(_bucket, object_key):
        if object_key.endswith("model.joblib"):
            return BytesIO(model_buffer.getvalue())
        return BytesIO(metadata_buffer.getvalue())

    client.get_object.side_effect = fake_get_object

    store = MinioModelStore(
        endpoint="localhost:9000",
        access_key="user",
        secret_key="pass",
        bucket="models",
        client=client,
    )

    loaded_pipeline, loaded_metadata = store.load_latest("energy-consumption")

    assert isinstance(loaded_pipeline, Pipeline)
    assert loaded_metadata.model_name == metadata.model_name
    assert loaded_metadata.mae == metadata.mae


def test_train_and_publish_calls_model_store(monkeypatch):
    df = MockTrainingDataReader().fetch_training_data()
    saved_metadata = None
    saved_pipeline = None

    class FakeStore:
        def save(self, pipeline, metadata):
            nonlocal saved_metadata, saved_pipeline
            saved_metadata = metadata
            saved_pipeline = pipeline
            return f"{metadata.model_name}/{metadata.trained_at}"

        def load_latest(self, model_name):
            raise NotImplementedError

    class FakeReader:
        def fetch_training_data(self):
            return df

    monkeypatch.setattr(
        "application.train_and_publish.utc_version_timestamp",
        lambda: "2026-09-16T14-30-00Z",
    )

    result = train_and_publish(
        data_reader=FakeReader(),
        model_store=FakeStore(),
        model_name="energy-consumption",
        test_size=0.25,
        random_state=42,
    )

    assert saved_metadata is not None
    assert saved_pipeline is result.training.pipeline
    assert result.object_prefix == "energy-consumption/2026-09-16T14-30-00Z"
    assert result.training.mae >= 0
    assert saved_metadata.features == ("site_id", "hour", "minute")

import json
from io import BytesIO
from unittest.mock import MagicMock

import joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from application.ports import SavedModelMetadata
from infrastructure.model_store import MinioModelStore


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

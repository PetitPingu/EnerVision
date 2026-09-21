import json
from io import BytesIO
from unittest.mock import MagicMock

import joblib
from minio.error import S3Error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from application.ports import SavedModelMetadata
from infrastructure.model_store import MinioModelStore


def _sample_metadata() -> SavedModelMetadata:
    return SavedModelMetadata(
        model_name="energy-consumption",
        trained_at="2026-09-16T14-30-00Z",
        metrics={"mae": 18.2, "rmse": 27.5},
        train_size=100,
        test_size=25,
        features=("site_id", "hour", "minute"),
    )


def test_minio_model_store_save_writes_version_and_promotes_to_latest():
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

    put_keys = [call.args[1] for call in client.put_object.call_args_list]
    assert put_keys == [
        "energy-consumption/2026-09-16T14-30-00Z/model.joblib",
        "energy-consumption/2026-09-16T14-30-00Z/metadata.json",
    ]

    # promote() copie cote serveur (pas de re-upload) vers latest/.
    copy_keys = [call.args[1] for call in client.copy_object.call_args_list]
    assert copy_keys == [
        "energy-consumption/latest/model.joblib",
        "energy-consumption/latest/metadata.json",
    ]


def test_register_writes_the_version_only_without_promoting():
    client = MagicMock()
    store = MinioModelStore(
        endpoint="localhost:9000",
        access_key="user",
        secret_key="pass",
        bucket="models",
        client=client,
    )
    pipeline = Pipeline(steps=[("identity", FunctionTransformer())])

    version = store.register(pipeline, _sample_metadata())

    assert version == "energy-consumption/2026-09-16T14-30-00Z"
    assert client.copy_object.call_count == 0


def test_get_current_metadata_returns_none_when_latest_does_not_exist():
    client = MagicMock()
    client.get_object.side_effect = S3Error(
        response=None,
        code="NoSuchKey",
        message="not found",
        resource="energy-consumption/latest/metadata.json",
        request_id="1",
        host_id="h",
    )
    store = MinioModelStore(
        endpoint="localhost:9000",
        access_key="user",
        secret_key="pass",
        bucket="models",
        client=client,
    )

    assert store.get_current_metadata("energy-consumption") is None


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

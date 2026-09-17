"""Tests de MlflowModelStore contre un vrai backend MLflow local (SQLite +
artefacts sur disque) - pas de mock : le Model Registry (aliases, versions)
n'est pas trivialement simulable, et un backend sqlite jetable par test est
aussi rapide qu'un mock tout en exerçant le vrai comportement MLflow. Le
store fichier ("file:") ne supporte pas le Registry, d'où sqlite plutôt
qu'un simple dossier local (voir docs/configuration.md).
"""

import mlflow
import pytest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from application.ports import SavedModelMetadata
from infrastructure.model_store import MlflowModelStore


def _sample_metadata(**overrides) -> SavedModelMetadata:
    data = {
        "model_name": "energy-consumption",
        "trained_at": "2026-09-16T14-30-00Z",
        "mae": 18.2,
        "rmse": 27.5,
        "train_size": 100,
        "test_size": 25,
        "features": ("site_id", "hour", "minute"),
    }
    data.update(overrides)
    return SavedModelMetadata(**data)


@pytest.fixture
def store(tmp_path):
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.create_experiment("test", artifact_location=str(tmp_path / "artifacts"))
    mlflow.set_experiment("test")
    return MlflowModelStore(tracking_uri=tracking_uri)


def _pipeline() -> Pipeline:
    return Pipeline(steps=[("identity", FunctionTransformer())])


def test_save_registers_the_model_and_returns_name_and_version(store):
    prefix = store.save(_pipeline(), _sample_metadata())

    assert prefix == "energy-consumption/1"


def test_save_then_load_latest_roundtrip(store):
    metadata = _sample_metadata()

    store.save(_pipeline(), metadata)
    loaded_pipeline, loaded_metadata = store.load_latest("energy-consumption")

    assert isinstance(loaded_pipeline, Pipeline)
    assert loaded_metadata == metadata


def test_load_latest_follows_the_alias_to_the_newest_version(store):
    store.save(_pipeline(), _sample_metadata(mae=20.0, trained_at="2026-09-15T10-00-00Z"))
    store.save(_pipeline(), _sample_metadata(mae=18.2, trained_at="2026-09-16T14-30-00Z"))

    _, loaded_metadata = store.load_latest("energy-consumption")

    assert loaded_metadata.mae == 18.2
    assert loaded_metadata.trained_at == "2026-09-16T14-30-00Z"


def test_get_current_metadata_returns_none_when_nothing_registered(store):
    assert store.get_current_metadata("energy-consumption") is None


def test_get_current_metadata_reflects_the_promoted_champion(store):
    store.save(_pipeline(), _sample_metadata(mae=20.0))

    metadata = store.get_current_metadata("energy-consumption")

    assert metadata.mae == 20.0


def test_register_does_not_move_the_alias(store):
    store.save(_pipeline(), _sample_metadata(mae=20.0, trained_at="2026-09-15T10-00-00Z"))

    store.register(_pipeline(), _sample_metadata(mae=18.2, trained_at="2026-09-16T14-30-00Z"))

    # Le challenger est enregistre (nouvelle version dans le Registry) mais
    # n'a pas ete promu : load_latest() suit toujours l'alias sur le champion.
    _, current = store.load_latest("energy-consumption")
    assert current.mae == 20.0


def test_promote_moves_the_alias_to_the_given_version(store):
    store.save(_pipeline(), _sample_metadata(mae=20.0, trained_at="2026-09-15T10-00-00Z"))
    challenger_version = store.register(
        _pipeline(), _sample_metadata(mae=18.2, trained_at="2026-09-16T14-30-00Z")
    )

    store.promote("energy-consumption", challenger_version)

    _, current = store.load_latest("energy-consumption")
    assert current.mae == 18.2


def test_models_are_versioned_independently_by_name(store):
    store.save(_pipeline(), _sample_metadata(model_name="site-a-model"))
    store.save(_pipeline(), _sample_metadata(model_name="site-b-model", mae=5.0))

    _, metadata_a = store.load_latest("site-a-model")
    _, metadata_b = store.load_latest("site-b-model")

    assert metadata_a.model_name == "site-a-model"
    assert metadata_b.model_name == "site-b-model"
    assert metadata_b.mae == 5.0

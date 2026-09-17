import pytest

from application.retrain_if_better import retrain_if_better
from infrastructure.training_data import MockTrainingDataReader


class FakeStore:
    """Double en mémoire : champion (promu) et versions enregistrées."""

    def __init__(self, champion=None):
        self._champion = champion
        self.registered = []
        self.promoted_versions = []

    def get_current_metadata(self, model_name):
        return self._champion

    def register(self, pipeline, metadata):
        self.registered.append(metadata)
        return f"{metadata.model_name}/{metadata.trained_at}"

    def promote(self, model_name, version):
        self.promoted_versions.append(version)
        self._champion = self.registered[-1]

    def save(self, pipeline, metadata):
        raise NotImplementedError

    def load_latest(self, model_name):
        raise NotImplementedError


class FakeReader:
    def __init__(self, df):
        self._df = df

    def fetch_training_data(self):
        return self._df


@pytest.fixture
def df():
    return MockTrainingDataReader().fetch_training_data()


def _patch_timestamp(monkeypatch, value="2026-09-17T10-00-00Z"):
    monkeypatch.setattr(
        "application.retrain_if_better.utc_version_timestamp",
        lambda: value,
    )


def test_first_training_is_always_promoted_even_without_champion(df, monkeypatch):
    _patch_timestamp(monkeypatch)
    store = FakeStore(champion=None)

    result = retrain_if_better(
        data_reader=FakeReader(df),
        model_store=store,
        model_name="energy-consumption",
    )

    assert result.promoted is True
    assert result.champion_mae is None
    assert len(store.registered) == 1
    assert len(store.promoted_versions) == 1


def test_worse_candidate_is_registered_but_not_promoted(df, monkeypatch):
    _patch_timestamp(monkeypatch)
    # MAE volontairement tres bas : sur MockTrainingDataReader avec les
    # parametres par defaut de retrain_if_better, le candidat obtient un MAE
    # ~32.66 (voir train_model), donc toujours pire que ce champion.
    champion = _champion_metadata(mae=1.0)
    store = FakeStore(champion=champion)

    result = retrain_if_better(
        data_reader=FakeReader(df),
        model_store=store,
        model_name="energy-consumption",
    )

    assert result.champion_mae == 1.0
    assert result.promoted is False
    assert len(store.registered) == 1  # toujours enregistre, pour l'historique
    assert store.promoted_versions == []


def test_better_candidate_is_promoted(df, monkeypatch):
    _patch_timestamp(monkeypatch)
    # MAE volontairement tres haut : le candidat entraine sur des vraies
    # donnees (meme mock) fera forcement mieux, evite de coupler le test a
    # la valeur exacte du MAE produit par train_model.
    champion = _champion_metadata(mae=10_000.0)
    store = FakeStore(champion=champion)

    result = retrain_if_better(
        data_reader=FakeReader(df),
        model_store=store,
        model_name="energy-consumption",
    )

    assert result.promoted is True
    assert store.promoted_versions == [f"energy-consumption/2026-09-17T10-00-00Z"]


def _champion_metadata(mae: float):
    from application.ports import SavedModelMetadata

    return SavedModelMetadata(
        model_name="energy-consumption",
        trained_at="2026-09-16T08-00-00Z",
        mae=mae,
        rmse=mae * 1.5,
        train_size=100,
        test_size=25,
        features=("site_id", "hour", "minute"),
    )

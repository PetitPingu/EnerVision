from application.state.train_and_publish_state import train_and_publish_state
from infrastructure.training_data import MockStateTrainingDataReader


def test_train_and_publish_state_calls_model_store(monkeypatch):
    df = MockStateTrainingDataReader().fetch_training_data()
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
        "application.state.train_and_publish_state.utc_version_timestamp",
        lambda: "2026-09-16T14-30-00Z",
    )

    result = train_and_publish_state(
        data_reader=FakeReader(),
        model_store=FakeStore(),
        model_name="sensor-state-model",
        test_size=0.25,
        random_state=42,
    )

    assert saved_metadata is not None
    assert saved_pipeline is result.training.pipeline
    assert result.object_prefix == "sensor-state-model/2026-09-16T14-30-00Z"
    assert 0.0 <= result.training.accuracy <= 1.0
    assert saved_metadata.metrics["accuracy"] == result.training.accuracy
    assert saved_metadata.features == ("site_id", "hour", "minute")

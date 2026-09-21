from infrastructure.ml.state.features import (
    SENSOR_COLUMNS,
    build_features,
    build_sensor_targets,
)
from infrastructure.ml.state.pipeline import create_model_pipeline
from infrastructure.training_data import MockStateTrainingDataReader


def _fitted_pipeline():
    df = MockStateTrainingDataReader().fetch_training_data()
    x, _ = build_features(df)
    sensors = build_sensor_targets(df)
    pipeline = create_model_pipeline()
    pipeline.fit(x, sensors.to_numpy())
    return pipeline, x, sensors


def test_create_model_pipeline_predicts_one_on_off_per_sensor():
    pipeline, x, _ = _fitted_pipeline()

    predictions = pipeline.predict(x)

    assert predictions.shape == (len(x), len(SENSOR_COLUMNS))
    assert set(predictions.ravel()) <= {0, 1}


def test_pipeline_learns_the_mock_sensor_pattern():
    pipeline, x, sensors = _fitted_pipeline()

    # Le mock lie l'heure a un motif de capteurs off : il doit etre retrouve.
    assert (pipeline.predict(x) == sensors.to_numpy()).mean() > 0.95


def test_mlflow_store_trusts_every_type_the_state_model_needs():
    from skops.io import dumps, get_untrusted_types

    pipeline, _, _ = _fitted_pipeline()

    # Meme liste que mlflow_store.register(), sinon le chargement du modele
    # echoue sur la VM.
    assert set(get_untrusted_types(data=dumps(pipeline))) <= {"sklearn.tree._tree.Tree"}

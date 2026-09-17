"""Script de vérification manuelle de l'infra MLflow (issue MLflow infra).

Logge un param, une métrique et un modèle factice sur le tracking server,
puis l'enregistre dans le Model Registry - preuve que le backend store
(Postgres) et l'artifact store (MinIO) fonctionnent de bout en bout, avant
qu'apps/prediction ne s'en serve pour de vrai.

Usage (depuis la racine du repo, avec mlflow/postgres/minio démarrés) :

    docker run --rm --network enervision_enervision-net \\
      -e MLFLOW_TRACKING_URI=http://mlflow:5000 \\
      -e MLFLOW_S3_ENDPOINT_URL=http://minio:9000 \\
      -e AWS_ACCESS_KEY_ID=<MINIO_ROOT_USER> \\
      -e AWS_SECRET_ACCESS_KEY=<MINIO_ROOT_PASSWORD> \\
      -e AWS_DEFAULT_REGION=us-east-1 \\
      -v "$(pwd)/mlflow:/verify" -w /verify python:3.12-slim \\
      sh -c "pip install -q 'mlflow==2.22.5' scikit-learn boto3 && python verify.py"

Version du client épinglée sur celle installée côté serveur (voir
mlflow/requirements.txt) : un client plus récent que le serveur peut
appeler des endpoints REST inexistants côté serveur (404).
"""

import os

import mlflow
import mlflow.sklearn
from sklearn.linear_model import LinearRegression

MODEL_NAME = "mlflow-infra-smoke-test"

mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
mlflow.set_experiment("mlflow-infra-verification")

model = LinearRegression().fit([[0], [1], [2]], [0, 2, 4])

with mlflow.start_run(run_name="infra_smoke_test") as run:
    mlflow.log_param("purpose", "verify_mlflow_infra")
    mlflow.log_metric("dummy_score", 1.0)
    mlflow.sklearn.log_model(model, artifact_path="model")

    print(f"Run loggé : {run.info.run_id}")

    version = mlflow.register_model(model_uri=f"runs:/{run.info.run_id}/model", name=MODEL_NAME)
    print(f"Modèle enregistré dans le Registry : {MODEL_NAME} v{version.version}")

print("OK - vérifiable dans l'UI MLflow (expérience 'mlflow-infra-verification' + onglet Models).")

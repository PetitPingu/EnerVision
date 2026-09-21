resource "docker_image" "mlflow" {
  name         = local.app_images.mlflow
  keep_locally = true
  depends_on   = [terraform_data.build_mlflow]
}

resource "docker_container" "mlflow" {
  name  = "mlflow"
  image = docker_image.mlflow.image_id

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "POSTGRES_USER=${var.db_user}",
    "POSTGRES_PASSWORD=${var.db_password}",
    "POSTGRES_DB=${var.db_name}",
    "MLFLOW_DB_SCHEMA=${var.mlflow_db_schema}",
    "MINIO_MODELS_BUCKET=${var.minio_models_bucket}",
    "MLFLOW_S3_ENDPOINT_URL=http://minio:9000",
    "AWS_ACCESS_KEY_ID=${var.minio_root_user}",
    "AWS_SECRET_ACCESS_KEY=${var.minio_root_password}",
    "AWS_DEFAULT_REGION=us-east-1",
  ]

  ports {
    internal = 5000
    external = var.mlflow_port
  }

  healthcheck {
    test         = ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval     = "5s"
    timeout      = "5s"
    retries      = 10
    start_period = "60s"
  }

  depends_on = [
    docker_container.database,
    docker_container.minio_init,
  ]
}

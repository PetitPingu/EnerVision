resource "docker_image" "core_api" {
  name         = local.app_images.core_api
  keep_locally = true
  depends_on   = [terraform_data.build_core_api]
}

resource "docker_image" "prediction" {
  name         = local.app_images.prediction
  keep_locally = true
  depends_on   = [terraform_data.build_prediction]
}

resource "docker_image" "recommendation" {
  name         = local.app_images.recommendation
  keep_locally = true
  depends_on   = [terraform_data.build_recommendation]
}

resource "docker_image" "etl_worker" {
  name         = local.app_images.etl_worker
  keep_locally = true
  depends_on   = [terraform_data.build_etl_worker]
}

resource "docker_container" "prediction" {
  name  = "prediction"
  image = docker_image.prediction.image_id

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "DATABASE_URL=${local.database_url}",
    "TRAINING_DATA_SOURCE=postgres",
    "MODEL_STORE=mlflow",
    "MODEL_NAME=${var.model_name}",
    "MINIO_ENDPOINT=minio:9000",
    "MINIO_ROOT_USER=${var.minio_root_user}",
    "MINIO_ROOT_PASSWORD=${var.minio_root_password}",
    "MINIO_MODELS_BUCKET=${var.minio_models_bucket}",
    "MLFLOW_TRACKING_URI=http://mlflow:5000",
    "MLFLOW_S3_ENDPOINT_URL=http://minio:9000",
    "AWS_ACCESS_KEY_ID=${var.minio_root_user}",
    "AWS_SECRET_ACCESS_KEY=${var.minio_root_password}",
    "AWS_DEFAULT_REGION=us-east-1",
    "AWS_CONFIG_FILE=/app/aws_config",
  ]

  ports {
    internal = 8000
    external = var.prediction_port
    ip       = "127.0.0.1"
  }

  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.http.routers.prediction.rule"
    value = "PathPrefix(`/prediction`)"
  }
  labels {
    label = "traefik.http.routers.prediction.entrypoints"
    value = "web"
  }
  labels {
    label = "traefik.http.routers.prediction.middlewares"
    value = "prediction-stripprefix"
  }
  labels {
    label = "traefik.http.middlewares.prediction-stripprefix.stripprefix.prefixes"
    value = "/prediction"
  }
  labels {
    label = "traefik.http.services.prediction.loadbalancer.server.port"
    value = "8000"
  }

  depends_on = [
    docker_container.database,
    docker_container.minio,
    docker_container.minio_init,
    docker_container.mlflow,
  ]
}

resource "docker_container" "recommendation" {
  name  = "recommendation"
  image = docker_image.recommendation.image_id

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "DATABASE_URL=${local.database_url}",
    "PREDICTION_URL=http://prediction:8000",
  ]

  ports {
    internal = 8000
    external = var.recommendation_port
    ip       = "127.0.0.1"
  }

  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.http.routers.recommendation.rule"
    value = "PathPrefix(`/recommendation`)"
  }
  labels {
    label = "traefik.http.routers.recommendation.entrypoints"
    value = "web"
  }
  labels {
    label = "traefik.http.routers.recommendation.middlewares"
    value = "recommendation-stripprefix"
  }
  labels {
    label = "traefik.http.middlewares.recommendation-stripprefix.stripprefix.prefixes"
    value = "/recommendation"
  }
  labels {
    label = "traefik.http.services.recommendation.loadbalancer.server.port"
    value = "8000"
  }

  depends_on = [
    docker_container.database,
    docker_container.prediction,
    terraform_data.db_migrate,
  ]
}

resource "docker_container" "core_api" {
  name  = "core_api"
  image = docker_image.core_api.image_id

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "DATABASE_URL=${local.database_url}",
    "PREDICTION_URL=http://prediction:8000",
    "RECOMMENDATION_URL=http://recommendation:8000",
    "CORS_ORIGINS=${var.cors_origins}",
    "ENERVISION_API_SCHEME=${var.enervision_api_scheme}",
    "ENERVISION_API_HOST=${var.enervision_api_host}",
    "ENERVISION_API_PORT=${var.enervision_api_port}",
    "ENERVISION_API_USERNAME=${var.enervision_api_username}",
    "ENERVISION_API_PASSWORD=${var.enervision_api_password}",
    "PROMETHEUS_URL=http://prometheus:9090",
    "REDIS_HOST=redis",
  ]

  ports {
    internal = 8000
    external = var.core_api_port
  }

  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.http.routers.core_api.rule"
    value = "PathPrefix(`/`)"
  }
  labels {
    label = "traefik.http.routers.core_api.entrypoints"
    value = "web"
  }
  labels {
    label = "traefik.http.services.core_api.loadbalancer.server.port"
    value = "8000"
  }

  depends_on = [
    docker_container.database,
    docker_container.prediction,
    docker_container.recommendation,
    docker_container.redis,
    terraform_data.db_migrate,
  ]
}

resource "docker_container" "etl_worker" {
  name  = "etl_worker"
  image = docker_image.etl_worker.image_id

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "DATABASE_URL=${local.database_url}",
    "ENERVISION_API_SCHEME=${var.enervision_api_scheme}",
    "ENERVISION_API_HOST=${var.enervision_api_host}",
    "ENERVISION_API_PORT=${var.enervision_api_port}",
    "ENERVISION_API_USERNAME=${var.enervision_api_username}",
    "ENERVISION_API_PASSWORD=${var.enervision_api_password}",
    "MINIO_ENDPOINT=minio:9000",
    "MINIO_ROOT_USER=${var.minio_root_user}",
    "MINIO_ROOT_PASSWORD=${var.minio_root_password}",
    "MINIO_RAW_BUCKET=${var.minio_raw_bucket}",
    "ETL_POLL_INTERVAL_SECONDS=${var.etl_poll_interval_seconds}",
    "REDIS_HOST=redis",
  ]

  depends_on = [
    docker_container.database,
    docker_container.minio,
    docker_container.minio_init,
    docker_container.redis,
  ]
}

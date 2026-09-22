output "network_name" {
  description = "Nom du réseau Docker interne"
  value       = docker_network.app_network.name
}

output "postgres_url" {
  description = "URL PostgreSQL/TimescaleDB (accès depuis l'hôte)"
  value       = "postgresql://${var.db_user}@${var.host}:${var.postgres_port}/${var.db_name}"
}

output "postgres_internal_host" {
  description = "Hôte PostgreSQL sur le réseau Docker"
  value       = docker_container.database.name
}

output "minio_api_url" {
  description = "URL API MinIO (accès depuis l'hôte)"
  value       = "http://${var.host}:${var.minio_port}"
}

output "minio_console_url" {
  description = "URL console MinIO (accès depuis l'hôte)"
  value       = "http://${var.host}:${var.minio_console_port}"
}

output "minio_internal_endpoint" {
  description = "Endpoint MinIO sur le réseau Docker"
  value       = "http://${docker_container.minio.name}:9000"
}

output "redis_url" {
  description = "URL Redis (accès depuis l'hôte)"
  value       = "redis://${var.host}:${var.redis_port}"
}

output "mlflow_url" {
  description = "URL du serveur MLflow"
  value       = "http://${var.host}:${var.mlflow_port}"
}

output "core_api_url" {
  description = "URL de l'API principale"
  value       = "http://${var.host}:${var.core_api_port}"
}

output "prediction_url" {
  description = "URL du service de prédiction (accès direct, lié à 127.0.0.1 : n'est atteignable que depuis la VM elle-même)"
  value       = "http://127.0.0.1:${var.prediction_port}"
}

output "recommendation_url" {
  description = "URL du service de recommandation (accès direct, lié à 127.0.0.1 : n'est atteignable que depuis la VM elle-même)"
  value       = "http://127.0.0.1:${var.recommendation_port}"
}

output "dashboard_url" {
  description = "URL du dashboard Next.js"
  value       = "http://${var.host}:${var.dashboard_port}"
}

output "dashboard_api_bff_url" {
  description = "URL core_api utilisée par le dashboard (injectée au build)"
  value       = local.dashboard_api_bff_url
}

output "traefik_url" {
  description = "URL de l'API via Traefik (entrypoint web, port 80)"
  value       = "http://${var.host}${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}"
}

output "traefik_dashboard_url" {
  description = "URL du dashboard Traefik (Host: traefik.localhost)"
  value       = "http://traefik.localhost:${var.traefik_dashboard_port}"
}

output "service_urls" {
  description = "Récapitulatif des URLs exposées sur l'hôte"
  value = {
    traefik_api            = "http://${var.host}${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}"
    traefik_dashboard      = "http://traefik.localhost:${var.traefik_dashboard_port}"
    dashboard              = "http://dashboard.localhost${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}"
    dashboard_direct       = "http://${var.host}:${var.dashboard_port}"
    core_api_traefik       = "http://${var.host}${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}/"
    core_api_direct        = "http://${var.host}:${var.core_api_port}"
    prediction_traefik     = "http://${var.host}${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}/prediction"
    prediction_direct      = "http://127.0.0.1:${var.prediction_port}"
    recommendation_traefik = "http://${var.host}${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}/recommendation"
    recommendation_direct  = "http://127.0.0.1:${var.recommendation_port}"
    mlflow                 = "http://${var.host}:${var.mlflow_port}"
    minio_api              = "http://${var.host}:${var.minio_port}"
    minio_console          = "http://${var.host}:${var.minio_console_port}"
    prometheus_traefik     = "http://prometheus.localhost${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}"
    prometheus_direct      = "http://127.0.0.1:${var.prometheus_port}"
    grafana                = "http://grafana.localhost${var.traefik_http_port == 80 ? "" : ":${var.traefik_http_port}"}"
    postgres               = "postgresql://${var.db_user}@${var.host}:${var.postgres_port}/${var.db_name}"
    redis                  = "redis://${var.host}:${var.redis_port}"
  }
}

output "internal_service_hosts" {
  description = "Noms DNS des services sur le réseau Docker (communication inter-conteneurs)"
  value = {
    postgres          = docker_container.database.name
    minio             = docker_container.minio.name
    redis             = docker_container.redis.name
    mlflow            = docker_container.mlflow.name
    core_api          = docker_container.core_api.name
    prediction        = docker_container.prediction.name
    recommendation    = docker_container.recommendation.name
    etl_worker        = docker_container.etl_worker.name
    dashboard         = docker_container.dashboard.name
    traefik           = docker_container.traefik.name
    postgres_exporter = docker_container.postgres_exporter.name
    redis_exporter    = docker_container.redis_exporter.name
    prometheus        = docker_container.prometheus.name
    grafana           = docker_container.grafana.name
  }
}

output "database_url" {
  description = "URL SQLAlchemy pour les apps Python (réseau Docker)"
  value       = local.database_url
  sensitive   = true
}

output "minio_buckets" {
  description = "Buckets MinIO provisionnés"
  value       = var.minio_buckets
}

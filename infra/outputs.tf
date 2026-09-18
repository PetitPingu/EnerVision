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
  description = "URL du service de prédiction (accès direct)"
  value       = "http://${var.host}:${var.prediction_port}"
}

output "recommendation_url" {
  description = "URL du service de recommandation (accès direct)"
  value       = "http://${var.host}:${var.recommendation_port}"
}

output "dashboard_url" {
  description = "URL du dashboard Next.js"
  value       = "http://${var.host}:${var.dashboard_port}"
}

output "dashboard_api_bff_url" {
  description = "URL core_api utilisée par le dashboard (injectée au build)"
  value       = local.dashboard_api_bff_url
}

output "service_urls" {
  description = "Récapitulatif des URLs exposées sur l'hôte"
  value = {
    dashboard      = "http://${var.host}:${var.dashboard_port}"
    core_api       = "http://${var.host}:${var.core_api_port}"
    prediction     = "http://${var.host}:${var.prediction_port}"
    recommendation = "http://${var.host}:${var.recommendation_port}"
    mlflow         = "http://${var.host}:${var.mlflow_port}"
    minio_api      = "http://${var.host}:${var.minio_port}"
    minio_console  = "http://${var.host}:${var.minio_console_port}"
    postgres       = "postgresql://${var.db_user}@${var.host}:${var.postgres_port}/${var.db_name}"
    redis          = "redis://${var.host}:${var.redis_port}"
  }
}

output "internal_service_hosts" {
  description = "Noms DNS des services sur le réseau Docker (communication inter-conteneurs)"
  value = {
    postgres       = docker_container.database.name
    minio          = docker_container.minio.name
    redis          = docker_container.redis.name
    mlflow         = docker_container.mlflow.name
    core_api       = docker_container.core_api.name
    prediction     = docker_container.prediction.name
    recommendation = docker_container.recommendation.name
    etl_worker     = docker_container.etl_worker.name
    dashboard      = docker_container.dashboard.name
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

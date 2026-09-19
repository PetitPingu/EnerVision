resource "docker_volume" "db_data" {
  name = "postgres_data"
}

resource "docker_volume" "minio_data" {
  name = "minio_data"
}

resource "docker_volume" "redis_data" {
  name = "redis_data"
}

resource "docker_volume" "prometheus_data" {
  name = "prometheus_data"
}

resource "docker_volume" "grafana_data" {
  name = "grafana_data"
}

resource "docker_volume" "minio_metrics_token" {
  name = "minio_metrics_token"
}

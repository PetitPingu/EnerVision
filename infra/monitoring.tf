locals {
  monitoring_root       = replace(abspath("${path.module}/../monitoring"), "\\", "/")
  minio_init_root       = replace(abspath("${path.module}/../minio/init"), "\\", "/")
  postgres_exporter_dsn = "postgresql://${var.db_user}:${urlencode(var.db_password)}@postgres:5432/${var.db_name}?sslmode=disable"
}

resource "docker_image" "postgres_exporter" {
  name         = "prometheuscommunity/postgres-exporter:v0.15.0"
  keep_locally = true
}

resource "docker_image" "redis_exporter" {
  name         = "oliver006/redis_exporter:v1.62.0"
  keep_locally = true
}

resource "docker_image" "prometheus" {
  name         = "prom/prometheus:v3.1.0"
  keep_locally = true
}

resource "docker_image" "grafana" {
  name         = "grafana/grafana:11.4.0"
  keep_locally = true
}

resource "docker_container" "postgres_exporter" {
  name  = "postgres-exporter"
  image = docker_image.postgres_exporter.image_id

  depends_on = [docker_container.database]

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "DATA_SOURCE_NAME=${local.postgres_exporter_dsn}",
  ]
}

resource "docker_container" "redis_exporter" {
  name  = "redis-exporter"
  image = docker_image.redis_exporter.image_id

  depends_on = [docker_container.redis]

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "REDIS_ADDR=redis://redis:6379",
  ]
}

resource "docker_container" "minio_metrics_token" {
  name       = "minio-metrics-token"
  image      = docker_image.minio_mc.image_id
  must_run   = false
  restart    = "no"
  rm         = false
  entrypoint = ["/bin/bash", "-c"]
  command = [
    <<-EOT
    until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null; do
      echo "Waiting for MinIO..."
      sleep 2
    done
    exec /init/generate-prometheus-token.sh
    EOT
  ]

  depends_on = [docker_container.minio]

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "MINIO_ROOT_USER=${var.minio_root_user}",
    "MINIO_ROOT_PASSWORD=${var.minio_root_password}",
  ]

  mounts {
    type      = "bind"
    source    = local.minio_init_root
    target    = "/init"
    read_only = true
  }

  volumes {
    volume_name    = docker_volume.minio_metrics_token.name
    container_path = "/secrets"
  }
}

resource "docker_container" "prometheus" {
  name  = "prometheus"
  image = docker_image.prometheus.image_id

  depends_on = [
    docker_container.traefik,
    docker_container.postgres_exporter,
    docker_container.redis_exporter,
    docker_container.minio_metrics_token,
    docker_container.etl_worker,
  ]

  networks_advanced {
    name = docker_network.app_network.name
  }

  ports {
    internal = 9090
    external = var.prometheus_port
    ip       = "127.0.0.1"
  }

  mounts {
    type      = "bind"
    source    = "${local.monitoring_root}/prometheus/prometheus.yml"
    target    = "/etc/prometheus/prometheus.yml"
    read_only = true
  }

  volumes {
    volume_name    = docker_volume.prometheus_data.name
    container_path = "/prometheus"
  }

  volumes {
    volume_name    = docker_volume.minio_metrics_token.name
    container_path = "/etc/prometheus/secrets"
    read_only      = true
  }

  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.http.routers.prometheus.rule"
    value = "Host(`prometheus.localhost`)"
  }
  labels {
    label = "traefik.http.routers.prometheus.entrypoints"
    value = "web"
  }
  labels {
    label = "traefik.http.services.prometheus.loadbalancer.server.port"
    value = "9090"
  }
}

resource "docker_container" "grafana" {
  name  = "grafana"
  image = docker_image.grafana.image_id

  depends_on = [docker_container.prometheus]

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "GF_SECURITY_ADMIN_USER=${var.grafana_admin_user}",
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_admin_password}",
  ]

  mounts {
    type      = "bind"
    source    = "${local.monitoring_root}/grafana/provisioning"
    target    = "/etc/grafana/provisioning"
    read_only = true
  }

  mounts {
    type      = "bind"
    source    = "${local.monitoring_root}/grafana/dashboards"
    target    = "/var/lib/grafana/dashboards"
    read_only = true
  }

  volumes {
    volume_name    = docker_volume.grafana_data.name
    container_path = "/var/lib/grafana"
  }

  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.http.routers.grafana.rule"
    value = "Host(`grafana.localhost`)"
  }
  labels {
    label = "traefik.http.routers.grafana.entrypoints"
    value = "web"
  }
  labels {
    label = "traefik.http.services.grafana.loadbalancer.server.port"
    value = "3000"
  }
}

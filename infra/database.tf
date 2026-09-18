resource "docker_image" "postgres" {
  name         = "timescale/timescaledb:2.15.3-pg16"
  keep_locally = true
}

resource "docker_container" "database" {
  name  = "postgres"
  image = docker_image.postgres.image_id

  networks_advanced {
    name = docker_network.app_network.name
  }

  volumes {
    volume_name    = docker_volume.db_data.name
    container_path = "/var/lib/postgresql/data"
  }

  env = [
    "POSTGRES_DB=${var.db_name}",
    "POSTGRES_USER=${var.db_user}",
    "POSTGRES_PASSWORD=${var.db_password}",
  ]

  ports {
    internal = 5432
    external = var.postgres_port
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ${var.db_user} -d ${var.db_name}"]
    interval = "5s"
    timeout  = "5s"
    retries  = 5
  }
}

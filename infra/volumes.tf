resource "docker_volume" "db_data" {
  name = "postgres_data"
}

resource "docker_volume" "minio_data" {
  name = "minio_data"
}

resource "docker_volume" "redis_data" {
  name = "redis_data"
}

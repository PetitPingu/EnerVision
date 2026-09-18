resource "docker_image" "minio_mc" {
  name         = "quay.io/minio/mc:latest"
  keep_locally = true
}

resource "docker_container" "minio_init" {
  name       = "minio-init"
  image      = docker_image.minio_mc.image_id
  must_run   = false
  restart    = "no"
  rm         = true
  entrypoint = ["/bin/sh", "-c"]
  command = [
    <<-EOT
    until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null; do
      echo "Waiting for MinIO..."
      sleep 2
    done
    exec /init/create-buckets.sh
    EOT
  ]

  depends_on = [docker_container.minio]

  networks_advanced {
    name = docker_network.app_network.name
  }

  env = [
    "MINIO_ROOT_USER=${var.minio_root_user}",
    "MINIO_ROOT_PASSWORD=${var.minio_root_password}",
    "MINIO_BUCKETS=${var.minio_buckets}",
  ]

  mounts {
    type      = "bind"
    source    = replace(abspath("${path.module}/../minio/init"), "\\", "/")
    target    = "/init"
    read_only = true
  }
}

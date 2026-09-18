resource "docker_image" "traefik" {
  name         = "traefik:v3.7"
  keep_locally = true
}

resource "docker_container" "traefik" {
  name  = "traefik"
  image = docker_image.traefik.image_id
  command = [
    "--providers.docker=true",
    "--providers.docker.exposedbydefault=false",
    "--entrypoints.web.address=:80",
    "--entrypoints.traefik.address=:8080",
    "--api.dashboard=true",
    "--metrics.prometheus=true",
  ]

  networks_advanced {
    name = docker_network.app_network.name
  }

  ports {
    internal = 80
    external = var.traefik_http_port
  }

  ports {
    internal = 8080
    external = var.traefik_dashboard_port
  }

  mounts {
    type      = "bind"
    source    = var.docker_socket_path
    target    = "/var/run/docker.sock"
    read_only = true
  }

  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.http.routers.traefik-dashboard.rule"
    value = "Host(`traefik.localhost`)"
  }
  labels {
    label = "traefik.http.routers.traefik-dashboard.entrypoints"
    value = "traefik"
  }
  labels {
    label = "traefik.http.routers.traefik-dashboard.service"
    value = "api@internal"
  }
  labels {
    label = "traefik.http.routers.traefik-dashboard.middlewares"
    value = "traefik-auth"
  }
  labels {
    label = "traefik.http.middlewares.traefik-auth.basicauth.users"
    value = var.traefik_dashboard_basic_auth_users
  }
}

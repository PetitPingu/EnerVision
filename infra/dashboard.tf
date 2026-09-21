resource "docker_image" "dashboard" {
  name         = "enervision/dashboard:latest"
  keep_locally = true
  depends_on   = [terraform_data.build_dashboard]
}

resource "docker_container" "dashboard" {
  name  = "dashboard"
  image = docker_image.dashboard.image_id

  networks_advanced {
    name = docker_network.app_network.name
  }

  ports {
    internal = 3000
    external = var.dashboard_port
  }

  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.http.routers.dashboard.rule"
    value = "Host(`dashboard.localhost`)"
  }
  labels {
    label = "traefik.http.routers.dashboard.entrypoints"
    value = "web"
  }
  labels {
    label = "traefik.http.services.dashboard.loadbalancer.server.port"
    value = "3000"
  }

  depends_on = [docker_container.core_api]
}

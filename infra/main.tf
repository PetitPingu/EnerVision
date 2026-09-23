terraform {
  required_version = ">= 1.5.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      # >= 3.6.2 requis pour Docker Engine 29+ (API min 1.44)
      version = "~> 3.6.0"
    }
  }
}

provider "docker" {
  host = local.docker_host_effective

  dynamic "registry_auth" {
    for_each = var.ghcr_read_token != "" ? [1] : []
    content {
      address  = "ghcr.io"
      username = var.ghcr_username
      password = var.ghcr_read_token
    }
  }
}

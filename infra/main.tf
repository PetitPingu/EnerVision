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
  # host = "ssh://${var.ssh_user}@${var.vm_host}:${var.ssh_port}"
  host = var.docker_host
}

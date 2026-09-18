terraform {
  required_version = ">= 1.5.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

provider "docker" {
  # host = "ssh://${var.ssh_user}@${var.vm_host}:${var.ssh_port}"
  host = var.docker_host
}

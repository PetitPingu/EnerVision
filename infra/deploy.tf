locals {
  docker_host_effective = var.vm_host != "" ? "ssh://${var.ssh_user}@${var.vm_host}:${var.ssh_port}" : var.docker_host
}

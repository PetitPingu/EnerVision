locals {
  app_images = {
    core_api       = var.build_images_locally ? "enervision/core_api:latest" : "${var.image_registry_prefix}/core_api:${var.image_tag}"
    prediction     = var.build_images_locally ? "enervision/prediction:latest" : "${var.image_registry_prefix}/prediction:${var.image_tag}"
    recommendation = var.build_images_locally ? "enervision/recommendation:latest" : "${var.image_registry_prefix}/recommendation:${var.image_tag}"
    etl_worker     = var.build_images_locally ? "enervision/etl_worker:latest" : "${var.image_registry_prefix}/etl_worker:${var.image_tag}"
    dashboard      = var.build_images_locally ? "enervision/dashboard:latest" : "${var.image_registry_prefix}/dashboard:${var.image_tag}"
    mlflow         = var.build_images_locally ? "enervision/mlflow:latest" : "${var.image_registry_prefix}/mlflow:${var.image_tag}"
  }
}

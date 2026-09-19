# Le provider kreuzwerker/docker échoue sur Windows avec
# "archive/tar: invalid tar header" lors du build via le bloc build {}.
# On délègue le build à la CLI Docker, puis on référence l'image par tag.

locals {
  repo_root_path        = abspath("${path.module}/..")
  database_url          = "postgresql+psycopg://${var.db_user}:${var.db_password}@postgres:5432/${var.db_name}"
  dashboard_api_bff_url = coalesce(var.dashboard_api_bff_url, "http://${var.host}:${var.core_api_port}")
}

resource "terraform_data" "build_mlflow" {
  input = join(",", [
    filemd5("${path.module}/../mlflow/Dockerfile"),
    filemd5("${path.module}/../mlflow/entrypoint.sh"),
    filemd5("${path.module}/../mlflow/requirements.txt"),
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/mlflow:latest -f mlflow/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_core_api" {
  input = join(",", [
    filemd5("${path.module}/../apps/core_api/Dockerfile"),
    filemd5("${path.module}/../apps/core_api/requirements.txt"),
    filemd5("${path.module}/../packages/db-schema/wait-for-postgres.sh"),
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/core_api:latest -f apps/core_api/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_prediction" {
  input = join(",", [
    filemd5("${path.module}/../apps/prediction/Dockerfile"),
    filemd5("${path.module}/../apps/prediction/requirements.txt"),
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/prediction:latest -f apps/prediction/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_recommendation" {
  input = join(",", [
    filemd5("${path.module}/../apps/recommendation/Dockerfile"),
    filemd5("${path.module}/../apps/recommendation/requirements.txt"),
    filemd5("${path.module}/../packages/db-schema/wait-for-postgres.sh"),
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/recommendation:latest -f apps/recommendation/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_etl_worker" {
  input = join(",", [
    filemd5("${path.module}/../apps/etl_worker/Dockerfile"),
    filemd5("${path.module}/../apps/etl_worker/requirements.txt"),
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/etl_worker:latest -f apps/etl_worker/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_dashboard" {
  input = join(",", [
    filemd5("${path.module}/../apps/dashboard/Dockerfile"),
    filemd5("${path.module}/../apps/dashboard/package-lock.json"),
    local.dashboard_api_bff_url,
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/dashboard:latest -f apps/dashboard/Dockerfile --build-arg NEXT_PUBLIC_API_BFF_URL=${local.dashboard_api_bff_url} ."
    working_dir = local.repo_root_path
  }
}

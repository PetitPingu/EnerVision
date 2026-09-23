# Le provider kreuzwerker/docker échoue sur Windows avec
# "archive/tar: invalid tar header" lors du build via le bloc build {}.
# On délègue le build à la CLI Docker, puis on référence l'image par tag.

locals {
  repo_root_path        = abspath("${path.module}/..")
  database_url          = "postgresql+psycopg://${var.db_user}:${var.db_password}@postgres:5432/${var.db_name}"
  dashboard_api_bff_url = coalesce(var.dashboard_api_bff_url, "http://${var.host}:${var.core_api_port}")

  # filemd5/requirements.txt seuls ne suffisent pas à détecter un changement
  # de code applicatif (cf. incident : etl_worker resté sur une image d'avant
  # le job de monitoring, requirements.txt inchangé -> jamais rebuild par
  # Terraform malgré plusieurs `terraform apply` après le merge). On hashe
  # tout l'arbre source de chaque service (et packages/db-schema, dont
  # dépendent core_api/prediction/recommendation/etl_worker) pour que tout
  # changement de code déclenche bien un rebuild.
  db_schema_source_hash = sha1(join("", [
    for f in sort(fileset(local.repo_root_path, "packages/db-schema/**")) : filemd5("${local.repo_root_path}/${f}")
  ]))
  core_api_source_hash = sha1(join("", [
    for f in sort(fileset(local.repo_root_path, "apps/core_api/**")) : filemd5("${local.repo_root_path}/${f}")
  ]))
  prediction_source_hash = sha1(join("", [
    for f in sort(fileset(local.repo_root_path, "apps/prediction/**")) : filemd5("${local.repo_root_path}/${f}")
  ]))
  recommendation_source_hash = sha1(join("", [
    for f in sort(fileset(local.repo_root_path, "apps/recommendation/**")) : filemd5("${local.repo_root_path}/${f}")
  ]))
  etl_worker_source_hash = sha1(join("", [
    for f in sort(fileset(local.repo_root_path, "apps/etl_worker/**")) : filemd5("${local.repo_root_path}/${f}")
  ]))
  dashboard_source_hash = sha1(join("", [
    for f in sort(fileset(local.repo_root_path, "apps/dashboard/src/**")) : filemd5("${local.repo_root_path}/${f}")
  ]))
}

resource "terraform_data" "build_mlflow" {
  count = var.build_images_locally ? 1 : 0

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
  count = var.build_images_locally ? 1 : 0

  input = join(",", [
    filemd5("${path.module}/../apps/core_api/Dockerfile"),
    local.core_api_source_hash,
    local.db_schema_source_hash,
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/core_api:latest -f apps/core_api/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_prediction" {
  count = var.build_images_locally ? 1 : 0

  input = join(",", [
    filemd5("${path.module}/../apps/prediction/Dockerfile"),
    local.prediction_source_hash,
    local.db_schema_source_hash,
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/prediction:latest -f apps/prediction/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_recommendation" {
  count = var.build_images_locally ? 1 : 0

  input = join(",", [
    filemd5("${path.module}/../apps/recommendation/Dockerfile"),
    local.recommendation_source_hash,
    local.db_schema_source_hash,
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/recommendation:latest -f apps/recommendation/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_etl_worker" {
  count = var.build_images_locally ? 1 : 0

  input = join(",", [
    filemd5("${path.module}/../apps/etl_worker/Dockerfile"),
    local.etl_worker_source_hash,
    local.db_schema_source_hash,
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/etl_worker:latest -f apps/etl_worker/Dockerfile ."
    working_dir = local.repo_root_path
  }
}

resource "terraform_data" "build_dashboard" {
  count = var.build_images_locally ? 1 : 0

  input = join(",", [
    filemd5("${path.module}/../apps/dashboard/Dockerfile"),
    filemd5("${path.module}/../apps/dashboard/package-lock.json"),
    local.dashboard_source_hash,
    local.dashboard_api_bff_url,
  ])

  provisioner "local-exec" {
    command     = "docker build -t enervision/dashboard:latest -f apps/dashboard/Dockerfile --build-arg NEXT_PUBLIC_API_BFF_URL=${local.dashboard_api_bff_url} ."
    working_dir = local.repo_root_path
  }
}

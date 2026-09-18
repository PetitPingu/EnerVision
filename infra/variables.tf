variable "docker_host" {
  type        = string
  default     = "npipe:////./pipe/dockerDesktopLinuxEngine"
  description = "URI du démon Docker (local ou SSH)"
}

variable "host" {
  type        = string
  default     = "localhost"
  description = "Hôte utilisé dans les URLs affichées par les outputs (accès depuis la machine locale)"
}

variable "db_name" {
  type        = string
  default     = "postgres"
  description = "Nom de la base de données"
}

variable "db_user" {
  type        = string
  default     = "postgres"
  description = "Nom d'utilisateur de la base de données"
}

variable "db_password" {
  type        = string
  default     = "postgres"
  sensitive   = true
  description = "Mot de passe de la base de données"
}

variable "postgres_port" {
  type        = number
  default     = 5432
  description = "Port exposé pour TimescaleDB"
}

variable "minio_root_user" {
  type        = string
  default     = "minioadmin"
  description = "Identifiant root MinIO"
}

variable "minio_root_password" {
  type        = string
  default     = "minioadmin"
  sensitive   = true
  description = "Mot de passe root MinIO"
}

variable "minio_port" {
  type        = number
  default     = 9000
  description = "Port API MinIO"
}

variable "minio_console_port" {
  type        = number
  default     = 9001
  description = "Port console MinIO"
}

variable "minio_buckets" {
  type        = string
  default     = "raw,models"
  description = "Buckets MinIO à créer (séparés par des virgules)"
}

variable "redis_port" {
  type        = number
  default     = 6379
  description = "Port exposé pour Redis"
}

variable "mlflow_port" {
  type        = number
  default     = 5000
  description = "Port exposé pour MLflow"
}

variable "mlflow_db_schema" {
  type        = string
  default     = "mlflow"
  description = "Schéma PostgreSQL dédié à MLflow"
}

variable "minio_models_bucket" {
  type        = string
  default     = "models"
  description = "Bucket MinIO pour les modèles ML"
}

variable "minio_raw_bucket" {
  type        = string
  default     = "raw"
  description = "Bucket MinIO pour les données brutes ETL"
}

variable "model_name" {
  type        = string
  default     = "energy-consumption"
  description = "Nom du modèle ML enregistré"
}

variable "etl_poll_interval_seconds" {
  type        = number
  default     = 60
  description = "Intervalle de polling du worker ETL (secondes)"
}

variable "core_api_port" {
  type        = number
  default     = 8000
  description = "Port exposé pour core_api (accès direct sans Traefik)"
}

variable "prediction_port" {
  type        = number
  default     = 8001
  description = "Port exposé pour prediction (accès direct sans Traefik)"
}

variable "recommendation_port" {
  type        = number
  default     = 8002
  description = "Port exposé pour recommendation (accès direct sans Traefik)"
}

variable "dashboard_port" {
  type        = number
  default     = 3000
  description = "Port exposé pour le dashboard Next.js"
}

variable "dashboard_api_bff_url" {
  type        = string
  default     = null
  description = "URL de core_api injectée au build Next.js (NEXT_PUBLIC_API_BFF_URL). Par défaut : http://{host}:{core_api_port}"
}

variable "enervision_api_scheme" {
  type        = string
  default     = "http"
  description = "Schéma de l'API mock EnerVision"
}

variable "enervision_api_host" {
  type        = string
  default     = "localhost"
  description = "Hôte de l'API mock EnerVision"
}

variable "enervision_api_port" {
  type        = string
  default     = "8000"
  description = "Port de l'API mock EnerVision"
}

variable "enervision_api_username" {
  type        = string
  default     = ""
  description = "Identifiant API mock EnerVision"
}

variable "enervision_api_password" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Mot de passe API mock EnerVision"
}

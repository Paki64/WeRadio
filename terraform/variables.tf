# Variables

# NAMESPACES
variable "namespace" {
  description = "The name of the Kubernetes namespace"
  type        = string
  default     = "weradio"
}



# GENERAL
variable "timezone" {
  description = "Timezone for services"
  type        = string
  default     = "Europe/Rome"
}



# BACKEND
variable "backend_config" {
  description = "Backend service configuration name"
  type = string
  default = "backend-config"
}
variable "backend_image" {
  description = "The Docker image for the backend service"
  type        = string
  default     = "paki13/weradio-backend:latest"
}
variable "backend_object_storage" {
  description = "Object storage type for backend (e.g., minio)"
  type        = string
  default     = "true" 
}
variable "backend_secret" {
  description = "Backend secrets name"
  type        = string
  default     = "backend-secret"
}
variable "backend_secret_type" {
  description = "Backend secret type"
  type        = string
  default     = "Opaque"
}
variable "backend_network_type" {
  description = "Backend network type"
  type        = string
  default     = "ClusterIP"
}

# Streamer node
variable "backend_streamer_name" {
  description = "Backend streamer name"
  type        = string
  default     = "backend-streamer"
}
variable "backend_streamer_port" {
  description = "Backend streamer port"
  type        = string
  default     = "5000"
}

# API node
variable "backend_api_name" {
  description = "Backend API name"
  type        = string
  default     = "backend-api"
}
variable "backend_api_port" {
  description = "Backend API port"
  type        = string
  default     = "5001"
}



# FRONTEND
variable "frontend_config" {
  description = "Frontend service configuration name"
  type = string
  default = "frontend-config" 
}
variable "frontend_name" {
  description = "Frontend service name"
  type        = string
  default     = "frontend"
}
variable "frontend_image" {
  description = "Frontend Docker image"
  type        = string
  default     = "paki13/weradio-frontend:latest"
}
variable "frontend_port" {
  description = "Frontend port"
  type        = string
  default     = "3000"
}
variable "api_url" {
  description = "API URL for frontend"
  type        = string
  default     = "http://backend-api:5001"
}
variable "frontend_network_type" {
  description = "Frontend network type"
  type        = string
  default     = "ClusterIP"
  # LoadBalancer suggested for cloud deployments
  # NodePort suggested for local deployments (e.g., minikube, kind)
  # ClusterIP suggested for use with an Ingress controller
}



# POSTGRES
variable "postgres_config" {
  description = "PostgreSQL configuration name"
  type = string
  default = "postgres-config"
}
variable "postgres_name" {
  description = "PostgreSQL service name"
  type        = string
  default     = "postgres"
  
}
variable "postgres_image" {
  description = "PostgreSQL Docker image"
  type        = string
  default     = "postgres:17-alpine"
}
variable "postgres_storage" {
  description = "PostgreSQL storage size"
  type        = string
  default     = "10Gi"
}
variable "postgres_storage_name" {
  description = "PostgreSQL storage name"
  type        = string
  default     = "postgres-storage"
}
variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "weradio"
}
variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "weradio_user"
}
variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}
variable "postgres_host" {
  description = "PostgreSQL host"
  type        = string
  default     = "postgres"
}
variable "postgres_port" {
  description = "PostgreSQL port"
  type        = string
  default     = "5432"
}
variable "postgres_lang" {
  description = "PostgreSQL LANG"
  type        = string
  default     = "en_US.UTF-8"
}
variable "postgres_lc_all" {
  description = "PostgreSQL LC_ALL"
  type        = string
  default     = "en_US.UTF-8"
}
variable "postgres_secret" {
  description = "PostgreSQL secret name"
  type        = string
  default     = "postgres-secret"
}
variable "postgres_secret_type" {
  description = "PostgreSQL secret type"
  type        = string
  default     = "Opaque"
}
variable "postgres_network_type" {
  description = "PostgreSQL network type"
  type        = string
  default     = "ClusterIP"
}



# REDIS
variable "redis_config" {
  description = "Redis configuration name"
  type = string
  default = "redis-config"
}
variable "redis_name" {
  description = "Redis service name"
  type        = string
  default     = "redis"
}
variable "redis_image" {
  description = "Redis Docker image"
  type        = string
  default     = "redis:7-alpine"
}
variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}
variable "redis_host" {
  description = "Redis host"
  type        = string
  default     = "redis"
}
variable "redis_port" {
  description = "Redis port"
  type        = string
  default     = "6379"
}
variable "redis_secret" {
  description = "Redis secret name"
  type        = string
  default     = "redis-secret"
}
variable "redis_secret_type" {
  description = "Redis secret type"
  type        = string
  default     = "Opaque"
}
variable "redis_network_type" {
  description = "Redis network type"
  type        = string
  default     = "ClusterIP"
}
variable "redis_storage" {
  description = "Redis storage size"
  type        = string
  default     = "5Gi"
}
variable "redis_storage_name" {
  description = "Redis storage name"
  type        = string
  default     = "redis-storage"
}


# MINIO
variable "minio_config" {
  description = "MinIO configuration name"
  type = string
  default = "minio-config"
}
variable "minio_name" {
  description = "MinIO service name"
  type        = string
  default     = "minio"
}
variable "minio_image" {
  description = "MinIO Docker image"
  type        = string
  default     = "minio/minio:latest"
}
variable "minio_secret" {
  description = "MinIO secret name"
  type        = string
  default     = "minio-secret"
}
variable "minio_secret_type" {
  description = "MinIO secret type"
  type        = string
  default     = "Opaque"
}
variable "minio_root_user" {
  description = "MinIO root user"
  type        = string
  default     = "admin"
}
variable "minio_root_password" {
  description = "MinIO root password"
  type        = string
  sensitive   = true
}
variable "minio_endpoint" {
  description = "MinIO endpoint"
  type        = string
  default     = "minio:9000"
}
variable "minio_access_key" {
  description = "MinIO access key"
  type        = string
  default     = "admin"
}
variable "minio_secret_key" {
  description = "MinIO secret key"
  type        = string
  sensitive   = true
}
variable "minio_storage" {
  description = "MinIO storage size"
  type        = string
  default     = "10Gi"
}
variable "minio_storage_name" {
  description = "MinIO storage name"
  type        = string
  default     = "minio-storage"
}
variable "minio_api_port" {
  description = "MinIO API port"
  type        = string
  default     = "9000"
}
variable "minio_console_port" {
  description = "MinIO console port"
  type        = string
  default     = "9001"
}
variable "minio_network_type" {
  description = "MinIO network type"
  type        = string
  default     = "ClusterIP"
}
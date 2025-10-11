# Backend Services

# ConfigMap
resource "kubernetes_config_map" "backend_config" {
  metadata {
    name      = var.backend_config
    namespace = var.namespace
  }
  data = {
    STREAMER_PORT    = var.backend_streamer_port
    API_PORT         = var.backend_api_port
    OBJECT_STORAGE   = var.backend_object_storage
    POSTGRES_HOST    = var.postgres_host
    POSTGRES_PORT    = var.postgres_port
    POSTGRES_DB      = var.postgres_db
    REDIS_HOST       = var.redis_host
    REDIS_PORT       = var.redis_port
    MINIO_ENDPOINT   = var.minio_endpoint
    MINIO_ACCESS_KEY = var.minio_access_key
  }
}

resource "kubernetes_secret" "backend_secret" {
  metadata {
    name      = var.backend_secret
    namespace = var.namespace
  }
  data = {
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
    REDIS_PASSWORD    = var.redis_password
    MINIO_SECRET_KEY  = var.minio_secret_key
  }
  type = var.backend_secret_type
}

resource "kubernetes_persistent_volume_claim" "backend_pvc" {
  metadata {
    name      = var.backend_storage_name
    namespace = var.namespace
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = var.backend_storage
      }
    }
  }
}



# Backend Streamer
resource "kubernetes_deployment" "backend_streamer" {

  metadata {
    name      = var.backend_streamer_name
    namespace = var.namespace
  }

  spec {

    replicas = 1

    selector {
      match_labels = {
        app = var.backend_streamer_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.backend_streamer_name
        }
      }

      spec {

        container {
          name  = var.backend_streamer_name
          image = var.backend_image
          env {
            name  = "STREAMER"
            value = "true"
          }

          env {
            name  = "WERADIO_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "STREAMER_PORT"
              }
            }
          }

          env {
            name  = "OBJECT_STORAGE"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "OBJECT_STORAGE"
              }
            }
          }

          env {
            name = "POSTGRES_HOST"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "POSTGRES_HOST"
              }
            }
          }

          env {
            name = "POSTGRES_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "POSTGRES_PORT"
              }
            }
          }

          env {
            name = "POSTGRES_DB"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "POSTGRES_DB"
              }
            }
          }

          env {
            name = "POSTGRES_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "POSTGRES_USER"
              }
            }
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "POSTGRES_PASSWORD"
              }
            }
          }

          env {
            name = "REDIS_HOST"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "REDIS_HOST"
              }
            }
          }

          env {
            name = "REDIS_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "REDIS_PORT"
              }
            }
          }

          env {
            name = "REDIS_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "REDIS_PASSWORD"
              }
            }
          }

          env {
            name = "MINIO_ENDPOINT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "MINIO_ENDPOINT"
              }
            }
          }

          env {
            name = "MINIO_ACCESS_KEY"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "MINIO_ACCESS_KEY"
              }
            }
          }

          env {
            name = "MINIO_SECRET_KEY"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "MINIO_SECRET_KEY"
              }
            }
          }

          port {
            container_port = var.backend_streamer_port
          }

          volume_mount {
            name       = var.backend_storage_name
            mount_path = "/app/data"
          }

        }

        volume {
          name = var.backend_storage_name
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.backend_pvc.metadata[0].name
          }
        }
      
      }
    }
  }

  depends_on = [
    kubernetes_deployment.postgres,
    kubernetes_deployment.redis,
    kubernetes_deployment.minio
  ]
}


resource "kubernetes_service" "backend_streamer" {
  metadata {
    name      = var.backend_streamer_name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = var.backend_streamer_name
    }

    port {
      port        = var.backend_streamer_port
      target_port = var.backend_streamer_port
    }

    type = var.backend_network_type
  }
}



# Backend API
resource "kubernetes_deployment" "backend_api" {
  metadata {
    name      = var.backend_api_name
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = var.backend_api_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.backend_api_name
        }
      }

      spec {
        container {
          name  = var.backend_api_name
          image = var.backend_image

          env {
            name  = "STREAMER"
            value = "false"
          }

          env {
            name  = "WERADIO_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "API_PORT"
              }
            }
          }

          env {
            name  = "OBJECT_STORAGE"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "OBJECT_STORAGE"
              }
            }
          }

          env {
            name = "POSTGRES_HOST"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "POSTGRES_HOST"
              }
            }
          }

          env {
            name = "POSTGRES_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "POSTGRES_PORT"
              }
            }
          }

          env {
            name = "POSTGRES_DB"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "POSTGRES_DB"
              }
            }
          }

          env {
            name = "POSTGRES_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "POSTGRES_USER"
              }
            }
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "POSTGRES_PASSWORD"
              }
            }
          }

          env {
            name = "REDIS_HOST"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "REDIS_HOST"
              }
            }
          }

          env {
            name = "REDIS_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "REDIS_PORT"
              }
            }
          }

          env {
            name = "REDIS_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "REDIS_PASSWORD"
              }
            }
          }

          env {
            name = "MINIO_ENDPOINT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "MINIO_ENDPOINT"
              }
            }
          }

          env {
            name = "MINIO_ACCESS_KEY"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.backend_config.metadata[0].name
                key  = "MINIO_ACCESS_KEY"
              }
            }
          }

          env {
            name = "MINIO_SECRET_KEY"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.backend_secret.metadata[0].name
                key  = "MINIO_SECRET_KEY"
              }
            }
          }

          volume_mount {
            name       = var.backend_storage_name
            mount_path = "/app/data"
          }

        }

        volume {
          name = var.backend_storage_name
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.backend_pvc.metadata[0].name
          }
        }

      }
    }
  }

  depends_on = [
    kubernetes_deployment.backend_streamer,
    kubernetes_deployment.postgres,
    kubernetes_deployment.redis,
    kubernetes_deployment.minio
  ]
}


resource "kubernetes_service" "backend_api" {
  metadata {
    name      = var.backend_api_name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = var.backend_api_name
    }

    port {
      port        = var.backend_api_port
      target_port = var.backend_api_port
    }

    type = var.backend_network_type
  }
}



resource "kubernetes_horizontal_pod_autoscaler_v2" "backend_api_hpa" {
  metadata {
    name      = var.backend_api_hpa
    namespace = var.namespace
  }
  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = var.backend_api_name
    }
    min_replicas = var.backend_api_min_replicas
    max_replicas = var.backend_api_max_replicas
    metric {
      type = "Resource"
      resource {
      name = "cpu"
      target {
        type                = "Utilization"
        average_utilization = var.backend_api_cpu_target
      }
      }
    }
    metric {
      type = "Resource"
      resource {
      name = "memory"
      target {
        type                = "Utilization"
        average_utilization = var.backend_api_mem_target
      }
      }
    }
  }
}

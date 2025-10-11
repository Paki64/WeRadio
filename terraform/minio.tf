# MinIO Object Storage

resource "kubernetes_secret" "minio_secret" {
  metadata {
    name      = var.minio_secret
    namespace = var.namespace
  }

  data = {
    MINIO_ROOT_USER     = var.minio_root_user
    MINIO_ROOT_PASSWORD = var.minio_root_password
  }

  type = var.minio_secret_type
}



resource "kubernetes_persistent_volume_claim" "minio_pvc" {
  metadata {
    name      = var.minio_storage_name
    namespace = var.namespace
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = var.minio_storage
      }
    }
  }
}



resource "kubernetes_deployment" "minio" {
  metadata {
    name      = var.minio_name
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = var.minio_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.minio_name
        }
      }

      spec {
        container {
          name  = var.minio_name
          image = var.minio_image

          command = ["minio", "server", "/data", "--console-address", ":9001"]

          env {
            name = "MINIO_ROOT_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.minio_secret.metadata[0].name
                key  = "MINIO_ROOT_USER"
              }
            }
          }

          env {
            name = "MINIO_ROOT_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.minio_secret.metadata[0].name
                key  = "MINIO_ROOT_PASSWORD"
              }
            }
          }

          env {
            name  = "TZ"
            value = var.timezone
          }

          resources {
            requests = {
              cpu    = var.minio_cpu_request
              memory = var.minio_mem_request
            }
            limits = {
              cpu    = var.minio_cpu_limit
              memory = var.minio_mem_limit
            }
          }

          port {
            container_port = var.minio_api_port
          }

          port {
            container_port = var.minio_console_port
          }

          volume_mount {
            name       = var.minio_storage_name
            mount_path = "/data"
          }

          readiness_probe {
            http_get {
              path = "/minio/health/live"
              port = var.minio_api_port
            }
            initial_delay_seconds = 30
            period_seconds        = 30
            timeout_seconds       = 20
            failure_threshold     = 3
          }
        }

        volume {
          name = var.minio_storage_name
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.minio_pvc.metadata[0].name
          }
        }
      }
    }
  }
}



resource "kubernetes_service" "minio" {
  metadata {
    name      = var.minio_name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = var.minio_name
    }

    port {
      name        = "api"
      port        = var.minio_api_port
      target_port = var.minio_api_port
    }

    port {
      name        = "console"
      port        = var.minio_console_port
      target_port = var.minio_console_port
    }

    type = var.minio_network_type
  }
}

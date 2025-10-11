# Redis Cache

resource "kubernetes_secret" "redis_secret" {
  metadata {
    name      = var.redis_secret
    namespace = var.namespace
  }

  data = {
    REDIS_PASSWORD = var.redis_password
  }

  type = var.redis_secret_type
}



resource "kubernetes_persistent_volume_claim" "redis_pvc" {
  metadata {
    name      = var.redis_storage_name
    namespace = var.namespace
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = var.redis_storage
      }
    }
  }
}



resource "kubernetes_deployment" "redis" {
  metadata {
    name      = var.redis_name
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = var.redis_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.redis_name
        }
      }

      spec {
        container {
          name  = var.redis_name
          image = var.redis_image

          command = ["redis-server", "--requirepass", "$(REDIS_PASSWORD)"]

          env {
            name = "REDIS_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.redis_secret.metadata[0].name
                key  = "REDIS_PASSWORD"
              }
            }
          }

          env {
            name  = "TZ"
            value = var.timezone
          }

          resources {
            requests = {
              cpu    = var.redis_cpu_request
              memory = var.redis_mem_request
            }
            limits = {
              cpu    = var.redis_cpu_limit
              memory = var.redis_mem_limit
            }
          }

          port {
            container_port = var.redis_port
          }

          volume_mount {
            name       = var.redis_storage_name
            mount_path = "/data"
          }

          readiness_probe {
            exec {
              command = ["redis-cli", "ping"]
            }
            initial_delay_seconds = 10
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 5
          }
        }

        volume {
          name = var.redis_storage_name
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.redis_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "redis" {
  metadata {
    name      = var.redis_name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = var.redis_name
    }

    port {
      port        = var.redis_port
      target_port = var.redis_port
    }

    type = var.redis_network_type
  }
}

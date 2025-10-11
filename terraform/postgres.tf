# PostgreSQL Database

resource "kubernetes_secret" "postgres_secret" {
  metadata {
    name      = var.postgres_secret
    namespace = var.namespace
  }

  data = {
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
  }

  type = var.postgres_secret_type
}



resource "kubernetes_persistent_volume_claim" "postgres_pvc" {
  metadata {
    name      = var.postgres_storage_name
    namespace = var.namespace
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = var.postgres_storage
      }
    }
  }
}



resource "kubernetes_deployment" "postgres" {
  metadata {
    name      = var.postgres_name
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = var.postgres_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.postgres_name
        }
      }

      spec {
        container {
          name  = var.postgres_name
          image = var.postgres_image

          env {
            name  = "POSTGRES_DB"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgres_secret.metadata[0].name
                key  = "POSTGRES_DB"
              }
            }
          }

          env {
            name  = "POSTGRES_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgres_secret.metadata[0].name
                key  = "POSTGRES_USER"
              }
            }
          }

          env {
            name  = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgres_secret.metadata[0].name
                key  = "POSTGRES_PASSWORD"
              }
            }
          }

          env {
            name  = "TZ"
            value = var.timezone
          }

          env {
            name  = "LANG"
            value = var.postgres_lang
          }

          env {
            name  = "LC_ALL"
            value = var.postgres_lc_all
          }

          port {
            container_port = var.postgres_port
          }

          volume_mount {
            name       = var.postgres_storage_name
            mount_path = "/var/lib/postgresql/data"
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "weradio_user", "-d", "weradio"]
            }
            initial_delay_seconds = 10
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 5
          }
        }

        volume {
          name = var.postgres_storage_name
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.postgres_pvc.metadata[0].name
          }
        }
      }
    }
  }
}



resource "kubernetes_service" "postgres" {
  metadata {
    name      = var.postgres_name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = var.postgres_name
    }

    port {
      port        = var.postgres_port
      target_port = var.postgres_port
    }

    type = var.postgres_network_type
  }
}

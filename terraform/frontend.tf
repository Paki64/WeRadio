# Frontend Service

resource "kubernetes_config_map" "frontend_config" {
  metadata {
    name      = var.frontend_config
    namespace = var.namespace
  }

  data = {
    FRONTEND_PORT = var.frontend_port
    API_URL       = var.api_url
  }
}



resource "kubernetes_deployment" "frontend" {
  metadata {
    name      = var.frontend_name
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = var.frontend_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.frontend_name
        }
      }

      spec {
        container {
          name  = var.frontend_name
          image = var.frontend_image

          env {
            name = "FRONTEND_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.frontend_config.metadata[0].name
                key  = "FRONTEND_PORT"
              }
            }
          }

          env {
            name = "API_URL"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.frontend_config.metadata[0].name
                key  = "API_URL"
              }
            }
          }

          resources {
            requests = {
              cpu    = var.frontend_cpu_request
              memory = var.frontend_mem_request
            }
            limits = {
              cpu    = var.frontend_cpu_limit
              memory = var.frontend_mem_limit
            }
          }

          readiness_probe {
            http_get {
              path = "/"
              port = var.frontend_port
            }
            initial_delay_seconds = 30
            period_seconds        = 10
          }

          liveness_probe {
            http_get {
              path = "/"
              port = var.frontend_port
            }
            initial_delay_seconds = 60
            period_seconds        = 30
          }

          port {
            container_port = var.frontend_port
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_deployment.backend_api
  ]
}



resource "kubernetes_service" "frontend" {
  metadata {
    name      = var.frontend_name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = var.frontend_name
    }

    port {
      port        = var.frontend_port
      target_port = var.frontend_port
    }

    type = var.frontend_network_type
  }
}



resource "kubernetes_horizontal_pod_autoscaler_v2" "frontend_hpa" {
  metadata {
    name      = var.frontend_hpa
    namespace = var.namespace
  }
  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = var.frontend_name
    }
    min_replicas = var.frontend_min_replicas
    max_replicas = var.frontend_max_replicas
    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = var.frontend_cpu_target
        }
      }
    }
    metric {
      type = "Resource"
      resource {
        name = "memory"
        target {
          type                = "Utilization"
          average_utilization = var.frontend_mem_target
        }
      }
    }
  }
}

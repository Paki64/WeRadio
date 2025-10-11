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

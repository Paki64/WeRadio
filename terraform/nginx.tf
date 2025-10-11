# Nginx Reverse Proxy

resource "kubernetes_config_map" "nginx_config" {
  metadata {
    name      = var.nginx_config
    namespace = var.namespace
  }

  data = {
    "nginx.conf" = <<-EOT
      events {
        worker_connections 1024;
      }

      http {
        upstream frontend {
          server ${var.frontend_name}:${var.frontend_port};
        }

        upstream backend_api {
          server ${var.backend_api_name}:${var.backend_api_port};
        }

        server {
          listen ${var.nginx_port};
          client_max_body_size 1000M;

          location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
          }

          location /api/ {
            if ($request_method = 'OPTIONS') {
              add_header 'Access-Control-Allow-Origin' '*';
              add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
              add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type';
              add_header 'Access-Control-Max-Age' 86400;
              return 204;
            }
            proxy_pass http://backend_api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_send_timeout 300s;
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type';
          }

          location /hls/ {
            proxy_pass http://backend_api/hls/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
          }
        }
      }
    EOT
  }
}

resource "kubernetes_deployment" "nginx" {
  metadata {
    name      = var.nginx_name
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = var.nginx_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.nginx_name
        }
      }

      spec {
        container {
          name  = var.nginx_name
          image = var.nginx_image

          port {
            container_port = var.nginx_port
          }

          volume_mount {
            name       = "nginx-config"
            mount_path = "/etc/nginx/nginx.conf"
            sub_path   = "nginx.conf"
          }
        }

        volume {
          name = "nginx-config"
          config_map {
            name = kubernetes_config_map.nginx_config.metadata[0].name
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_deployment.frontend,
    kubernetes_deployment.backend_api
  ]
}

resource "kubernetes_service" "nginx" {
  metadata {
    name      = var.nginx_name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = var.nginx_name
    }

    port {
      port        = var.nginx_port
      target_port = var.nginx_port
      node_port   = var.nginx_node_port
    }

    type = var.nginx_network_type
  }
}



resource "kubernetes_horizontal_pod_autoscaler_v2" "nginx_hpa" {
  metadata {
    name      = var.nginx_hpa
    namespace = var.namespace
  }
  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = var.nginx_name
    }
    min_replicas = var.nginx_min_replicas
    max_replicas = var.nginx_max_replicas
    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = var.nginx_cpu_target
        }
      }
    }
  }
}

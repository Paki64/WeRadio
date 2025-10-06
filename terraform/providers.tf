terraform {
  required_providers {
    kubernetes = {
      source = "hashicorp/kubernetes"
      version = var.kubernetes_version
    }
  }
}

provider "kubernetes" {
  config_path     = "~/.kube/config"
  config_context  = var.kubernetes_context
}
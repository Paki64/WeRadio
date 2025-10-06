# PROVIDERS
variable "kubernetes_version" {
  description = "The version of the Kubernetes provider"
  type        = string
  default     = "2.38.0"
}
variable "kubernetes_context" {
  description = "The context to use in the Kubernetes config"
  type        = string
  default     = "minikube"
}


# NAMESPACES
variable "namespace" {
  description = "The name of the Kubernetes namespace"
  type        = string
  default     = "weradio"
}

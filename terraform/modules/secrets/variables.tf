variable "project_id" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "kubernetes_namespace" {
  type = string
}

variable "kubernetes_service_account" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  type      = string
  sensitive = true
}

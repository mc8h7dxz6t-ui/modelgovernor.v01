variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "Primary GCP region."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Primary GCP zone."
  type        = string
  default     = "us-central1-a"
}

variable "cluster_name" {
  description = "Base cluster name."
  type        = string
  default     = "modelgovernor"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "prod"
}

variable "gke_node_machine_type" {
  description = "GKE node machine type."
  type        = string
  default     = "e2-standard-4"
}

variable "gke_initial_node_count" {
  description = "Initial GKE node count."
  type        = number
  default     = 1
}

variable "gke_min_node_count" {
  description = "Minimum GKE node count."
  type        = number
  default     = 1
}

variable "gke_max_node_count" {
  description = "Maximum GKE node count."
  type        = number
  default     = 5
}

variable "postgres_tier" {
  description = "Cloud SQL instance tier."
  type        = string
  default     = "db-g1-small"
}

variable "postgres_db_name" {
  description = "Application database name."
  type        = string
  default     = "modelgovernor"
}

variable "redis_memory_size_gb" {
  description = "Memorystore memory size in GB."
  type        = number
  default     = 1
}

variable "authorized_networks" {
  description = "Networks allowed to reach the GKE control plane."
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

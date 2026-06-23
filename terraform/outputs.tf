output "cluster_name" {
  description = "GKE cluster name."
  value       = module.gke.cluster_name
}

output "cluster_endpoint" {
  description = "GKE control plane endpoint."
  value       = module.gke.cluster_endpoint
}

output "cluster_ca_certificate" {
  description = "Base64 CA certificate for the cluster."
  value       = module.gke.cluster_ca_certificate
  sensitive   = true
}

output "postgres_connection_name" {
  description = "Cloud SQL connection name."
  value       = module.postgres.connection_name
}

output "postgres_private_ip" {
  description = "Cloud SQL private IP address."
  value       = module.postgres.private_ip_address
}

output "redis_host" {
  description = "Memorystore endpoint."
  value       = module.redis.host
}

output "redis_port" {
  description = "Memorystore port."
  value       = module.redis.port
}

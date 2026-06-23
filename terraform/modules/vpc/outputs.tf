output "network_id" {
  value = google_compute_network.vpc.id
}

output "network_self_link" {
  value = google_compute_network.vpc.self_link
}

output "subnetwork_self_link" {
  value = google_compute_subnetwork.gke.self_link
}

output "subnetwork_name" {
  value = google_compute_subnetwork.gke.name
}

output "pods_range_name" {
  value = google_compute_subnetwork.gke.secondary_ip_range[0].range_name
}

output "services_range_name" {
  value = google_compute_subnetwork.gke.secondary_ip_range[1].range_name
}

output "service_networking_connection" {
  value = google_service_networking_connection.private_service_access.id
}

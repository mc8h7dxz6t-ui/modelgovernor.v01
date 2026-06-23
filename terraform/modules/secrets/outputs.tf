output "gcp_service_account_email" {
  value = google_service_account.runtime.email
}

output "secret_ids" {
  value = [for secret in google_secret_manager_secret.runtime : secret.secret_id]
}

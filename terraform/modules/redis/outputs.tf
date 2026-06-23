output "host" {
  value = google_redis_instance.this.host
}

output "port" {
  value = google_redis_instance.this.port
}

output "auth_string" {
  value     = google_redis_instance.this.auth_string
  sensitive = true
}

output "connection_uri" {
  value     = "rediss://default:${urlencode(google_redis_instance.this.auth_string)}@${google_redis_instance.this.host}:${google_redis_instance.this.port}/0"
  sensitive = true
}

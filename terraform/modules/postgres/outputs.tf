output "connection_name" {
  value = google_sql_database_instance.this.connection_name
}

output "private_ip_address" {
  value = google_sql_database_instance.this.private_ip_address
}

output "database_name" {
  value = google_sql_database.app.name
}

output "username" {
  value = google_sql_user.app.name
}

output "password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "connection_uri" {
  value     = "postgresql+psycopg://${google_sql_user.app.name}:${urlencode(random_password.db_password.result)}@${google_sql_database_instance.this.private_ip_address}:5432/${google_sql_database.app.name}"
  sensitive = true
}

resource "google_redis_instance" "this" {
  name                    = "${var.name_prefix}-redis"
  project                 = var.project_id
  region                  = var.region
  tier                    = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb          = var.redis_memory_size_gb
  authorized_network      = var.authorized_network
  connect_mode            = "PRIVATE_SERVICE_ACCESS"
  transit_encryption_mode = "SERVER_AUTHENTICATION"
  auth_enabled            = true

  redis_configs = {
    "maxmemory-policy" = "allkeys-lru"
  }
}

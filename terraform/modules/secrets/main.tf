resource "random_password" "sidecar_tokens" {
  length  = 32
  special = false
}

resource "random_password" "litellm_master_key" {
  length  = 40
  special = false
}

resource "google_service_account" "runtime" {
  account_id   = substr(replace("${var.name_prefix}-runtime", "_", "-"), 0, 30)
  project      = var.project_id
  display_name = "modelgovernor runtime"
}

resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.kubernetes_namespace}/${var.kubernetes_service_account}]"
}

locals {
  secret_payloads = {
    "modelgovernor-database-url"       = var.database_url
    "modelgovernor-redis-url"          = var.redis_url
    "modelgovernor-sidecar-tokens"     = random_password.sidecar_tokens.result
    "modelgovernor-openai-api-key"     = "REPLACE_WITH_OPENAI_API_KEY"
    "modelgovernor-litellm-master-key" = random_password.litellm_master_key.result
  }
}

resource "google_secret_manager_secret" "runtime" {
  for_each  = local.secret_payloads
  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "runtime" {
  for_each    = local.secret_payloads
  secret      = google_secret_manager_secret.runtime[each.key].id
  secret_data = each.value
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each  = google_secret_manager_secret.runtime
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

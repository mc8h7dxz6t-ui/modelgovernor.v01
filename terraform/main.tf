locals {
  name_prefix = "${var.cluster_name}-${var.environment}"
  common_labels = {
    project     = var.cluster_name
    environment = var.environment
    "managed-by" = "terraform"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

data "google_client_config" "current" {}

provider "kubernetes" {
  host                   = "https://${module.gke.cluster_endpoint}"
  token                  = data.google_client_config.current.access_token
  cluster_ca_certificate = base64decode(module.gke.cluster_ca_certificate)
}

resource "google_project_service" "apis" {
  for_each = toset([
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

module "vpc" {
  source      = "./modules/vpc"
  project_id  = var.project_id
  region      = var.region
  name_prefix = local.name_prefix

  depends_on = [google_project_service.apis]
}

module "gke" {
  source                 = "./modules/gke"
  project_id             = var.project_id
  region                 = var.region
  zone                   = var.zone
  cluster_name           = var.cluster_name
  environment            = var.environment
  name_prefix            = local.name_prefix
  network_self_link      = module.vpc.network_self_link
  subnetwork_self_link   = module.vpc.subnetwork_self_link
  pods_range_name        = module.vpc.pods_range_name
  services_range_name    = module.vpc.services_range_name
  authorized_networks    = var.authorized_networks
  initial_node_count     = var.gke_initial_node_count
  min_node_count         = var.gke_min_node_count
  max_node_count         = var.gke_max_node_count
  node_machine_type      = var.gke_node_machine_type

  depends_on = [google_project_service.apis, module.vpc]
}

module "postgres" {
  source            = "./modules/postgres"
  project_id        = var.project_id
  region            = var.region
  environment       = var.environment
  name_prefix       = local.name_prefix
  postgres_db_name  = var.postgres_db_name
  postgres_tier     = var.postgres_tier
  private_network   = module.vpc.network_self_link

  depends_on = [google_project_service.apis, module.vpc]
}

module "redis" {
  source               = "./modules/redis"
  project_id           = var.project_id
  region               = var.region
  environment          = var.environment
  name_prefix          = local.name_prefix
  authorized_network   = module.vpc.network_self_link
  redis_memory_size_gb = var.redis_memory_size_gb

  depends_on = [google_project_service.apis, module.vpc]
}

module "secrets" {
  source                     = "./modules/secrets"
  project_id                 = var.project_id
  name_prefix                = local.name_prefix
  kubernetes_namespace       = "modelgovernor"
  kubernetes_service_account = "modelgovernor-runtime"
  database_url               = module.postgres.connection_uri
  redis_url                  = module.redis.connection_uri

  depends_on = [google_project_service.apis, module.postgres, module.redis]
}

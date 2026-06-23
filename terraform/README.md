# Terraform deployment

## Prerequisites

- Terraform 1.6 or newer
- `gcloud` authenticated to the target project
- A GCS bucket for Terraform state
- IAM permissions to manage GKE, VPC, Cloud SQL, Memorystore, and Secret Manager

## Usage

1. Replace `REPLACE_WITH_YOUR_TF_STATE_BUCKET` in `versions.tf`.
2. Create a `terraform.tfvars` or pass variables on the CLI, at minimum `project_id`.
3. Initialize, plan, and apply:

```bash
terraform init
terraform plan -var="project_id=YOUR_PROJECT_ID"
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

The stack provisions a private VPC, a private GKE cluster, Cloud SQL PostgreSQL, Memorystore Redis, Secret Manager entries, and Workload Identity access for Kubernetes workloads.

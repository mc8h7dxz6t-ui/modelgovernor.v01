# Cloud deployment

## Prerequisites

- `gcloud` authenticated to the target GCP project
- Terraform 1.6+
- `kubectl`
- `kustomize`
- Helm 3
- A GCS bucket for Terraform state and a GKE-compatible `KUBECONFIG`

## Terraform workflow

Initialize from `terraform/`, replace the backend bucket in `versions.tf`, then provide required variables such as `project_id`.

```bash
cd terraform
terraform init
terraform plan -var="project_id=YOUR_PROJECT_ID"
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

Terraform creates the private VPC, GKE cluster, Cloud SQL for PostgreSQL, Memorystore for Redis, Secret Manager secrets, and the Workload Identity bindings used by the runtime.

## Kustomize overlays

Use the base manifests in `deploy/base` for shared resources, then render the environment overlays:

```bash
kustomize build deploy/overlays/dev
kustomize build deploy/overlays/prod
```

The dev overlay reduces replica counts and relaxes sidecar limits. The prod overlay increases replicas, expands HPA bounds, and turns the gateway Service into a public GCP load balancer. Update image tags either by editing the overlay `images` entries or by using `kustomize edit set image`.

## Helm usage

Install or upgrade with the bundled chart:

```bash
helm install modelgovernor helm/modelgovernor
helm upgrade --install modelgovernor helm/modelgovernor -f helm/modelgovernor/values-prod.yaml
```

`values.yaml` carries safe defaults and `values-prod.yaml` raises replica counts and limits for production.

## CI/CD workflows

`.github/workflows/ci.yml` compiles the Python services, runs the integration suite against PostgreSQL and Redis service containers, and validates both Kustomize overlays plus the Helm chart.

`.github/workflows/promote.yml` is a manual promotion workflow. It validates a semantic image tag, rewrites the selected overlay image tags, renders manifests, performs a client-side dry run, and applies only when the target overlay is `prod`.

## Network boundaries

- **Gateway** accepts external ingress on port 4000 and can only egress to sidecar, DNS, and provider HTTPS endpoints.
- **Sidecar** only accepts ingress from gateway and kube-system probes, and only egresses to Postgres, Redis, DNS, and HTTPS callbacks.
- **Reconciler** is internal-only; kube-system can probe it, and it only reaches Postgres and DNS.
- **Redis** only accepts traffic from sidecar and reconciler and has no outbound access.

These policies keep provider access at the gateway boundary and keep ledger access constrained to the governance plane.

## Secrets management

`deploy/base/secrets/external-secret.yaml` defines External Secrets Operator resources backed by a `ClusterSecretStore` named `modelgovernor-secrets`. Terraform provisions the referenced Secret Manager secrets. ESO syncs those values into the Kubernetes Secrets consumed by sidecar, reconciler, and gateway.

## Scaling

The sidecar HPA uses `autoscaling/v2` with CPU and memory targets to absorb reserve/settle bursts while protecting memory-heavy paths. The gateway HPA uses CPU scaling for proxy throughput. Production overlays increase the minimum replica floor and maximum burst ceiling for both services.

## Monitoring

The sidecar exposes `/metrics` for Prometheus-format scraping. In GKE, this endpoint can be collected by a Prometheus operator, Managed Service for Prometheus, or an OpenTelemetry collector and then forwarded into Cloud Monitoring dashboards and alerting policies.

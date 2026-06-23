# Kubernetes Helm Chart Architecture Blueprint

## Purpose

This blueprint closes the repository's hosted-operations documentation gap by
describing a production-grade Helm packaging model for `modelgovernor.v01`.
It is intentionally architectural rather than executable: the goal is to define
the chart structure, scaling rules, health model, and security posture that a
hosted deployment should implement.

## Design goals

- preserve the repository's deterministic finance-plane boundaries
- package the platform for repeatable Kubernetes installation
- make runtime scaling explicit rather than ad hoc
- expose health, readiness, and observability surfaces required for hosted SRE
- keep stateful dependencies external so the chart remains portable

## Release topology

The Helm release should package only the components owned by this repository:

- optional **gateway** Deployment and Service for governed routing
- **sidecar** Deployment and Service as the authoritative policy plane
- **reconciler** CronJob for deterministic expiry and stranded-hold repair
- **PodMonitor** or `ServiceMonitor` for Prometheus scraping
- **PrometheusRule** resources for baseline alerting
- **NetworkPolicy**, **PodDisruptionBudget**, **HorizontalPodAutoscaler**, and
  optional **Ingress** resources

The chart should not bundle Postgres or Redis for production use.  Those remain
externally managed dependencies referenced by connection strings and secrets.

## Recommended chart layout

```text
charts/modelgovernor/
  Chart.yaml
  values.yaml
  values-production.yaml
  values-standalone.yaml
  templates/
    _helpers.tpl
    namespace.yaml
    serviceaccount.yaml
    gateway-deployment.yaml
    gateway-service.yaml
    sidecar-deployment.yaml
    sidecar-service.yaml
    reconciler-cronjob.yaml
    hpa-sidecar.yaml
    hpa-gateway.yaml
    pdb-sidecar.yaml
    ingress.yaml
    networkpolicy.yaml
    podmonitor.yaml
    prometheusrule.yaml
    externalsecret.yaml
```

## Values model

The chart should expose a small number of explicit value groups:

- `global`: namespace, common labels, image registry, pull secrets
- `mode`: `governed` or `standalone`
- `gateway`: enablement, replicas, autoscaling, ingress, resources
- `sidecar`: image, replicas, resources, probes, env, autoscaling, PDB
- `reconciler`: schedule, resources, backoff, history limits
- `security`: service accounts, pod security, network policies, secret names
- `observability`: PodMonitor, scrape interval, alert rule enablement
- `externalDependencies`: `postgres`, `redis`, `pgbouncer`, TLS endpoints

This keeps operator choices visible and prevents security-critical behavior from
being buried inside templates.

## Structural scaling rules

### Sidecar

The sidecar is the only authoritative request-path workload in this repository
and should be horizontally scaled by structure, not by emergency tuning:

- baseline `replicaCount: 2` to avoid a single-pod control-plane failure
- `minReplicas: 2` in production
- `maxReplicas` sized to the database proxy and provider-rate budget
- HPA v2 on both CPU and memory
- optional custom metric on in-flight request concurrency or request rate when a
  Prometheus adapter or service mesh is available
- scale-down stabilization to avoid oscillation during bursty traffic

Recommended baseline targets:

- CPU average utilization: `60%`
- memory average utilization: `70%`
- scale-up policy: allow rapid doubling for short bursts
- scale-down policy: stabilize for `300s`

The sidecar must not autoscale independently of the database path.  Production
deployments should pair it with PgBouncer, RDS Proxy, or an equivalent
transaction-pooling layer and keep application pools intentionally small.

### Gateway

When the governed gateway is deployed in-cluster:

- start with `replicaCount: 2`
- scale on CPU plus request-rate metrics if available
- keep gateway and sidecar HPA ceilings coordinated so the gateway cannot
  overwhelm the policy plane

### Reconciler

The reconciler remains a CronJob, not an HPA-managed service:

- `concurrencyPolicy: Forbid`
- small, fixed resource envelope
- schedule tuned to reservation TTL and stranded-hold response objectives
- horizontal scaling achieved by more frequent execution only after verifying
  database lock behavior and sweep duration

## Health and readiness model

Hosted operations should standardize three probe classes:

- **startup probe** on `/healthz` to tolerate cold starts and image pulls
- **liveness probe** on `/healthz` to detect wedged processes
- **readiness probe** on `/readyz` to gate traffic

Recommended production defaults for the sidecar:

```text
startupProbe:
  path: /healthz
  periodSeconds: 5
  failureThreshold: 12

livenessProbe:
  path: /healthz
  periodSeconds: 15
  timeoutSeconds: 2
  failureThreshold: 3

readinessProbe:
  path: /readyz
  periodSeconds: 10
  timeoutSeconds: 2
  failureThreshold: 3
```

Readiness must be treated as the traffic gate.  A rollout is not complete until
new pods pass `/readyz`, Prometheus scraping resumes, and baseline admin and
audit routes remain reachable from trusted networks.

## Workload safety controls

Every production template should include:

- `securityContext` with `runAsNonRoot`, `readOnlyRootFilesystem`, and
  `allowPrivilegeEscalation: false`
- explicit resource requests and limits
- `PodDisruptionBudget` for sidecar with `minAvailable: 1`
- `topologySpreadConstraints` across zones when the cluster supports them
- rolling update strategy with `maxSurge: 1` and `maxUnavailable: 0`
- `terminationGracePeriodSeconds` sized for in-flight HTTP completion

## Network and trust-boundary controls

The chart should enforce the repository's trust boundaries:

- ingress reaches only the gateway or an explicitly internal sidecar endpoint
- only gateway, reconciler, and trusted admin sources may call sidecar routes
- sidecar egress is limited to Postgres, Redis, and approved provider endpoints
- reconciler egress is limited to Postgres
- admin routes remain internal-only and continue to require `X-Internal-Token`

Recommended Kubernetes controls:

- default-deny `NetworkPolicy`
- separate ServiceAccounts for gateway, sidecar, and reconciler
- least-privilege RBAC
- external secret injection rather than inline Secret manifests

## Hosted operations baseline

To close the hosted-operations gap, the Helm package should be accompanied by
environment-specific values and clear ownership of these run-time controls:

- ingress and TLS termination model
- Postgres HA endpoint and transaction-pooling proxy
- Redis HA policy and failover expectation
- backup and restore workflow for the ledger database
- alert routing, on-call ownership, and escalation path
- upgrade path for images, migrations, and chart revisions
- rollback criteria based on readiness, metrics, and reconciliation health

## Environment profiles

The blueprint supports two primary values profiles:

### Governed hosted profile

- gateway enabled
- sidecar replicas >= 2
- HPA enabled
- PodMonitor and PrometheusRule enabled
- Ingress enabled with TLS
- NetworkPolicy enforced
- external Postgres, Redis, and secret manager required

### Standalone operator profile

- gateway disabled
- sidecar exposed only on internal Service or private ingress
- same probes and security controls retained
- reduced HPA ceilings for small environments

## Questionnaire-ready summary

This Helm blueprint gives buyers and operators a concrete answer for:

- how the platform is packaged for Kubernetes
- how health and readiness are enforced
- how horizontal scaling is bounded
- how trusted traffic is separated from untrusted traffic
- how observability and alerting are wired into the release

It therefore fills the previously open hosted-operations documentation gap
without changing the repository's core control-plane boundaries.

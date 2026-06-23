# Observability

## Scrape surfaces

| Endpoint | Auth | Contents |
|---|---|---|
| `GET /metrics/prometheus` (sidecar) | None | Process invariant counters, HTTP RED metrics |
| `GET /metrics` (sidecar) | Internal token | DB aggregates + invariant counters |
| `GET /metrics.json` | None | JSON invariant snapshot |
| `GET /metrics/prometheus` (reconciler) | None | Invariant counters + leader gauge |

PodMonitors: `deploy/base/sidecar-podmonitor.yaml`, `deploy/base/reconciler-podmonitor.yaml`.

## Tracing

Set `OTEL_EXPORTER_OTLP_ENDPOINT` (sidecar deployment wires `http://otel-collector:4318`).
Collector manifest: `deploy/base/otel-collector.yaml`.

Reserve and settle handlers emit spans when OTEL packages are installed.

## Dashboards

Grafana dashboard ConfigMap: `deploy/base/grafana-dashboard.yaml` (reserve SLO panels).

## SLOs

See `docs/slo-definitions.md` for SLI targets and multi-window burn-rate alerts in
`deploy/base/prometheus-rules.yaml`.

## Synthetic probes

`synthetic-canary` CronJob (`deploy/base/synthetic-probe-cronjob.yaml`) probes sidecar,
gateway, and reconciler health every 5 minutes.

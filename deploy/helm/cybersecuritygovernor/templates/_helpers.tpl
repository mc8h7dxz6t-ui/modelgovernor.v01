{{/*
CybersecurityGovernor Helm chart helpers
*/}}
{{- define "cybersecuritygovernor.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "cybersecuritygovernor.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "cybersecuritygovernor.namespace" -}}
{{- .Values.global.namespace }}
{{- end }}

{{- define "cybersecuritygovernor.labels" -}}
helm.sh/chart: {{ include "cybersecuritygovernor.name" . }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "cybersecuritygovernor.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- range $k, $v := .Values.global.labels }}
{{ $k }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{- define "cybersecuritygovernor.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cybersecuritygovernor.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "cybersecuritygovernor.secretName" -}}
{{- .Values.secrets.name }}
{{- end }}

{{- define "cybersecuritygovernor.image" -}}
{{- $img := index .Values.images .imageKey -}}
{{- printf "%s:%s" $img.repository $img.tag }}
{{- end }}

{{- define "cybersecuritygovernor.syncWave" -}}
{{- if .wave }}
argocd.argoproj.io/sync-wave: {{ .wave | quote }}
{{- end }}
{{- end }}

{{- define "cybersecuritygovernor.istioPodAnnotations" -}}
{{- if .Values.enterprise.istio.enabled }}
sidecar.istio.io/inject: "true"
{{- end }}
{{- end }}

{{- define "cybersecuritygovernor.istioPrincipal" -}}
cluster.local/ns/{{ include "cybersecuritygovernor.namespace" .root }}/sa/{{ .serviceAccount }}
{{- end }}

{{- define "cybersecuritygovernor.platformServiceAccountName" -}}
{{- if .Values.serviceAccounts.create -}}
{{- .Values.serviceAccounts.platform.name -}}
{{- end -}}
{{- end }}

{{- define "cybersecuritygovernor.gatewayServiceAccountName" -}}
{{- if .Values.serviceAccounts.create -}}
{{- .Values.serviceAccounts.gateway.name -}}
{{- end -}}
{{- end }}

{{- define "cybersecuritygovernor.postgresBackendHost" -}}
{{- if .Values.postgres.external.enabled -}}
{{- .Values.postgres.external.host -}}
{{- else -}}
postgres
{{- end -}}
{{- end }}

{{- define "cybersecuritygovernor.postgresBackendPort" -}}
{{- if .Values.postgres.external.enabled -}}
{{- .Values.postgres.external.port -}}
{{- else -}}
5432
{{- end -}}
{{- end }}

{{- define "cybersecuritygovernor.platformIntegrationEnv" -}}
- name: CG_PLATFORM_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "cybersecuritygovernor.secretName" .root }}
      key: database-url
- name: SIEM_EXPORT_MODE
  value: {{ .root.Values.integrations.siemExportMode | quote }}
- name: THREAT_INTEL_MODE
  value: {{ .root.Values.integrations.threatIntelMode | quote }}
- name: THREAT_INTEL_SOURCE
  value: {{ .root.Values.integrations.threatIntelSource | quote }}
{{- if .root.Values.integrations.splunkHecUrl }}
- name: SPLUNK_HEC_URL
  value: {{ .root.Values.integrations.splunkHecUrl | quote }}
{{- end }}
{{- if .root.Values.integrations.sentinelWorkspaceId }}
- name: SENTINEL_WORKSPACE_ID
  value: {{ .root.Values.integrations.sentinelWorkspaceId | quote }}
{{- end }}
{{- if .root.Values.integrations.threatIntelFeedUrl }}
- name: THREAT_INTEL_FEED_URL
  value: {{ .root.Values.integrations.threatIntelFeedUrl | quote }}
{{- end }}
{{- end }}

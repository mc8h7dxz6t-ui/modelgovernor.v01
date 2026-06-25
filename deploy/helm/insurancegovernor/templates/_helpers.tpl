{{/*
InsuranceGovernor Helm chart helpers
*/}}
{{- define "insurancegovernor.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "insurancegovernor.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "insurancegovernor.namespace" -}}
{{- .Values.global.namespace }}
{{- end }}

{{- define "insurancegovernor.labels" -}}
helm.sh/chart: {{ include "insurancegovernor.name" . }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "insurancegovernor.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- range $k, $v := .Values.global.labels }}
{{ $k }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{- define "insurancegovernor.selectorLabels" -}}
app.kubernetes.io/name: {{ include "insurancegovernor.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "insurancegovernor.secretName" -}}
{{- .Values.secrets.name }}
{{- end }}

{{- define "insurancegovernor.image" -}}
{{- $img := index .Values.images .imageKey -}}
{{- printf "%s:%s" $img.repository $img.tag }}
{{- end }}

{{- define "insurancegovernor.syncWave" -}}
{{- if .wave }}
argocd.argoproj.io/sync-wave: {{ .wave | quote }}
{{- end }}
{{- end }}

{{- define "insurancegovernor.istioPodAnnotations" -}}
{{- if .Values.enterprise.istio.enabled }}
sidecar.istio.io/inject: "true"
{{- end }}
{{- end }}

{{- define "insurancegovernor.postgresBackendHost" -}}
{{- if .Values.postgres.external.enabled -}}
{{- .Values.postgres.external.host -}}
{{- else -}}
postgres
{{- end -}}
{{- end }}

{{- define "insurancegovernor.postgresBackendPort" -}}
{{- if .Values.postgres.external.enabled -}}
{{- .Values.postgres.external.port -}}
{{- else -}}
5432
{{- end -}}
{{- end }}

{{- define "insurancegovernor.platformIntegrationEnv" -}}
- name: IG_PLATFORM_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "insurancegovernor.secretName" .root }}
      key: database-url
- name: PAYMENT_RAIL_MODE
  value: {{ .root.Values.integrations.paymentRailMode | quote }}
- name: ORACLE_FEED_MODE
  value: {{ .root.Values.integrations.oracleFeedMode | quote }}
- name: ORACLE_FEED_SOURCE
  value: {{ .root.Values.integrations.oracleFeedSource | quote }}
{{- if .root.Values.integrations.fednowApiUrl }}
- name: FEDNOW_API_URL
  value: {{ .root.Values.integrations.fednowApiUrl | quote }}
{{- end }}
{{- if .root.Values.integrations.clearinghouseApiUrl }}
- name: CLEARINGHOUSE_API_URL
  value: {{ .root.Values.integrations.clearinghouseApiUrl | quote }}
{{- end }}
{{- if .root.Values.integrations.oracleFeedUrl }}
- name: ORACLE_FEED_URL
  value: {{ .root.Values.integrations.oracleFeedUrl | quote }}
{{- end }}
{{- end }}

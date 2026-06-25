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

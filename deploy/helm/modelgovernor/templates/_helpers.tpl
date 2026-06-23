{{/*
ModelGovernor Helm chart helpers
*/}}
{{- define "modelgovernor.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "modelgovernor.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "modelgovernor.namespace" -}}
{{- .Values.global.namespace }}
{{- end }}

{{- define "modelgovernor.labels" -}}
helm.sh/chart: {{ include "modelgovernor.name" . }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "modelgovernor.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- range $k, $v := .Values.global.labels }}
{{ $k }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{- define "modelgovernor.selectorLabels" -}}
app.kubernetes.io/name: {{ include "modelgovernor.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "modelgovernor.secretName" -}}
{{- .Values.secrets.name }}
{{- end }}

{{- define "modelgovernor.image" -}}
{{- $img := index .Values.images .imageKey -}}
{{- printf "%s:%s" $img.repository $img.tag }}
{{- end }}

{{- define "modelgovernor.syncWave" -}}
{{- if .wave }}
argocd.argoproj.io/sync-wave: {{ .wave | quote }}
{{- end }}
{{- end }}

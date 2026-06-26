{{/* Finance Governor Helm helpers */}}
{{- define "financegovernor.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "financegovernor.namespace" -}}
{{- .Values.global.namespace }}
{{- end }}

{{- define "financegovernor.labels" -}}
helm.sh/chart: {{ include "financegovernor.name" . }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "financegovernor.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- range $k, $v := .Values.global.labels }}
{{ $k }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{- define "financegovernor.secretName" -}}
{{- .Values.secrets.name }}
{{- end }}

{{- define "fg.namespace" -}}
{{ .Values.namespace }}
{{- end }}

{{- define "fg.labels" -}}
app.kubernetes.io/name: finance-governor
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "fg.namespace" -}}
{{- default "finance-governor" .Values.namespace }}
{{- end }}

{{- define "fg.labels" -}}
app.kubernetes.io/name: finance-governor
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "fg.secretName" -}}
{{- default "fg-internal" .Values.secrets.name }}
{{- end }}

{{- define "fg.configMapName" -}}
fg-config
{{- end }}

{{- define "fg.databaseUrl" -}}
{{- printf "postgresql+psycopg://%s:%s@fg-postgres:5432/%s" .Values.postgres.user .Values.postgres.password .Values.postgres.database }}
{{- end }}

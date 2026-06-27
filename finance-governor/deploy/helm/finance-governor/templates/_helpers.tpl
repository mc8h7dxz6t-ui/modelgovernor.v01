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

{{- define "fg.databaseHost" -}}
{{- if .Values.pgbouncer.enabled }}fg-pgbouncer{{- else if .Values.postgres.external.enabled }}{{ .Values.postgres.external.host }}{{- else }}fg-postgres{{- end }}
{{- end }}

{{- define "fg.databasePort" -}}
{{- if .Values.pgbouncer.enabled }}6432{{- else if .Values.postgres.external.enabled }}{{ .Values.postgres.external.port }}{{- else }}5432{{- end }}
{{- end }}

{{- define "fg.postgresBackendHost" -}}
{{- if .Values.postgres.external.enabled }}{{ .Values.postgres.external.host }}{{- else }}fg-postgres{{- end }}
{{- end }}

{{- define "fg.postgresBackendPort" -}}
{{- if .Values.postgres.external.enabled }}{{ .Values.postgres.external.port }}{{- else }}5432{{- end }}
{{- end }}

{{- define "fg.databaseUrl" -}}
{{- printf "postgresql+psycopg://%s:%s@%s:%s/%s" .Values.postgres.user .Values.postgres.password (include "fg.databaseHost" .) (include "fg.databasePort" . | toString) .Values.postgres.database }}
{{- end }}

{{- define "fg.redisHost" -}}
{{- if .Values.redis.sentinel.enabled }}fg-redis-master{{- else }}fg-redis{{- end }}
{{- end }}

{{- define "fg.redisUrl" -}}
{{- printf "redis://%s:6379/0" (include "fg.redisHost" .) }}
{{- end }}

{{- define "fg.podAntiAffinity" -}}
{{- if .Values.enterprise.podAntiAffinity }}
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/name: finance-governor
            app.kubernetes.io/instance: {{ .Release.Name }}
        topologyKey: kubernetes.io/hostname
{{- end }}
{{- end }}

{{- define "fg.platformEnv" -}}
- name: FG_SPINE_ENABLED
  value: {{ .Values.platforms.spineEnabled | quote }}
- name: FG_SIDECAR_URL
  value: http://fg-sidecar:8091
- name: FG_INTERNAL_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ include "fg.secretName" . }}
      key: fg-internal-tokens
- name: POSTGRES_USER
  value: {{ .Values.postgres.user | quote }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "fg.secretName" . }}
      key: postgres-password
- name: DATABASE_URL
  value: postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@{{ include "fg.databaseHost" . }}:{{ include "fg.databasePort" . }}/{{ .Values.postgres.database }}
{{- end }}

{{- define "fg.istioPodAnnotations" -}}
{{- if .Values.istio.enabled }}
sidecar.istio.io/inject: "true"
{{- if .Values.istio.holdApplicationUntilProxyStarts }}
proxy.istio.io/config: '{ "holdApplicationUntilProxyStarts": true }'
{{- end }}
{{- end }}
{{- end }}

{{- define "fg.creditGovernRailEnv" -}}
- name: FG_CREDIT_RAIL_MODE
  value: {{ .Values.platforms.creditgovern.rail.mode | default "auto" | quote }}
- name: FG_CREDIT_RAIL_URL
  value: {{ .Values.platforms.creditgovern.rail.url | default "" | quote }}
- name: FG_CREDIT_RAIL_TIMEOUT
  value: {{ .Values.platforms.creditgovern.rail.timeout | default "10" | quote }}
- name: FG_CREDIT_RAIL_CIRCUIT_THRESHOLD
  value: {{ .Values.platforms.creditgovern.rail.circuitThreshold | default "5" | quote }}
{{- end }}

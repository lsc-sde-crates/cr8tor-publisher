{{/*
the name to be used by the publisher service
*/}}
{{- define "approval.name" -}}
{{- printf "%s-approval" .Release.Name }}
{{- end }}

{{/*
the name to be used by the publisher service
*/}}
{{- define "publisher.name" -}}
{{- printf "%s-publisher" .Release.Name }}
{{- end }}

{{/*
the name to be used by the metadata service
*/}}
{{- define "metadata.name" -}}
{{- printf "%s-metadata" .Release.Name }}
{{- end }}

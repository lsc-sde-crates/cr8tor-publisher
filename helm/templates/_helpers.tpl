{{/*
the name to be used by the publisher service
*/}}
{{- define "approval.name" -}}
{{- printf "%s-approval" .Release.Name }}
{{- end }}

{{/*
the name to be used by the publisher service
*/}}
{{- define "publish.name" -}}
{{- printf "%s-publish" .Release.Name }}
{{- end }}

{{/*
the name to be used by the metadata service
*/}}
{{- define "metadata.name" -}}
{{- printf "%s-metadata" .Release.Name }}
{{- end }}


{{/*
the name of pvc's internally
*/}}
{{- define "inline.volume.name" -}}
{{- printf "%s-%s-inline" .org .pvc }}
{{- end }}
{{/*
the name of pvc's internally
*/}}
{{- define "inline.volume.mountPath" -}}
{{- printf "%s/%s" .mountPath .pvc }}
{{- end }}

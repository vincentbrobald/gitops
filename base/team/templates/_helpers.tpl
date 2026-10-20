{{- define "team.ns" -}}team-{{ required "team is required" .Values.team }}{{- end -}}
{{- define "team.host" -}}argocd-{{ .Values.team }}.{{ required "appsDomain is required" .Values.appsDomain }}{{- end -}}
{{- define "team.client" -}}argocd-{{ required "cluster is required" .Values.cluster }}-team-{{ .Values.team }}{{- end -}}
{{- define "team.tektonHost" -}}tekton-{{ .Values.team }}.{{ required "appsDomain is required" .Values.appsDomain }}{{- end -}}
{{- define "team.tektonClient" -}}tekton-{{ required "cluster is required" .Values.cluster }}-team-{{ .Values.team }}{{- end -}}
{{- define "team.crossplane" -}}
providerConfigRef: {kind: ClusterProviderConfig, name: default}
{{- end -}}
{{- define "team.repos" -}}
{{- $repos := list (printf "%s-gitops" .Values.team) }}
{{- range .Values.repositories }}
{{- if not (hasPrefix (printf "%s-" $.Values.team) .) }}{{ fail (printf "repository %q: must start with %s-" . $.Values.team) }}{{ end }}
{{- $repos = append $repos . }}
{{- end }}
{{- toJson $repos }}
{{- end -}}

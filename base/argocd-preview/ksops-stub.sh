#!/bin/bash
# ksops stand-in for the render-only Argo CD (argocd-preview): never decrypts.
#
# Same interface as ksops (a kustomize exec KRM function): reads a
# ResourceList whose functionConfig is the ksops generator, and returns the
# Secrets of the files it lists. Each value is replaced by a fingerprint of
# its ciphertext, so the rendered tree keeps every Secret and key name, and a
# diff shows which keys changed, but no value ever leaves the encrypted file.
# Argo CD's API masks Secret values in what it returns, so the fingerprints
# are also in the annotation preview.argocd/fingerprints (key: fingerprint).
# Note: sops re-encrypts every value of a file it edits, so an edited file
# shows all its keys as changed.
set -euo pipefail
YQ=${YQ:-/usr/local/bin/yq}

redact() {  # redact <file>: the Secret, values replaced, sops metadata dropped
    local file=$1 doc field key fp fps=""
    doc=$("$YQ" 'del(.sops)' "$file")
    for field in data stringData; do
        while IFS= read -r key; do
            [ -n "$key" ] || continue
            fp=$(K=$key F=$field "$YQ" '.[strenv(F)][strenv(K)]' "$file" | sha256sum | cut -c1-16)
            fps+="$key: $fp"$'\n'
            if [ "$field" = data ]; then   # data holds base64
                fp=$(printf 'REDACTED sha256:%s' "$fp" | base64 -w0)
            else
                fp="REDACTED sha256:$fp"
            fi
            doc=$(printf '%s\n' "$doc" | K=$key F=$field V=$fp "$YQ" '.[strenv(F)][strenv(K)] = strenv(V)')
        done < <(F=$field "$YQ" '.[strenv(F)] // {} | keys | .[]' "$file")
    done
    printf '%s\n' "$doc" | FPS=$fps "$YQ" '.metadata.annotations."preview.argocd/redacted" = "true"
        | .metadata.annotations."preview.argocd/fingerprints" = strenv(FPS)'
}

config=$(cat)
echo "apiVersion: config.kubernetes.io/v1"
echo "kind: ResourceList"
echo "items:"
while IFS= read -r file; do
    [ -n "$file" ] || continue
    redact "$file" | sed 's/^/  /; 1s/^  /- /'
done < <(printf '%s\n' "$config" | "$YQ" '.functionConfig.files // [] | .[]')

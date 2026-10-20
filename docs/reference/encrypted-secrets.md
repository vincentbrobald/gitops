# Encrypted Secrets

> Reference · [Documentation](../../README.md#documentation)

Every Secret in this repository is a SOPS-encrypted file (`*.enc.yaml`),
decrypted by KSOPS when Argo CD renders its folder: each folder lists its
files in `secret-generator.yaml`. They're encrypted for the age keys of the
folder's `.sops.yaml`: the cluster's own key and the admin key. A copy of this
repository for another site keeps the generators and makes its own files,
encrypted for its own keys (see
[Edit an encrypted Secret](../how-to/edit-an-encrypted-secret.md)).

| Who encrypts for whom | File | Written by |
|---|---|---|
| `clusters/<cluster>/` | `.sops.yaml` | `deploy-talos.py`, from the cluster file |
| `applications/` (the teams') | `.sops.yaml` | by hand: the same keys as the clusters that run the teams |

## The Secrets

| File | Secret | Keys | Made by |
|---|---|---|---|
| `applications/<org>/<team>/argocd/repo-credentials.enc.yaml` | `team-<team>/repo-creds-<team>` | Argo CD credential template | `tools/teams.py` ([Team files](team-files.md)) |
| `applications/<org>/<team>/argocd/ci-bot.enc.yaml`, `ci-webhook.enc.yaml`, `ci-webhook-pac.enc.yaml` | `team-<team>/forgejo-bot`, `team-<team>/forgejo-webhook`, `ci-<team>/pac-webhook` | the CI user's password, the webhooks' secret | `tools/teams.py` |
| `applications/<org>/<team>/argocd/tekton-dashboard.enc.yaml` | `team-<team>/tekton-dashboard-oauth2-proxy` | `cookie-secret` | `tools/teams.py` |
| `clusters/<cluster>/generated/<topic>/secret-*.enc.yaml` | the add-ons' (Argo CD and Headlamp OIDC, Grafana, Talos backups) | | `deploy-talos.py`, from the cluster file |
| `clusters/<cluster>/crossplane/secret-crossplane-system-keycloak-credentials.enc.yaml` | `crossplane-system/keycloak-credentials` | `client_id`, `client_secret`, `url`, `realm`, `keycloak_version` | by hand: Keycloak's client for Crossplane (infra) |
| `clusters/<cluster>/crossplane/secret-crossplane-system-forgejo-credentials.enc.yaml` | `crossplane-system/forgejo-credentials` | `api_token`, `host` | by hand: the token of Forgejo's user for Crossplane (infra) |
| `clusters/<cluster>/crossplane/secret-crossplane-system-harbor-credentials.enc.yaml` | `crossplane-system/harbor-credentials` | `username`, `password`, `credentials` | by hand: Harbor's admin (infra) |
| `clusters/<cluster>/crossplane/secret-crossplane-system-artifact-keeper-credentials.enc.yaml` | `crossplane-system/artifact-keeper-credentials` | `url`, `token` | by hand: Artifact Keeper's API token (infra) |
| `clusters/<cluster>/argocd-preview/secret-argocd-preview-creds-forgejo.enc.yaml` | `argocd-preview/creds-forgejo` | `url`, `type`, `sshPrivateKey` | by hand: a read-only deploy key of this repository ([Merge checks](merge-checks.md)) |
| `clusters/<cluster>/tekton/dashboard/secret-tekton-dashboard-oauth2-proxy.enc.yaml` | `tekton-dashboard/oauth2-proxy` | `cookie-secret` | by hand: random |
| `clusters/<cluster>/ci/<name>/*.enc.yaml` | the platform CI repositories' | | `tools/ci.py` ([Platform CI repositories](ci-repository.md)) |
| `clusters/<cluster>/ci/provider-*/dockerhub-push.enc.yaml` | `provider-*/dockerhub-push` | `username`, `token` | by hand: a Docker Hub access token (the providers' public images) |

The infra playbooks take Keycloak's client secret, the Forgejo token and
Harbor's admin password from these Secrets when they exist (their lookup
`site_secret`: a Secret here wins over the file in the secrets tree), so the
services and Crossplane agree.

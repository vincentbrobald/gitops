# Tools

> Reference · [Documentation](../../README.md#documentation)

The scripts that check this repository's layout and write its generated
files. The merge check runs each `check` ([Merge checks](merge-checks.md)).

| Script | `check` | `generate` |
|---|---|---|
| `tools/teams.py` | validates the tree `applications/` (the files' content: the charts' schemas); fails if a generated file is stale | writes `<org>/<team>/argocd/` and `clusters/<cluster>/addons/projects/tenants.yaml`; makes missing keys and Secrets |
| `tools/ci.py` | checks `clusters/<cluster>/ci/` (the files' content: the chart's schema); fails if a generated file is stale | writes each folder's `kustomization.yaml` and `secret-generator.yaml`; makes missing Secrets |
| `tools/generated.py` | compares `addons/generated/` and `generated/` with `generated/CHECKSUMS` | (none: deploy-talos.py writes those) |

## Who runs `generate`

The merge check does: a pull request that adds a team, an environment or a CI
repository without its generated files gets them committed to its branch by
pac-bot (step `generate` of the [merge checks](merge-checks.md)), made by the
target branch's scripts. Running `generate` yourself is optional, and
required only for a pull request that changes `tools/` itself.

## What `generate` needs

Encrypting needs only the recipients' public keys (`.sops.yaml`); no private
key, except in the case below.

| Script | Needs |
|---|---|
| `tools/teams.py` | `ssh-keygen`, `sops` (`SOPS=<path>` if not on `PATH`) |
| `tools/ci.py` | `sops`; `PAC_BOT_TOKEN_FILE` (default `/root/lab/lab-secrets/forgejo/pac-bot-token`); a private key (`SOPS_AGE_KEY_FILE`) only to add `forgejo:` to a repository whose `forgejo-pac.enc.yaml` exists already (its webhook secret is copied) |

| Variable | Meaning |
|---|---|
| `GITOPS_ROOT` | the checkout to work on (default: the script's own); the merge check runs the target branch's scripts on the pull request's files |

```sh
SOPS=~/.cache/talos/v1.14.2/sops-v3.13.3 python3 tools/teams.py generate
```

## Validation in the charts

The content of `organization.yaml`, `team.yaml` and `repository.yaml` (keys,
formats, required values, no unknown key) is validated by the charts that
render them: `values.schema.json` in `base/organization`, `base/team`,
`base/ci-repository`. Helm refuses invalid values, so the merge check's render
fails with the key at fault. The scripts check what no chart sees: the tree.

## Checks of `tools/teams.py`

Directory names and their limits ([Team files](team-files.md#names)); every
organization has an `organization.yaml`, every team a `team.yaml`; the
repositories listed (they get deploy keys); a namespace's
directory has `base/` and `env/<env>/` only, and each environment's
`kustomization.yaml` is an overlay of `../../base`; listeners in the base count
once per environment; ListenerSet host names start with `<team>-` and are unique;
`repo-credentials.enc.yaml` and `deploy-keys.yaml` go together; a team
marked `removed: true` has no `argocd/` (`generate` deletes it); a team folder
deleted while the target branch (`GITOPS_BASE`, default `origin/main`) doesn't
have `removed: true` in its `team.yaml`; nothing but
generated files in `argocd/`; the teams' Argo CDs know the same Forgejo SSH
host key as the platform's (`base/team/argocd-values.yaml` against
`clusters/<cluster>/addons/generated/argocd.yaml`).

## Checks of `tools/ci.py`

Namespaces unique across repositories; the required Secrets exist; nothing
but `repository.yaml`, `*.enc.yaml` and generated files in the folder.

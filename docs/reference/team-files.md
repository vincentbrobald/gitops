# Team files

> Reference · [Documentation](../../README.md#documentation)

The files under `applications/` that describe organizations, teams and their
namespaces, and the Applications each one becomes. To add one:
[Add a team](../how-to/add-a-team.md), [Add an environment](../how-to/add-an-environment.md).
What a team then gets: [What a team gets](team-resources.md).

## Tree

| Path | Describes | Application(s) |
|---|---|---|
| `applications/<org>/organization.yaml` | a Forgejo organization | `org-<org>` (chart `base/organization`, namespace `org-<org>`) |
| `applications/<org>/<team>/team.yaml` | a team | `team-<team>` (core), `team-<team>-ci`, `team-<team>-packages` (chart `base/team`), `team-<team>-argocd` (the team's Argo CD) |
| `applications/<org>/<team>/argocd/` | generated, never edit | (synced by `team-<team>`) |
| `applications/<org>/<team>/<ns>/base/kustomization.yaml` | the base of namespace `<ns>`, shared by its environments (includes `base/team-namespace`) | |
| `applications/<org>/<team>/<ns>/env/<env>/kustomization.yaml` | an environment: an overlay of `../../base` | `ns-<env>-<team>-<ns>`, namespace `<env>-<team>-<ns>` |

## Names

| Name | Rule |
|---|---|
| organization | lower-case DNS label, at most 30 characters |
| team | lower-case DNS label, at most 20 characters, unique across organizations; not `library`, `providers`, `gitops-scanner`, `pac-demo` (the platform's Harbor projects) |
| namespace `<ns>` | lower-case DNS label, at most 30 characters; `argocd` is reserved |
| environment `<env>` | lower-case letters and digits, at most 8, starting with a letter |
| `<env>-<team>-<ns>` | at most 63 characters |
| repository | starts with `<team>-`; `<team>-gitops` always exists and isn't listed |
| listener host name | first label starts with `<team>-`, unique across the site |

## `organization.yaml`

Validated by `base/organization/values.schema.json`: an unknown key, a
missing realm or a bad visibility fails the merge check's render.

| Key | Description |
|---|---|
| `forgejo.fullName` | the organization's display name |
| `forgejo.description` | its description |
| `forgejo.visibility` | `public`, `limited` (signed-in users) or `private` |
| `keycloak.realm` | the Keycloak realm of its users: its teams' groups are made there, its teams' Argo CDs log in through it |
| `owners` | Forgejo user names added to the organization's team Owners |

## `team.yaml`

Passed to the chart as a values file and validated by
`base/team/values.schema.json`: an unknown or mistyped key fails the merge
check's render.

| Key | Description |
|---|---|
| `description` | the team's description (Forgejo team, Keycloak group) |
| `members` | Keycloak user names, the same in Forgejo |
| `repositories` | repositories besides `<team>-gitops`, each `<team>-...`; may be `[]` |
| `removed` | `true`: step 1 of removing the team. Its Applications go; the folder stays until step 2 ([Remove a team](../how-to/remove-a-team-or-environment.md#a-team)) |

## Generated files

Written by `python3 tools/teams.py generate` ([tools](tools.md)):

| File | Content | Made |
|---|---|---|
| `<team>/argocd/argocd-namespaces.yaml` | the namespaces the team's Argo CD may use: `team-<team>` and its environments | every run |
| `<team>/argocd/deploy-keys.yaml` | a read-only deploy key on each team repository (Crossplane) | with a new key |
| `<team>/argocd/repo-credentials.enc.yaml` | the key's private half: an Argo CD credential template for `<org>/<team>-*` | once; delete with `deploy-keys.yaml` for a new key |
| `<team>/argocd/ci-bot.enc.yaml` | the password of Forgejo user `ci-<team>` (Secret `forgejo-bot`) | once |
| `<team>/argocd/ci-webhook.enc.yaml`, `ci-webhook-pac.enc.yaml` | the webhooks' secret, for Forgejo and for Pipelines-as-Code | once; delete the three CI files to replace them |
| `<team>/argocd/tekton-dashboard.enc.yaml` | the cookie secret of the team Dashboard's oauth2-proxy | once; deleting it signs everyone out |
| `<team>/argocd/kustomization.yaml`, `secret-generator.yaml` | how the folder is built (KSOPS) | every run |
| `clusters/<cluster>/addons/projects/tenants.yaml` | the AppProject `tenants`: every namespace of the tree | every run |

The encrypted files are SOPS-encrypted for the cluster (`applications/.sops.yaml`).
For a team with `removed: true`, `generate` deletes its `argocd/` folder;
its namespaces stay in `tenants.yaml` until the team's folder is deleted.

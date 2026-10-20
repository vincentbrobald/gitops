# Crossplane providers

> Reference · [Documentation](../../README.md#documentation)

Which external objects Crossplane manages from this repository, with which
provider and credential. The conventions behind them:
[Crossplane](../explanation/crossplane.md).

| Provider | Manages | Signs in as |
|---|---|---|
| provider-keycloak (crossplane-contrib) | realm example: clients and their groups claims (Tekton Dashboard, Headlamp, Grafana, Harbor, Artifact Keeper, the teams' Argo CDs and Dashboards), the group `grafana-admins`, the teams' groups and memberships | `crossplane-lab` (realm master): `manage-clients`, `manage-users`, `view-users` of realm example. Its Secret's `keycloak_version` must follow Keycloak upgrades |
| provider-forgejo (ours, `alice/provider-forgejo`: Upjet, the Forgejo Terraform provider compiled in) | the platform CI repositories' collaborators, webhooks and deploy keys; organizations, teams, their repositories, the teams' CI users and tokens | `crossplane-lab`, a Forgejo site admin, bounded by the admission policies `forgejo-users` and `team-forgejo` |
| provider-upjet-harbor (crossplane-contrib) | Harbor: its Keycloak login, proxy caches, the platform's and the teams' projects, the CI robots | Harbor's admin |
| provider-artifact-keeper (ours, `alice/provider-artifact-keeper`) | Artifact Keeper: its OIDC login, the shared caches, the teams' repositories, permissions, CI accounts and tokens | an admin API token `crossplane-lab` |

## Packages and API groups

| Provider object | Package | Kinds in |
|---|---|---|
| `provider-keycloak` | `xpkg.crossplane.io/crossplane-contrib/provider-keycloak` | `*.keycloak.m.crossplane.io` |
| `forgejo` | `registry.example.org/providers/forgejo` | `*.forgejo.m.crossplane.brobald.be` |
| `provider-harbor` | `ghcr.io/crossplane-contrib/provider-upjet-harbor` | `*.harbor.m.crossplane.io` |
| `artifact-keeper` | `registry.example.org/providers/artifact-keeper` | `artifactkeeper.crossplane.brobald.be` |

Versions: `clusters/lab/crossplane/`. Our providers' groups are under
`brobald.be`, the owner's public domain, so that no site name reaches the
published copy of the lab.

## Where the objects are

| Objects | Path |
|---|---|
| providers, their credentials (SOPS), the activation policy | `clusters/lab/crossplane/` (Application `crossplane-providers`) |
| Crossplane itself | chart, `clusters/lab/addons/crossplane.yaml` |
| the Tekton Dashboard's Keycloak client | `clusters/lab/tekton/dashboard/keycloak-client.yaml` |
| Headlamp's and Grafana's clients, `grafana-admins` | `generated/headlamp/`, `generated/monitoring/` (deploy-talos.py, `oidc.crossplane` in the cluster file) |
| Harbor's settings: registries, projects, its Keycloak client | `clusters/lab/registries/harbor/` |
| Artifact Keeper's settings: its Keycloak client, OIDC, shared caches | `clusters/lab/registries/artifact-keeper/` |
| CI repositories' Forgejo settings and Harbor robots | `base/ci-repository` with `clusters/lab/ci/<name>/repository.yaml` |
| each team's objects | chart `base/team` |
| each organization | chart `base/organization` |

## Credentials

| Secret (`crossplane-system`) | Provider |
|---|---|
| `keycloak-credentials` | provider-keycloak (flat keys `client_id`, `client_secret`, `url`, `realm`, `keycloak_version`) |
| `forgejo-credentials` | provider-forgejo |
| `harbor-credentials` | provider-upjet-harbor |
| `artifact-keeper-credentials` | provider-artifact-keeper |

## Provider configs

| ClusterProviderConfig | Used by |
|---|---|
| `default` (each provider) | every managed resource that names none |
| `ci-<team>` (provider-forgejo) | the team's own CI objects: Crossplane signs in as user `ci-<team>` |

## Installed kinds

Only the kinds listed in `clusters/lab/crossplane/activation.yaml` (a
ManagedResourceActivationPolicy) are installed. To add one:
[Add a Crossplane kind](../how-to/add-a-crossplane-kind.md).

Undo procedures for objects taken over from Ansible: infra's
[Hand an object back to Ansible](https://github.com/vincentbrobald/infra/blob/main/docs/how-to/hand-back-to-ansible.md).

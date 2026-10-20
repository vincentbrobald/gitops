# What a team gets

> Reference · [Documentation](../../README.md#documentation)

Everything the platform makes for a team from its `team.yaml`, by
Application. The files: [Team files](team-files.md). Why it is split and
bounded this way: [Multi-tenancy](../explanation/multi-tenancy.md).

## `team-<team>` (core)

| Where | Object |
|---|---|
| cluster | namespace `team-<team>`: ResourceQuota, LimitRange, Pod Security `restricted`, `view` for the members, label `gateway.example.org/listeners=ingress` |
| Keycloak (the organization's realm) | group `team-<team>` and its members (authoritative: a member added in Keycloak's console is removed) |
| Keycloak | client `argocd-lab-team-<team>` (public, PKCE) of the team's Argo CD |
| Forgejo | team `<team>` in the organization: write access to its repositories, may create repositories; its members |
| Forgejo | repositories `<org>/<team>-gitops` and those listed: private, created with a README, never deleted by Crossplane |
| Forgejo | a read-only deploy key on each, for the team's Argo CD |
| team's Argo CD | Application `root`, syncing `apps/` of `<team>-gitops` (`*.yaml`, `*.yml`, recursively) |
| cluster | the generated Secrets of `argocd/` ([team files](team-files.md#generated-files)) |

## `team-<team>-argocd`

| Property | Value |
|---|---|
| Install | Argo CD chart in `team-<team>`, namespace-scoped (`base/team/argocd-values.yaml`) |
| UI | `https://argocd-<team>.apps.lab.example.org`, on a ListenerSet of its own |
| Login | Keycloak only; admins: the team's group and `argocd-admins` |
| Destinations | `team-<team>` (its Applications) and the team's environment namespaces, nothing else |
| Repositories | `ssh://git@forgejo.example.org:2222/<org>/<team>-*` (the credential template) |
| Project | its own `default` |

## `team-<team>-ci`

| Where | Object |
|---|---|
| cluster | namespace `ci-<team>`: Pod Security `baseline`, quota 2 CPU and 4 GiB requested, 8 GiB memory limit, 10 pods; `view` for the members |
| Forgejo | user `ci-<team>`, member of the team (Crossplane, password from `ci-bot.enc.yaml`) |
| cluster | ClusterProviderConfig `ci-<team>`: Crossplane signs in to Forgejo as `ci-<team>` |
| Forgejo | a token of `ci-<team>` for Pipelines-as-Code (Secret `forgejo-token` in `ci-<team>`) |
| Forgejo | a webhook to Pipelines-as-Code on each team repository |
| cluster | a Pipelines-as-Code `Repository` per team repository in `ci-<team>` (policy: pull requests run for the team's members) |
| cluster | the team's Tekton Dashboard in `team-<team>`: read-only, tenant mode, reads `ci-<team>` only, at `https://tekton-<team>.apps.lab.example.org` |
| Keycloak | client `tekton-lab-team-<team>` of the Dashboard's oauth2-proxy (admits the group `team-<team>`) |

## `team-<team>-packages`

| Where | Object |
|---|---|
| Harbor | project `<team>`: images at `registry.example.org/<team>/<image>`, public for pulls, Trivy scan on push, 20 GB quota, never deleted by Crossplane |
| Harbor | group `team-<team>` as maintainer: members push with their own login |
| Harbor | robot `robot$<team>+<team>-ci` (push and pull in `<team>`); its secret in Secret `harbor-push` of `ci-<team>`, readable by the members |
| Artifact Keeper | hosted repositories `<team>-maven`, `<team>-npm`, `<team>-pypi`, `<team>-generic` (never deleted) |
| Artifact Keeper | virtual repositories `<team>-<format>-all`: the hosted one, then the shared cache of Maven Central, npmjs or PyPI |
| Artifact Keeper | read/write for the group `team-<team>` (waits until the group's first member logs in) |
| Artifact Keeper | service account `svc-ci-<team>` and its token, restricted to the team's repositories, in Secret `artifact-keeper-push` of `ci-<team>` (keys `token`, `username`) |

## `org-<org>`

| Where | Object |
|---|---|
| Forgejo | the organization (Crossplane's user `crossplane-lab` its first owner; never deleted) |
| Forgejo | `owners` in its team Owners |

## When a team is removed

In two steps ([Remove a team](../how-to/remove-a-team-or-environment.md#a-team)):

| Goes | Stays (no `Delete`; remove by hand if needed) |
|---|---|
| the team's Applications and their objects; memberships; deploy keys; the CI user, its token, the webhooks; the Dashboard; Artifact Keeper permissions, service account and token; then namespaces `team-<team>`, `ci-<team>` (namespace cleanup) and the environments' | the Keycloak group and clients, the Forgejo team and repositories, the Harbor project, the Artifact Keeper hosted repositories |

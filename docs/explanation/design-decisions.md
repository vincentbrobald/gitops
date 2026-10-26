# Design decisions

> Explanation · [Documentation](../../README.md#documentation)

The choices the platform is built on, what else was considered, and when to
look at them again. Each entry links to the page that explains it in depth.
Pages in other repositories are named by repository and path.

Every project of the platform has a page like this one for its own choices:

| Project | Page |
|---|---|
| gitops (this repository) | platform-wide: Argo CD, teams, secrets, Crossplane, site services |
| [talos-install](https://github.com/vincentbrobald/talos-install/blob/main/docs/explanation/design-decisions.md) | Talos, libvirt, the script, networks, upgrades, add-ons |
| [infra](https://github.com/vincentbrobald/infra/blob/main/docs/explanation/design-decisions.md) | VMs, Ansible, CA, Keycloak, Forgejo, S3, DNS |
| [gitops-scanner](https://github.com/vincentbrobald/gitops-scanner/blob/main/docs/explanation/design-decisions.md) | rendering with Argo CD, the preview, the checks |
| [provider-forgejo](https://github.com/vincentbrobald/provider-forgejo/blob/main/docs/explanation/design-decisions.md) | Upjet, the vendored Terraform provider |
| [provider-artifact-keeper](https://github.com/vincentbrobald/provider-artifact-keeper/blob/main/docs/explanation/design-decisions.md) | a provider written by hand |
| [lb](https://github.com/vincentbrobald/lb/blob/main/docs/explanation/design-decisions.md) | SNI passthrough, why it isn't running |
| [pac-demo](https://github.com/vincentbrobald/pac-demo/blob/main/docs/explanation/design-decisions.md) | the smallest pipeline |

## Principles

- **Open source, and as little foreign tooling as possible.** Open-source
  components are preferred; where a Terraform provider is the only existing
  integration, it is compiled into a Crossplane provider rather than run
  through Terraform or OpenTofu.
- **Versions at least 14 days old.** A pinned release must have been
  published at least 14 days before it is adopted, unless it fixes a security
  issue. Release dates are noted next to the pins for that reason.
- **Git is the interface.** A change to what runs on the clusters, or to what
  lives inside the site's services, is a pull request here; nothing needs a
  script run by hand afterwards.

## Repository and Argo CD

### Several clusters, one repository, site objects managed once

**Decision.** Every cluster has its own folder and Argo CD; what manages site
objects (Crossplane, the teams, CI, the merge checks) runs on `lab` only.
**Why.** Two Crossplanes managing the same Keycloak client or Forgejo team
would overwrite each other; the teams' site objects must be made once.
**Cost.** Teams use one cluster; giving them a second one is a design change.
**Revisit if** teams need environments on several clusters.
See [Several clusters](several-clusters.md).

### One root Application per cluster

**Decision.** Each cluster folder has a single root, the app-of-apps
`addons`, which syncs `clusters/<name>/addons/` recursively and lists itself.
**Why.** The repository alone holds the cluster's whole Argo CD view; a
rebuilt Argo CD finds everything from one Application.
**Alternatives.** deploy-talos.py's separate root Application (still
available, `argocd.application.enabled`): two roots to reason about.
**Revisit if** a cluster needs content synced from another repository as its
root. See [Architecture](architecture.md).

### Two writers, with checksums

**Decision.** deploy-talos.py writes the add-ons it knows about
(`addons/generated/`, `generated/`) and pushes them to `main` itself;
everything else goes through pull requests. `generated/CHECKSUMS` and
`tools/generated.py` make hand edits of its files fail the merge check.
**Why.** deploy-talos.py knows the cluster's shape (addresses, host names,
OIDC clients) because it built the cluster; the cluster file stays the single
source for it.
**Alternatives.** Argo CD's Source Hydrator (rendered manifests on a
branch of their own); deploy-talos.py writing to a separate repository;
Forgejo's protected file patterns. All need deploy-talos.py restructured, or
their behaviour with deploy keys checked; the checksum check is 62 lines that
work.
**Revisit if** the Source Hydrator matures, or deploy-talos.py's rendering
moves into a chart. See [Architecture](architecture.md#two-writers).

### Render before merge

**Decision.** Every pull request is rendered before and after by Argo CD's
own code at the clusters' version (gitops-scanner), and errors block the
merge.
**Why.** Changes break where they are rendered, not where they are written:
a chart value or generator template breaks an Application elsewhere.
**Alternatives.** Linting and schema checks only (miss render failures);
`argocd app diff` against the live cluster (needs cluster access from CI,
and only shows existing Applications).
**Revisit if** Argo CD gains a supported offline render of a whole
app-of-apps tree. See [Rendering before merging](merge-checks.md).

### Releases kept in Git

**Decision.** Upstream release manifests that this repository deploys by hand
(Tekton Pipelines, Pipelines-as-Code, the Tekton Dashboard) are copied into
`base/` unchanged, with their source URL and checksum in the kustomization;
site changes are kustomize patches on top.
**Why.** A remote kustomize resource is downloaded at every render, by Argo
CD and by the merge check: a GitHub outage breaks both, and nothing verifies
the file. In Git, a render needs nothing outside the site, the file is the
one whose checksum matched upstream's, and an upgrade shows in the merge
check's diff.
**Alternatives.** Remote URLs (what this replaced); Helm charts from an OCI
registry mirrored by Harbor (none is published for Pipelines-as-Code or the
Dashboard).
**Cost.** About 1.7 MB of YAML in Git, and an upgrade is a download plus a
checksum comparison ([Upgrade Tekton](../how-to/upgrade-tekton.md)).
**Revisit if** the releases ship as charts or OCI artifacts the site can
mirror. deploy-talos.py's Gateway API CRDs are still a remote URL
(`generated/gateway-api/`).

### Restricted AppProjects with explicit lists

**Decision.** Every Application is in a project that limits sources,
destinations and kinds; `default` is narrowed to the root; the `tenants`
project lists every namespace of the tree, generated by `tools/teams.py`.
**Why.** A bad `team.yaml` or chart change must not reach cluster-scoped
objects or other namespaces.
**Alternatives.** Globs: impossible with environment namespaces named
`<env>-<team>-<ns>` (next entry). Argo CD sync impersonation
(`destinationServiceAccounts`), bounding syncs by Kubernetes RBAC instead of
lists: still behind a feature flag in Argo CD 3.x.
**Revisit if** impersonation becomes stable. See [Bounded Applications](projects.md).

## Teams

### Teams as data, rendered by ApplicationSets

**Decision.** Organizations, teams and environments are YAML files under
`applications/`; ApplicationSets turn them into Applications.
**Why.** A new team is a small reviewable file, and every team looks the
same.
**Alternatives.** One hand-written Application per team (drifts apart);
a controller of our own (more code to own).
See [Multi-tenancy](multi-tenancy.md).

### Helm charts for the per-team objects

**Decision.** `base/team`, `base/organization` and `base/ci-repository` are
Helm charts rendered by Argo CD from this repository (not published).
**Why.** One data file becomes many objects: one Forgejo `Repository`,
`TeamRepository`, `DeployKey`, `Webhook` and PaC `Repository` per team
repository, one `TeamMember` per member. Kustomize can't loop over a list, and
each chart validates its input with a `values.schema.json` (the data files are
passed as values files, so an unknown key is refused too).
**Alternatives.** Kustomize bases filled by ApplicationSet patches: works for
the one-per-team objects; data lists would need one Application per team
repository (a matrix generator with `elementsYaml`), list fields in the
providers (members, owners), and the charts' validation would move to
`tools/teams.py` and the admission policies.
**Revisit if** a single templating mechanism becomes a goal; `base/organization`
(one object and its owners) is the easiest to convert first.

### Environment namespaces named `<env>-<team>-<ns>`

**Decision.** An environment `dev` of namespace `hello` of team `platform` is
`dev-platform-hello`.
**Consequence.** No glob selects one team's namespaces, so they are listed:
`argocd-namespaces.yaml` per team and the `tenants` project, both generated.
**Alternatives.** `<team>-<ns>-<env>` with dash-free team names would allow
`<team>-*` globs in projects; each team's namespace-scoped Argo CD would still
need an explicit list. Renaming means migrating every environment.
**Revisit with** the next entry.

### A namespace-scoped Argo CD per team

**Decision.** Each team gets its own Argo CD in `team-<team>`, which deploys
only to the team's namespaces and reads only its repositories.
**Why.** A mistake in a team's repository stays inside its bounds; the
platform's Argo CD holds no team content; teams get the full UI on what is
theirs.
**Alternatives.** One shared Argo CD with "apps in any namespace", a project
per team and sync impersonation: no instance per team and no namespace lists,
but teams share one instance and impersonation is still behind a flag.
**Revisit if** the number of teams makes per-team instances costly, or
impersonation is stable. See [Multi-tenancy](multi-tenancy.md#a-teams-own-argo-cd).

### Three Applications per team

**Decision.** The team chart renders three components, core, CI and
packages, each its own Application. The core one keeps the name `team-<team>`.
**Why.** Separate sync status and diffs per duty; a waiting Artifact Keeper
permission doesn't mark the whole team unhealthy.
**Why the name.** ApplicationSets give their Applications the cascade
finalizer, so renaming `team-<team>` would delete the team's objects.
See [Multi-tenancy](multi-tenancy.md#one-file-per-team-three-applications).

### CI runs as the team

**Decision.** A team's pipelines run as its own Forgejo user `ci-<team>`,
made by Crossplane, never as the platform's `pac-bot`.
**Why.** A run's token reaches only the team's repositories.
**Consequence.** Crossplane's Forgejo account must be a site admin to create
users; two admission policies (`forgejo-users`, `team-forgejo`) bound what
Crossplane may create from the cluster.
See [Multi-tenancy](multi-tenancy.md#ci-as-the-team-not-as-the-platform).

### Removing a team in two steps, namespaces deleted by a job

**Decision.** A team is removed with `removed: true` in its `team.yaml`
first, its folder afterwards (`tools/teams.py` enforces the order). Argo CD
keeps `team-<team>` and `ci-<team>` (`Delete=false`); a CronJob
(`base/namespace-cleanup`) deletes them once no Application of the team is
left and no Crossplane object remains in them.
**Why.** Deleting the folder at once removed the namespaces from the
`tenants` project in the same change, and Argo CD then dropped the team's
Applications without deleting their objects. Deleting a namespace together
with Crossplane's objects in it left them unable to delete their external
objects. Both were found by removing a test team.
**Alternatives.** Name patterns in `tenants` (`team-*`, `ci-*`): one step,
but looser bounds, and environment namespaces have no safe pattern; a
`tenants` project that only grows; Argo CD PostDelete hooks deleting the
namespaces (the hook needs a ClusterRole, which `tenants` would then have to
permit).
**Cost.** Two pull requests per team, and namespaces linger up to about
15 minutes.
**Revisit if** Argo CD deletes an Application's resources in a controllable
order, or Crossplane stops needing the namespace to delete.

## Secrets and generated files

### Secrets in Git, SOPS-encrypted

**Decision.** Secrets live in this repository encrypted with SOPS (age keys)
and are decrypted by Argo CD with KSOPS. Random secrets (deploy keys, CI
passwords, webhook and cookie secrets, robot passwords) are made once by
`tools/teams.py` and `tools/ci.py`, run by the merge check on a pull request
that needs them and committed to its branch: encrypting needs only the
recipients' public keys, so the pipeline holds no private key.
**Why.** Git holds everything: a rebuilt cluster gets the same secrets, and
so does a rebuilt service (the infra playbooks read them from here first).
**Alternatives.** Generating random secrets in the cluster (Carvel
secretgen-controller, External Secrets Operator generators): no generation
scripts and no KSOPS boilerplate, but a rebuilt cluster gets new secrets.
That is tolerable here, since everything consuming them is reconciled by
Crossplane (only Dashboard sessions would be lost). An external secret store
(Vault, OpenBao): another service to run and back up.
**Revisit if** the generation scripts grow, or a rebuild without Git access
to the age key becomes a requirement.

### The `tools/` scripts

**Decision.** Three scripts check the repository's data and write what an
ApplicationSet can't derive: `teams.py` (validation, namespace lists, keys and
secrets), `ci.py` (the same for platform CI repositories), `generated.py`
(deploy-talos.py's checksums). The merge check runs each `check`. They are
the repository's tooling, not workarounds: hence `tools/`, not the
Kubernetes convention `hack/`.
**Done:** the validation of the files' content moved to `values.schema.json`
in the charts (Helm validates at render); the scripts keep what no chart sees.
The generators run in the merge check (the target branch's copy, on the pull
request's files), which commits their output: nobody runs them by hand.
**Not done in deploy-talos.py:** generating the teams' and CI repositories'
secrets there would tie the cluster installer to the platform's data model,
and they would only appear at its next run, not with the pull request that
needs them.

**Could be replaced by standard primitives, with a functional change:**

| Part | Replacement | The change |
|---|---|---|
| the webhook secret written twice | provider-forgejo's `Webhook` reading `forgejo-pac` directly (`secretRef`) | a provider change; for teams the two copies are in different namespaces (`team-<team>`, `ci-<team>`), so the Webhook objects would move; infra's playbook reads `forgejo-pac` for the webhooks Ansible keeps |
| pac-bot's token copied to every namespace | Crossplane `PersonalAccessToken`s, as for the teams' CI users | new tokens, and pac-bot's password in the cluster |
| random secrets and KSOPS boilerplate | in-cluster generation (previous entry) | a rebuilt cluster gets new secrets |

**Would stay:** cross-file uniqueness (host names, team names), the namespace
lists (until the naming or Argo CD layout changes), `generated.py`.
See [tools](../reference/tools.md).

## External services through Crossplane

### Crossplane for what lives inside the services

**Decision.** Keycloak clients and groups, Forgejo organizations, teams,
repositories and users, Harbor projects and robots, Artifact Keeper
repositories and permissions are Crossplane objects here; Ansible (infra)
only installs the services and the accounts the platform starts with.
**Why.** A merged pull request is enough, nothing needs an Ansible run; each
object sits next to what uses it; console edits are undone.
**Alternatives.** Ansible for everything (a playbook run per change, drift
between runs); Terraform/OpenTofu (another state and workflow).
See [Crossplane](crossplane.md), and infra's [Ansible and Crossplane](https://github.com/vincentbrobald/infra/blob/main/docs/explanation/ansible-and-crossplane.md).

### No `Delete` for what matters

**Decision.** Managed resources use `[Observe, Create, Update]` (plus
`LateInitialize` for server-assigned IDs).
**Why.** Removing an object from Git must not destroy a repository, project
or client others depend on.
**Cost.** Removed teams leave Keycloak groups, Forgejo repositories and
Harbor projects behind, to clean up by hand. See [Crossplane](crossplane.md#no-delete-for-what-matters).

### Taking over existing objects in `[Observe]` first

**Decision.** An object Ansible or a person made is adopted by its external
name in `[Observe]`, compared with the service, then managed; a backup and a
way back exist for every takeover.
**Why.** Providers write defaults out explicitly; managing at once could
change behaviour. See [Take over an existing external object](../how-to/take-over-an-existing-object.md).

### Our own providers

**Decision.** provider-forgejo is an Upjet provider with the Forgejo
Terraform provider compiled in, no Terraform at runtime; provider-artifact-keeper
is written by hand.
**Why.** No Crossplane provider existed for either. Forgejo has a maintained
Terraform provider (MPL-2.0) to build on; Artifact Keeper has none.
**Alternatives.** provider-terraform running Terraform/OpenTofu (an external
tool and its state inside the cluster). See the providers' READMEs.

### Only the Crossplane kinds in use

**Decision.** A ManagedResourceActivationPolicy installs only the listed
kinds.
**Why.** Hundreds of unused CRDs cost the API server memory and slow
discovery. **Cost.** A new kind is activated before its first object; an
active kind is removed with its CRD. See [Add or remove a Crossplane kind](../how-to/add-a-crossplane-kind.md).

## Site services

### Harbor for images

**Decision.** Harbor serves the site's images and the pull-through mirrors.
**Why.** Projects with quotas, robot accounts per pipeline, roles for Keycloak
groups, scanning on push, and a Crossplane provider: what per-team registries
need. The previous registry (zot) had no per-project roles or robots.
See infra's [Registries](https://github.com/vincentbrobald/infra/blob/main/docs/explanation/registries.md).

### Artifact Keeper for packages

**Decision.** Artifact Keeper (MIT) serves Maven, npm, PyPI and generic
packages.
**Why.** Hosted, proxy and virtual repositories for every format needed, OIDC
groups, a complete API. **Alternatives.** Nexus: its prebuilt editions are no
longer open source.

### One source for the site CA

**Decision.** trust-manager publishes `site-root-ca` from one file into every
namespace.
**Why.** One change replaces the CA everywhere, and new namespaces have it
without asking. **Rule.** Nothing else writes `site-root-ca`.
See [One site CA, through trust-manager](site-ca.md).

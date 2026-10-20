# Argo CD projects

> Reference · [Documentation](../../README.md#documentation)

What each Application of the platform Argo CD may deploy, and from where.
The AppProjects are in `clusters/lab/addons/projects/`. Why they are set up
this way: [Bounded Applications](../explanation/projects.md).

| Project | Applications | Destinations | Cluster-scoped kinds | Namespaced kinds | Sources |
|---|---|---|---|---|---|
| `default` | the app-of-apps `addons` (and deploy-talos.py's root Application) | `argocd` | none | Application, ApplicationSet, AppProject, Secret | this repository |
| `platform-infra` | Argo CD, Cilium, cert-manager, Crossplane and its providers, trust-manager, Gateway API, Longhorn, metrics-server, monitoring, tuppr, Tekton, Pipelines-as-Code, `team-policies`, `namespace-cleanup` | any namespace | any | any | this repository, the charts' repositories (listed) |
| `platform-services` | `harbor`, `artifact-keeper`, `headlamp`, `ingress`, `talos-backup`, `ci-<name>` | the namespaces listed | `Namespace` | any | this repository, Headlamp's chart |
| `tenants` | `org-<org>`, `team-<team>`, `team-<team>-ci`, `team-<team>-packages`, `team-<team>-argocd`, `ns-<env>-<team>-<ns>` | `org-*`, `team-*`, `ci-*` and environment namespaces of `applications/`, each listed | `Namespace`, `ClusterProviderConfig` (Forgejo: the teams' CI logins) | `TENANT_KINDS` of `tools/teams.py`, each listed | this repository, the Argo CD chart |
| `preview` | `argocd-preview` | `argocd-preview` | none | any | this repository, the Argo CD chart |

## Files

| File | Written by |
|---|---|
| `default.yaml`, `platform-infra.yaml`, `platform-services.yaml`, `preview.yaml` | hand |
| `tenants.yaml` | `tools/teams.py generate` (namespaces from `applications/`, kinds from `TENANT_KINDS`, `TENANT_CLUSTER_KINDS`) |

## Who sets an Application's project

| Applications | Where `spec.project` is written |
|---|---|
| hand-written, in `addons/` | the Application or ApplicationSet template |
| generated, in `addons/generated/` | deploy-talos.py (`project_of()`: `headlamp`, `ingress`, `talos-backup` → `platform-services`, the rest `platform-infra`, the roots `default`) |

## Not covered

The teams' own Argo CDs (namespaces `team-<team>`) have their own `default`
project, bounded by their namespaced installation and `argocd-namespaces.yaml`.

# Team namespaces

> Reference · [Documentation](../../README.md#documentation)

What every environment namespace `<env>-<team>-<ns>` gets from
`base/team-namespace`, and the rules workloads there must follow. To add one:
[Add an environment](../how-to/add-an-environment.md). To deploy into one:
[Deploy an application](../how-to/deploy-an-application.md).

## Objects

| Object | Value |
|---|---|
| Namespace labels | `example.org/org`, `/team`, `/app`, `/env`; Pod Security `restricted`; `cleanup.example.org/when-orphaned` with the annotation `cleanup.example.org/applications: example.org/namespace=<namespace>` ([Namespace cleanup](namespace-cleanup.md)) |
| ResourceQuota `platform` | see sizes below; never LoadBalancer or NodePort Services |
| LimitRange `platform` | containers without resources: request 50m CPU and 128Mi, limit 512Mi |
| CiliumNetworkPolicy `platform` | incoming only from the namespace itself, the ingress gateway and Prometheus; outgoing not restricted |
| RoleBinding `team-deployer` | ClusterRole `team-deployer` for the team's Argo CD (controller and server) |
| RoleBinding `team-view` | `view` for the group `oidc:team-<team>` (members; no Secrets) |
| ConfigMap `site-root-ca` | the site CA (trust-manager) |

## Quota sizes

| Size | Component | requests.cpu | requests.memory | limits.memory | pods | PVCs | requests.storage |
|---|---|---|---|---|---|---|---|
| small (default) | | 1 | 2Gi | 4Gi | 20 | 5 | 20Gi |
| medium | `base/team-namespace/sizes/medium` | 2 | 4Gi | 8Gi | 40 | 10 | 50Gi |
| large | `base/team-namespace/sizes/large` | 4 | 8Gi | 16Gi | 80 | 20 | 100Gi |

## ClusterRole `team-deployer`

What the team's Argo CD may manage in its namespaces:

| API group | Resources |
|---|---|
| core | configmaps, secrets, services, serviceaccounts, persistentvolumeclaims, pods; read pods/log, events, endpoints |
| `discovery.k8s.io` | endpointslices (read) |
| `apps` | deployments, statefulsets, daemonsets, replicasets, controllerrevisions |
| `batch` | jobs, cronjobs |
| `autoscaling` | horizontalpodautoscalers |
| `policy` | poddisruptionbudgets |
| `rbac.authorization.k8s.io` | roles, rolebindings |
| `gateway.networking.k8s.io` | httproutes, grpcroutes |
| `cert-manager.io` | certificates |
| `monitoring.coreos.com` | servicemonitors, podmonitors, prometheusrules |

Not: quotas, limit ranges, network policies, Gateways or ListenerSets,
Crossplane's kinds, anything cluster-scoped.

## Admission policies

| Policy | Rule |
|---|---|
| `team-routes` | a route in a team namespace attaches only to a ListenerSet of its own namespace |
| `team-listeners` | a listener host name in a team's namespaces starts with `<team>-`, `argocd-<team>.` or `tekton-<team>.` |
| `forgejo-users` | Crossplane makes only CI users (`ci-<name>`, never admins) and tokens with CI scopes; in a team's namespaces only that team's, through ClusterProviderConfig `ci-<team>`; cluster-scoped twins refused |
| `team-forgejo` | a team's Forgejo objects stay its own: repositories `<org>/<team>-...`, its own Forgejo team, references within the namespace (not IDs), no organizations |

## Host names

An environment's overlay adds a ListenerSet `apps` (one HTTPS listener per
host name, named after the host's first label) and its Certificates:

| Property | Rule |
|---|---|
| Host name | `<team>-<name>.apps.lab.example.org`, unique across the site |
| Listener name | the host name's first label |
| Certificate | from the site's ACME CA (ClusterIssuer `acme`) |
| Routes | `parentRefs: [{group: gateway.networking.k8s.io, kind: ListenerSet, name: apps, sectionName: <listener>}]`, no `hostnames` needed |

## Pods

Pod Security `restricted`:

| Field | Required |
|---|---|
| `runAsNonRoot` | `true`, with an image or `runAsUser` that isn't root |
| `allowPrivilegeEscalation` | `false` |
| `capabilities` | `drop: [ALL]` |
| `seccompProfile` | `RuntimeDefault` |
| ports | above 1024 |

Images come from `registry.example.org`: `docker.io/...`, `ghcr.io/...`,
`quay.io/...` through Harbor's proxy caches
(`registry.example.org/docker.io/nginxinc/nginx-unprivileged:1.31.5-alpine`),
the team's own in project `<team>`.

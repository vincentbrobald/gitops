# Several clusters

> Explanation · [Documentation](../../README.md#documentation)

How more than one cluster is deployed from this repository, what each
cluster has of its own, and what exists only once for the whole site. To add
one: [Add a cluster](../how-to/add-a-cluster.md).

## One folder per cluster, one Argo CD per cluster

Every cluster has its own Argo CD, installed by deploy-talos.py, and its own
folder `clusters/<name>/`. That Argo CD's only root is the app-of-apps
`addons`, which syncs `clusters/<name>/addons/` and nothing else. Clusters
don't see each other's folders: a change to `clusters/lab/` can't touch
another cluster, and every Application deploys to its own cluster
(`https://kubernetes.default.svc`).

What clusters share comes from `base/`: a cluster's folder holds overlays
that include a base and patch what differs (host names, URLs), plus the
cluster's own encrypted Secrets. A second cluster reuses the bases; it doesn't
copy their manifests.

## What every cluster has

| What | Where |
|---|---|
| Argo CD and the add-ons the cluster file describes (Cilium, cert-manager, the gateway, Headlamp, Longhorn, monitoring, tuppr, backups) | `addons/generated/`, `generated/`, written by deploy-talos.py |
| its AppProjects | `addons/projects/` |
| the site CA in every namespace | trust-manager (`addons/trust-manager.yaml`, `trust/`) |
| its Secrets, encrypted for its own age key and the admin key | `.sops.yaml` (written by deploy-talos.py) |
| its Keycloak clients `k8s-<name>`, `argocd-<name>` | made by deploy-talos.py through Keycloak's API |
| its host names, `*.apps.<name>.example.org` | the cluster file, registered on the router |

## What exists once for the site

Some things are not per cluster but per site: there is one Keycloak realm,
one Forgejo, one Harbor, one Artifact Keeper, one set of teams. Whatever
manages them must run on exactly one cluster. Today that is `lab`:

| What | Why only once |
|---|---|
| Crossplane and its providers (`crossplane/`, `registries/`) | two Crossplanes managing the same Keycloak client, Forgejo team or Harbor project would overwrite each other forever, each undoing the other's "drift" |
| the teams (`applications/`, `addons/teams.yaml`) | a team's Keycloak group, Forgejo team, repositories and Harbor project are site objects, made through Crossplane; `tools/teams.py` refuses teams on more than one cluster, and the teams' Secrets are encrypted for one cluster's key (`applications/.sops.yaml`) |
| Pipelines-as-Code and the platform CI repositories (`tekton/`, `ci/`, `addons/ci.yaml`) | Forgejo sends each repository's webhook to one address; one CI is enough for the site |
| the merge checks' render-only Argo CD (`argocd-preview`) | it renders every cluster's folder; it needs no cluster of its own |

A cluster without these is a full Kubernetes cluster with its add-ons, logins,
certificates, backups and GitOps, deployed from this repository like `lab`. It
uses the site's services (registry mirror, backups bucket, Keycloak) but
doesn't manage them.

## Checked like the rest

The merge check renders every cluster's folder, from one entry point per
cluster in `.gitops-check.yaml`; a folder without an entry point is reported
as unreached. `tools/generated.py` checks every cluster's generated files.

The merge check knows clusters by their server URL (`clusters` in `.gitops-check.yaml`). Every cluster's
Applications deploy to the same in-cluster URL, so a new cluster's entry point
names the existing `lab` cluster entry: destinations resolve the same way.
Only an ApplicationSet with a cluster generator selecting clusters by label
would need distinct entries, which the in-cluster URL can't provide.

## Teams on several clusters

Teams can only use one cluster today. Giving them environments on a second
cluster would need: the teams' ApplicationSets (and the `tenants` project) on
that cluster too, rendering only that cluster's environments; the site objects
(groups, repositories, projects) still made once, by `lab`; Secrets in
`applications/` encrypted for both clusters' keys; and `tools/teams.py`
generating per-cluster namespace lists. It is a design change, not a step of
adding a cluster.

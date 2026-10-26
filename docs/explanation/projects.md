# Bounded Applications

> Explanation · [Documentation](../../README.md#documentation)

Why every Application of the platform Argo CD belongs to a restricted
AppProject. The table: [Argo CD projects](../reference/projects.md).

## What they prevent

Without projects, any Application may deploy anything anywhere. Projects put
a ceiling on each group: the teams' ApplicationSets (`tenants`) can only touch
the namespaces of `applications/` and the kinds the team chart uses, so a bad
`team.yaml` or chart change can't create a ClusterRole or write into
`kube-system`; namespaced services (`platform-services`) get nothing
cluster-wide but their Namespace; only infrastructure (`platform-infra`) may
install CRDs and cluster-wide RBAC.

## Lists, not patterns

Destinations and kinds are listed one by one rather than with wildcards. An
environment namespace is `<env>-<team>-<ns>` with any `<env>`, so no pattern
would separate it from a platform namespace with two dashes. `tools/teams.py`
generates `tenants.yaml` from the tree instead, so the list is always exact
and a new environment needs no hand edit.

## `default` is narrowed, not removed

The app-of-apps `addons` creates the other projects, so it can't wait for one:
it stays in `default`. `default` is then narrowed to exactly what the root
deploys (Argo CD's own objects in `argocd`). An Application that forgets its
project lands in `default` and is refused, instead of silently getting
everything. On a new cluster Argo CD first creates an open `default`; the
app-of-apps narrows it on its first sync.

## Changing a project is safe

An Application's project isn't part of how Argo CD tracks its objects, so
moving an Application to another project changes none of them. A resource the
new project doesn't permit is refused at sync and shown; nothing is pruned.

## Checked before merge

The merge check renders everything in project `default`.
The check therefore compares every Application against the AppProject in the
same rendering: a source, destination, kind or namespace the project doesn't
permit blocks the merge before it reaches a cluster.

## The teams' own Argo CDs

They keep their own `default` project. Their bounds come from being installed
namespace-scoped and from `argocd-namespaces.yaml`, not from projects.

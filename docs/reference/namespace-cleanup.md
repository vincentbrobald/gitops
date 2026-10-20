# Namespace cleanup

> Reference · [Documentation](../../README.md#documentation)

The CronJob that deletes namespaces whose owning Applications are gone, once
Crossplane is done in them (`base/namespace-cleanup`, Application
`namespace-cleanup`). Why it exists: [Multi-tenancy](../explanation/multi-tenancy.md#removing-a-team).
How a removal uses it: [Remove a team](../how-to/remove-a-team-or-environment.md#a-team).

## Opting in

On the Namespace:

| Field | Value |
|---|---|
| label `cleanup.example.org/when-orphaned` | `"true"` |
| annotation `cleanup.example.org/applications` | a label selector over the Applications in `argocd` that own the namespace, e.g. `example.org/team=platform` |
| annotation `argocd.argoproj.io/sync-options` | `Delete=false`, when the namespace holds Crossplane objects: Argo CD then deletes its content, not the namespace |

Who opts in here:

| Namespaces | Selector | `Delete=false` |
|---|---|---|
| `team-<team>`, `ci-<team>` (chart `base/team`) | `example.org/team=<team>` | yes |
| environments `<env>-<team>-<ns>` (`base/team-namespace`, annotation added by `addons/teams.yaml`) | `example.org/namespace=<env>-<team>-<ns>` | no: a safety net when an environment's folder is deleted alone |

Secret `forgejo-bot` in `team-<team>` is also `Delete=false`: it goes with the
namespace.

## What a run does

For each namespace that opted in and isn't being deleted:

| Condition | Action |
|---|---|
| an Application matches the selector | nothing (and clears an earlier orphan mark) |
| none matches, no mark yet | marks it: annotation `cleanup.example.org/orphaned-since` (Unix time) |
| marked less than `GRACE_SECONDS` ago | waits |
| marked long enough, Crossplane managed resources left | waits; logs how many and which |
| marked long enough, none left | deletes the namespace |

Managed resources are the namespaced CRDs of category `managed` (every
Crossplane provider's kinds).

## Settings

| Item | Value |
|---|---|
| Schedule | every 5 minutes, one run at a time |
| Retries | an API call answered 429 or 5xx, or not answered, is tried 5 times (waits 1, 2, 4, 8 s, or `Retry-After`); then the run fails and the next starts over |
| `GRACE_SECONDS` | `600` |
| `DRY_RUN` | `false`; `true` logs what it would do |
| `ARGOCD_NAMESPACE` | `argocd` |
| Image | `docker.io/library/python:3.14-slim`, script `cleanup.py` (standard library) from a ConfigMap |
| Namespace | `namespace-cleanup`, Pod Security `restricted` |

## Rights

| ClusterRole | Grants |
|---|---|
| `namespace-cleanup` | namespaces: get, list, patch, delete; CRDs and Applications: get, list |
| `namespace-cleanup:crossplane-view` | aggregated from the roles labelled `rbac.crossplane.io/aggregate-to-view`: read the managed resources (no Secrets) |

## Logs

```sh
kubectl -n namespace-cleanup get jobs
kubectl -n namespace-cleanup logs job/<job>
```

One line per namespace that isn't simply owned, e.g. `team-x: orphaned for
300s of 600s`, `team-x: waiting for Crossplane: 2 managed resource(s) left`.

# Merge checks

> Reference · [Documentation](../../README.md#documentation)

What runs on every pull request to `main`, and what blocks a merge. Why the
checks are built this way: [Rendering before merging](../explanation/merge-checks.md).
The scanner itself: [gitops-scanner](https://github.com/vincentbrobald/gitops-scanner).

## Branch protection

| Rule | Value |
|---|---|
| Required status | `Pipelines as Code CI / gitops-check` |
| Branch | must be up to date with `main` |
| Direct pushes | deploy keys only (deploy-talos.py commits its generated files that way) |

## Steps (`.tekton/pr-check.yaml`, read from `main`)

The checks run the target branch's `tools/` scripts (`GITOPS_ROOT` points them
at the pull request's files), unless the pull request changes `tools/`. The
Forgejo credentials are mounted only into the steps `clone`, `generate` and
`check`.

| Step | Command | Fails when |
|---|---|---|
| `generate` | the target branch's `tools/teams.py generate`, `tools/ci.py generate` on the pull request's files | never fails on content; when it made files, it commits them to the pull request's branch as pac-bot and stops the run (the push starts a new one). Skipped for a pull request that changes `tools/` |
| `teams` | `python3 tools/teams.py check` | the tree `applications/` is invalid, a generated file is stale, or a team folder is deleted without `removed: true` on `main` first |
| `ci-repositories` | `python3 tools/ci.py check` | a `ci/<name>/` folder is incomplete, or a generated file is stale |
| `generated` | `python3 tools/generated.py check` | a file deploy-talos.py generates differs from `generated/CHECKSUMS`, or an unlisted file is there |
| `check` | gitops-check | see below |

## gitops-check

Renders the pull request before and after with a render-only Argo CD
(`argocd-preview`, the clusters' version), starting from the entry points in
`.gitops-check.yaml`.

| Blocks the merge (errors) | Reported only (warnings) |
|---|---|
| an Application or ApplicationSet that doesn't render (including values a chart's `values.schema.json` refuses) | resources without a known schema |
| a resource rendered by two Applications | an ApplicationSet generating nothing |
| a Secret with values in clear in Git, a kustomize `secretGenerator` | a deploy-talos.py file edited by hand |
| a resource invalid against its schema | the target branch failing to render |
| a directory with manifests no entry point reaches (unless `ignore`d) | |
| an Application its AppProject doesn't permit (source, destination, kind, namespace), or a missing project | |
| a branch not up to date with `main` | |

Secrets are never decrypted: they render with key names and placeholder
values. The report (a pull request comment) lists errors, warnings and the
per-resource diff.

## `.gitops-check.yaml`

This repository's values. What each key means: gitops-scanner's
[configuration reference](https://github.com/vincentbrobald/gitops-scanner/blob/main/docs/reference/configuration.md).

| Key | Value here |
|---|---|
| `repository` | this repository's SSH URL; `trackedRevisions: [main, HEAD]` |
| `argocd.version` | the clusters' Argo CD version |
| `clusters` | `lab` (`https://kubernetes.default.svc`) |
| `entrypoints` | one per cluster folder (`lab`: `clusters/lab/addons`, recursive), and `samples` (`samples/applicationsets`, not deployed). Every cluster's entry point names the cluster entry `lab`: all clusters' Argo CDs deploy to their own in-cluster server, and the render-only Argo CD knows clusters by server URL |
| `ignore` | `.tekton` (this repository's pipelines), `base/team-namespace/sizes` (quota components the environments include) |
| `external` | the teams' repositories, `ssh://git@forgejo.example.org:2222/example/` |
| `checks` | informational (`secrets: redact`, `blockOn: errors`): the scanner always behaves this way |

## Samples

`samples/applicationsets/` holds one ApplicationSet per generator type (list,
git directories, git files, clusters, matrix), with Go templates and
`missingkey=error`. They are rendered and checked like everything else, but
no Application syncs them and their Applications have no automated sync.

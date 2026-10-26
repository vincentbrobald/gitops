# Rendering before merging

> Explanation · [Documentation](../../README.md#documentation)

Why every pull request is rendered before it can merge, and what that buys.
What runs: [Merge checks](../reference/merge-checks.md).

## Render, don't lint

A change to this repository rarely breaks where it is made: a chart value, a
generator template, an ApplicationSet parameter breaks what Argo CD renders
from it, somewhere else. So the check renders the whole repository twice,
before (`main`) and after (the pull request), with Argo CD's own code at
the clusters' version, and compares. What would fail on the
cluster fails in the pull request; what would change on the cluster shows as
a per-resource diff for the reviewer.

## Following what Argo CD follows

Rendering starts at the entry points (the cluster's `addons` folder) and
follows Applications, ApplicationSets and their sources, as Argo CD does. A
directory nothing reaches is therefore an error: it is either a typo in an
Application's path or dead content. Only directories listed under `ignore`
are exempt.

## Secrets stay secret

The check never decrypts: KSOPS generators render each Secret with its key
names and placeholder values. The diff still shows a key added or removed,
or "values changed" when the encrypted value differs. A Secret in clear in
Git, on the other hand, is an error.

## Errors block, diffs inform

Only errors block (render failures, duplicates, invalid resources, clear
Secrets, unreached directories, project violations); a diff, however large,
never does. Whether a change is wanted is the reviewer's call, whether it
works is the check's.

## Layout checks first

Before rendering, `tools/teams.py`, `tools/ci.py` and `tools/generated.py` check
the data the repository is built from: names, keys, generated files being
current, deploy-talos.py's files untouched. Their errors are about the file
that is wrong, which a render error rarely is.

## What it can't see

Crossplane's kinds have no schemas, so a wrong field in a managed resource
only shows at sync, in the object's conditions. The teams' own repositories are outside the check: the
platform renders the teams' Argo CDs, not what they deploy.

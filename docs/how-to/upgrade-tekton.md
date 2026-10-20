# Upgrade Tekton

> How-to · [Documentation](../../README.md#documentation)

Move Tekton Pipelines, Pipelines-as-Code or the Tekton Dashboard to a new
release. Each release file is kept in Git unchanged, next to the
kustomization that names its source and checksum: `base/tekton/pipelines/`,
`base/tekton/pipelines-as-code/`, `base/tekton/dashboard/`. Why:
[Design decisions](../explanation/design-decisions.md#releases-kept-in-git).

1. Pick the release: at least 14 days old unless it fixes a security issue,
   and compatible with the others (Pipelines-as-Code's release notes name the
   Pipelines versions it supports). Read the release notes for removed fields
   and changed defaults; `config/feature-flags` changes matter (the merge
   check's pipeline needs `enable-api-fields: beta`).
2. Download the file the kustomization names, at the new version, over the
   old one. For Pipelines:

   ```sh
   v=v1.18.0
   curl -sSfL -o base/tekton/pipelines/release.yaml \
     https://github.com/tektoncd/pipeline/releases/download/$v/release.yaml
   sha256sum base/tekton/pipelines/release.yaml
   ```

   Pipelines-as-Code: `tektoncd/pipelines-as-code`, file `release.k8s.yaml`;
   Dashboard: `tektoncd/dashboard`, file `release.yaml`.
3. Compare the checksum with the one GitHub lists for that asset:

   ```sh
   curl -sSf https://api.github.com/repos/tektoncd/pipeline/releases/tags/$v \
     | python3 -c 'import sys,json; [print(a["digest"], a["name"]) for a in json.load(sys.stdin)["assets"] if a["name"]=="release.yaml"]'
   ```

   They must be equal. Don't edit the file: patches go in the kustomization.
4. Write the new URL and checksum in the kustomization's comment.
5. [Propose the change](propose-a-change.md). The report shows every changed
   object of the release (images, CRDs, ConfigMaps): read it for anything the
   release notes didn't mention.
6. Check after the merge:

   ```sh
   kubectl -n argocd get application tekton-pipelines pipelines-as-code tekton-dashboard
   kubectl -n tekton-pipelines get deploy -o custom-columns=NAME:.metadata.name,IMAGE:.spec.template.spec.containers[0].image
   ```

   All Synced and Healthy, the new version in the images; then a pull request
   in this repository still gets its merge check.

If the upgrade breaks Pipelines-as-Code, the merge check can't run on the
pull request that reverts it: revert on `main` with a deploy key, or merge the
revert without the check, then let Argo CD sync.

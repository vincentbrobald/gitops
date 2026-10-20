# Build and host the images yourself

> How-to · [Documentation](../../README.md#documentation)

By default the platform runs three images built elsewhere and published on
Docker Hub. To build them on your own CI and serve them from your own Harbor
instead (to pin exactly what runs, to change the code, or to depend on no
outside registry), follow the steps below once per image. Going back is the
last step reversed.

| Image | Default | Used by, in this repository |
|---|---|---|
| provider-forgejo | `docker.io/vincentbrobald/provider-forgejo:<VERSION>-<commit>` | Crossplane: `clusters/<cluster>/crossplane/forgejo.yaml`, `spec.package` |
| provider-artifact-keeper | `docker.io/vincentbrobald/provider-artifact-keeper:<VERSION>-<commit>` | Crossplane: `clusters/<cluster>/crossplane/artifact-keeper.yaml`, `spec.package` |
| gitops-scanner | `docker.io/vincentbrobald/gitops-scanner:latest` | the merge checks: `.tekton/pr-check.yaml`, the `image:` of its steps |

The two providers are Crossplane packages: the image is the package
(`/package.yaml`) and the provider at once. Their sources and this
repository's own are on GitHub: `github.com/vincentbrobald/provider-forgejo`,
`provider-artifact-keeper`, `gitops-scanner`.

## Before you start

- Harbor runs (the infra repository) and Crossplane manages it: the projects
  in `clusters/<cluster>/registries/harbor/projects.yaml`. Two of them hold
  these images, `providers` and `gitops-scanner`; both are public, so that the
  clusters pull without credentials. The proxy projects `docker.io`,
  `ghcr.io`, `quay.io` and `gcr.io` serve the base images the builds use.
- Pipelines-as-Code runs your repositories' pipelines
  ([Platform CI repositories](../reference/ci-repository.md)).

## 1. Put the sources in your Forgejo

For each image, an empty repository on your Forgejo (the infra repository's
`forgejo.yml` makes it), then:

```sh
git clone https://github.com/vincentbrobald/provider-forgejo
cd provider-forgejo
git remote set-url origin ssh://git@forgejo.example.org:2222/alice/provider-forgejo.git
mkdir -p .tekton && git mv examples/tekton/build.yaml .tekton/build.yaml
git commit -m "CI: build the image here" && git push -u origin main
```

`.tekton/build.yaml` tests the code, builds the image with kaniko (base
images through Harbor's proxy projects), scans it with Trivy (fixable HIGH or
CRITICAL fail it) and, on `main`, pushes it to your Harbor. It takes the
registry's name and a robot's credentials from Secret `registry-push` of its
namespace, and your CA from ConfigMap `site-root-ca`: the next step makes
both.

## 2. Make it a platform CI repository

`clusters/<cluster>/ci/<name>/repository.yaml`, with a Harbor robot in the
image's project:

```yaml
repository: alice/provider-forgejo
namespace: provider-forgejo
forgejo:
  repositoryId: 42        # GET /api/v1/repos/alice/provider-forgejo, field id
harbor:
  project: providers      # gitops-scanner for gitops-scanner
  robot: provider-forgejo-ci
```

The rest (the namespace in project `platform-services`, the merge check
making the Secrets, the webhook): [Add a platform CI
repository](add-a-platform-ci-repository.md).

## 3. Build

Push to `main` (or re-run the first PipelineRun once the webhook exists). On
success the image is in Harbor:

| Image | Pushed as |
|---|---|
| provider-forgejo | `<registry>/providers/forgejo:<VERSION>-<commit>` and `:latest` |
| provider-artifact-keeper | `<registry>/providers/artifact-keeper:<VERSION>-<commit>` and `:latest` |
| gitops-scanner | `<registry>/gitops-scanner/gitops-check:<commit>` and `:latest` |

`<registry>` is your Harbor's name (e.g. `registry.example.org`),
`<VERSION>` the repository's `VERSION` file, `<commit>` the commit (7
characters for the providers, the whole hash for gitops-scanner).

## 4. Point the platform at it

Change the reference and [propose the change](propose-a-change.md):

```yaml
# clusters/<cluster>/crossplane/forgejo.yaml
spec:
  package: registry.example.org/providers/forgejo:v0.7.0-1a2b3c4
```

```yaml
# .tekton/pr-check.yaml (from examples/tekton/pr-check.yaml), each step's image
image: registry.example.org/gitops-scanner/gitops-check:latest
```

Keep the Provider's name: Crossplane installs the new package as a new
revision of the same Provider and switches to it (`kubectl get
providers.pkg.crossplane.io` shows the new package, Healthy), and its kinds
and objects stay. Never replace a Provider by another one with a new name:
deleting a Provider deletes its CRDs, and with them every object of its
kinds. The merge checks pull `:latest` at each run, so a change to
gitops-scanner applies to the next pull request.

From then on, a merge in the image's repository builds a new image; a
provider reaches the clusters when its `spec.package` names the new tag.

## Going back to Docker Hub

Set the references back to the `docker.io/vincentbrobald/...` images (the
same tags exist there) and propose the change. The CI repositories may stay:
they only build.

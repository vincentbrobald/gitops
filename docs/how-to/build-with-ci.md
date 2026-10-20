# Build with CI (team)

> How-to · [Documentation](../../README.md#documentation)

For a team: run pipelines from a repository on every pull request and push,
build images, publish packages, and deploy the result. What a run gets:
[CI runs](../reference/ci-runs.md). `example/platform-hello`'s
`.tekton/build.yaml` is a complete example.

## Run a pipeline

1. Add a PipelineRun to `.tekton/` in a team repository, with the events that
   start it:

   ```yaml
   metadata:
     annotations:
       pipelinesascode.tekton.dev/on-event: "[pull_request, push]"
       pipelinesascode.tekton.dev/on-target-branch: "[main]"
   ```

2. Clone with the workspace `{{ git_auth_secret }}` (it holds the run's
   credentials), and mount ConfigMap `site-root-ca` for anything that calls
   Forgejo, Harbor or Artifact Keeper.
3. Push. Check: the commit or pull request shows a status from `ci-<team>`;
   the run is in your Tekton Dashboard, `https://tekton-<team>.apps.lab.example.org`.

Pull requests from people outside the team wait for a member's `/ok-to-test`
comment; `/retest` runs a pipeline again.

## Build and push an image

Use kaniko (`ghcr.io/osscontainertools/kaniko`) with the Harbor robot from
Secret `harbor-push`:

- destination `registry.example.org/<team>/<image>:<tag>`;
- user `robot$<team>+<team>-ci`, password key `attribute.secret`;
- `--registry-certificate registry.example.org=<path to site-root-ca.crt>`;
- base images through Harbor's proxy caches (`registry.example.org/docker.io/...`).

Check: the image is in Harbor, project `<team>`, with its scan result.

## Publish a package

Authenticate with Secret `artifact-keeper-push` (`token` as bearer, or as the
password of `username`) and publish to `<team>-<format>` at
`https://artifacts.example.org`; resolve dependencies through
`<team>-<format>-all` ([endpoints](../reference/ci-runs.md#packages-artifact-keeper-httpsartifactsexampleorg)).

## Deploy what was built

Have the run on `main` commit the new image tag to the environment's overlay
(e.g. `images:` in `deploy/dev/kustomization.yaml`) with the run's
credentials. Exclude that path with `pipelinesascode.tekton.dev/on-path-change`
so the commit doesn't start another build. Your Argo CD deploys the new tag.

## Follow a run

```sh
kubectl -n ci-<team> get pipelineruns
kubectl -n ci-<team> logs <run>-build-pod -c step-<name>
```

A failed step's last lines also show in the status on Forgejo.

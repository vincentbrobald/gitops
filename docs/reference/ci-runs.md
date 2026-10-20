# CI runs

> Reference · [Documentation](../../README.md#documentation)

What a team's pipeline run gets and may use. How to set one up:
[Build with CI](../how-to/build-with-ci.md).

## Where and as whom

| Property | Value |
|---|---|
| Runner | Pipelines-as-Code, the PipelineRuns in `.tekton/` of a team repository |
| Namespace | `ci-<team>`, Pod Security `baseline` |
| Forgejo identity | user `ci-<team>` (never the platform's `pac-bot`): its token reaches the team's repositories only |
| Who may start one | pull requests from members of the Forgejo team; others after a member's `/ok-to-test`; `/retest` reruns |
| Results | commit and pull request status; failed step's last lines in the status |
| Dashboard | `https://tekton-<team>.apps.lab.example.org` (Keycloak, members only) |

## PipelineRun annotations

| Annotation | Value |
|---|---|
| `pipelinesascode.tekton.dev/on-event` | `"[pull_request, push]"` |
| `pipelinesascode.tekton.dev/on-target-branch` | `"[main]"` |
| `pipelinesascode.tekton.dev/on-path-change` | glob patterns: run only when a matching path changes (`example/platform-hello`'s `.tekton/build.yaml` has an example) |

## Workspaces and Secrets

| Name | Content |
|---|---|
| `{{ git_auth_secret }}` | the user's credentials to clone and push: `.git-credentials`, `.gitconfig` |
| ConfigMap `site-root-ca` | the site's CA, key `site-root-ca.crt` (Forgejo, Harbor, Artifact Keeper use it) |
| Secret `harbor-push` | the Harbor robot: key `attribute.secret`, user `robot$<team>+<team>-ci`, push and pull in project `<team>` |
| Secret `artifact-keeper-push` | Artifact Keeper token: keys `token` (bearer, or password of `username`), `username` |

## Images

| Item | Value |
|---|---|
| Builder | kaniko (`ghcr.io/osscontainertools/kaniko`): no daemon, no privileges |
| Push to | `registry.example.org/<team>/<image>` |
| Base images | through Harbor's proxy caches; `--registry-certificate registry.example.org=<ca>` |
| Scan | Harbor scans every push (Trivy) |

## Packages (Artifact Keeper, `https://artifacts.example.org`)

| Format | Publish to | Resolve through |
|---|---|---|
| Maven | `/maven/<team>-maven` | `<team>-maven-all` (and Maven Central) |
| npm | `/npm/<team>-npm/` | `<team>-npm-all` (and npmjs) |
| PyPI | `/pypi/<team>-pypi/` | `<team>-pypi-all` (and PyPI) |
| generic | `PUT /api/v1/repositories/<team>-generic/artifacts/<path>` | |

People sign in through Keycloak and make their own API token in the UI.

## Limits

| Limit | Value |
|---|---|
| `ci-<team>` quota | 2 CPU and 4 GiB requested, 8 GiB memory limit, 10 pods |
| Steps without resources | 50m CPU and 128Mi requested, 1 GiB limit |
| Concurrency | two runs at a time per repository |
| Not allowed | privileged steps, host access (Pod Security `baseline`) |

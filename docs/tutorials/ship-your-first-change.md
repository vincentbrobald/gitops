# Ship your first change

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you are a member of a team on the platform. You find your
team's tools, change its application through a pull request, watch the CI
build it, merge, and see the new version answer on its host name a few
minutes later. Then you take the change back. You never touch the platform's
repository: everything happens in your team's own repositories.

The example is the platform team's demo, `example/platform-hello`, served at
https://platform-hello-dev.apps.lab.example.org. For another team, replace
`platform` with its name.

You need: membership of the team (its `team.yaml` lists you), a browser that
trusts the site's CA, and Git with an SSH key on your Forgejo account. Log in
to Forgejo once (https://forgejo.example.org, "Sign in with keycloak") if you
never did: the platform makes you a member of the Forgejo team only after
your first login.

## 1. Find your team's tools

Open each of these and log in through Keycloak:

| Tool | Address | You should see |
|---|---|---|
| Forgejo | https://forgejo.example.org/example | the repositories `platform-gitops` and `platform-hello` |
| the team's Argo CD | https://argocd-platform.apps.lab.example.org | `root` and `hello-dev`, Synced and Healthy |
| the team's Tekton Dashboard | https://tekton-platform.apps.lab.example.org | the past runs of `build` in `ci-platform` |
| Harbor | https://registry.example.org | the project `platform`, with the repository `hello` |

`platform-gitops` says *what* the team's Argo CD deploys (`apps/`);
`platform-hello` holds the application, its manifests and its CI.

Open https://platform-hello-dev.apps.lab.example.org: the page names the
commit it was built from. Note it.

## 2. Change the page in a pull request

```sh
git clone ssh://git@forgejo.example.org:2222/example/platform-hello.git
cd platform-hello
git switch -c my-first-change
sed -i 's/👋/🚀/' app/index.html
git commit -am "Page: a rocket" && git push -u origin my-first-change
```

Open a pull request for `my-first-change` in Forgejo. Within a minute it shows
a status from `ci-platform`, first pending, then green. In the Tekton
Dashboard you should see the run: on a pull request it builds the image to
check it, and pushes nothing.

## 3. Merge, and watch it arrive

Merge the pull request. The merge is a push to `main`, which starts the CI
again, this time with two more steps:

1. In the Tekton Dashboard, the new run's step `image` pushes
   `registry.example.org/platform/hello:<commit>`, and the step `deploy`
   commits that tag to `deploy/dev/kustomization.yaml`.
2. In Forgejo, `main` has a new commit by the team's CI:
   `deploy/dev: hello <commit>`.
3. In Harbor, the project `platform` has the new tag; its scan result shows
   once Trivy is done.
4. In the team's Argo CD, `hello-dev` goes OutOfSync, then Synced, within
   three minutes ("Refresh" is immediate): it rolled the Deployment to the
   new image.

Reload https://platform-hello-dev.apps.lab.example.org: you should see the
rocket and the new commit.

## 4. Look at what runs

Your Keycloak login reads (but doesn't change) your team's namespaces. With
the cluster's OIDC kubeconfig (`/root/lab/lab-cluster/kubeconfig-oidc` on the
host):

```sh
export KUBECONFIG=/root/lab/lab-cluster/kubeconfig-oidc
kubectl -n dev-platform-hello get pods
kubectl -n dev-platform-hello logs deploy/hello --tail=5
```

The first command prints a login URL the first time. You should see two
`hello` pods Running, and nginx's access log with your requests. Secrets are
the one thing you can't read there.

## 5. Take it back

A change is undone like it was made: with a new commit, built and deployed
the same way.

```sh
git switch main && git pull
sed -i 's/🚀/👋/' app/index.html
git commit -am "Page: back to the hand" && git push
```

This time you pushed to `main` directly, which members may do; a pull request
would add the check before the merge. The push starts the CI like any change
to `app/`: a new image, a new tag, and a few minutes later the page shows the
hand again, with the newest commit. Writing an older tag into `deploy/dev` by
hand would roll back faster, until the next build overwrites it.

## What you did

You shipped a change through your team's own path: a pull request checked by
your CI, a merge that built and published an image, and your Argo CD
deploying the tag your CI committed. The platform's repository wasn't
involved: it decides where your team may deploy, not what.

## Next steps

- Build something of your own: [Build with CI](../how-to/build-with-ci.md),
  [Deploy an application](../how-to/deploy-an-application.md).
- The rules your pods follow: [Team namespaces](../reference/team-namespaces.md).
- When something is refused: [Troubleshoot a team deployment](../how-to/troubleshoot-a-team-deployment.md).
- What a pipeline run gets: [CI runs](../reference/ci-runs.md).

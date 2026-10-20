# Onboard a team

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you give a new team, `sandbox`, everything the platform
offers: its own Argo CD, repositories, CI and registry project, and an
environment with a host name. Then you act as the team: you put an
application in its repository, let its CI build it, and have its Argo CD
deploy it at https://sandbox-hello-dev.apps.lab.example.org. At the end you
remove the team again.

You need: a Keycloak account in realm `example` that has logged in to Forgejo
once, permission to open pull requests in this repository, a clone of it, and
`kubectl` with the admin kubeconfig of cluster `lab`
(`export KUBECONFIG=/root/lab/lab-cluster/kubeconfig`). The examples use the
member `alice`: use your own user name. If a team `sandbox` exists already,
choose another name and use it everywhere `sandbox` appears.

## 1. Create the team

Create `applications/example/sandbox/team.yaml`:

```yaml
description: A team to learn with
members: [alice]
repositories: [sandbox-hello]
```

Commit it on a branch, push, and open a pull request against `main`:

```sh
git switch -c team-sandbox
git add applications/example/sandbox/team.yaml
git commit -m "Team sandbox"
git push -u origin team-sandbox
```

Within a minute the merge check adds a commit to your branch, by pac-bot:
"Generated files (tools/teams.py, tools/ci.py)". It holds the team's deploy
key and encrypted Secrets in `applications/example/sandbox/argocd/`, and the
team's namespaces in `clusters/lab/addons/projects/tenants.yaml`. The check
then runs again on that commit, turns green, and posts a report. Its table
lists the new Applications `team-sandbox`, `team-sandbox-argocd`,
`team-sandbox-ci`, `team-sandbox-packages`, and the team Argo CD's own
`team-sandbox/root`.

Merge the pull request. After a few minutes:

```sh
kubectl -n argocd get applications -l example.org/team=sandbox
```

You should see `team-sandbox`, `team-sandbox-argocd` and `team-sandbox-ci`
Synced and Healthy. `team-sandbox-packages` stays Degraded: its Artifact
Keeper permissions wait for the team's group to exist there. Log in once at
https://artifacts.example.org through Keycloak, and it turns Healthy.

Look at what the team got:

- https://argocd-sandbox.apps.lab.example.org: the team's Argo CD. "Log in
  via Keycloak" lets you in. It has one Application, `root`, with nothing to
  deploy yet.
- Forgejo, organization `example`: the team `sandbox` with you as a member,
  and the repositories `sandbox-gitops` and `sandbox-hello`, each with a
  README.
- https://tekton-sandbox.apps.lab.example.org: the team's Tekton Dashboard,
  empty.

## 2. Give the application an environment

The application `hello` gets the environment `dev`: namespace
`dev-sandbox-hello`, host name `sandbox-hello-dev.apps.lab.example.org`.
Update `main` (`git switch main && git pull`), start a new branch, and create
three files.

`applications/example/sandbox/hello/base/kustomization.yaml`, what every
environment of `hello` shares:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: [../../../../../base/team-namespace]
```

`applications/example/sandbox/hello/env/dev/kustomization.yaml`, the
environment, an overlay of the base:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: [../../base, listeners.yaml]
```

`applications/example/sandbox/hello/env/dev/listeners.yaml`, the host name's
listener and certificate, copied from the platform team's demo:

```sh
sed 's/platform-hello-dev/sandbox-hello-dev/g' \
  applications/example/platform/hello/env/dev/listeners.yaml \
  > applications/example/sandbox/hello/env/dev/listeners.yaml
```

Commit, push, open a pull request. pac-bot again commits the updated
namespace lists, and the report shows one new Application,
`ns-dev-sandbox-hello`, with eight objects: the Namespace, its quota, limit
range and network policy, two role bindings, the ListenerSet `apps` and the
Certificate. Merge it. About two minutes later:

```sh
kubectl -n dev-sandbox-hello get listenerset,certificate
```

You should see the ListenerSet `apps` Accepted and Programmed, and the
Certificate `tls-sandbox-hello-dev` Ready.

## 3. Put the application in its repository

From here on you are the team. Clone `sandbox-hello` and copy the platform
team's demo into it, renaming the team (the namespace, host name, image and
Harbor robot all derive from it):

```sh
cd ..
git clone ssh://git@forgejo.example.org:2222/example/sandbox-hello.git
git clone ssh://git@forgejo.example.org:2222/example/platform-hello.git
cd sandbox-hello
cp -r ../platform-hello/{app,deploy,.tekton,Containerfile} .
grep -rl platform app deploy .tekton | xargs sed -i -e 's/platform-/sandbox-/g' \
  -e 's/-platform/-sandbox/g' -e 's#/platform/#/sandbox/#g' \
  -e 's/\$platform+/$sandbox+/g' -e 's/team platform/team sandbox/g'
git add -A && git commit -m "The hello application" && git push
```

You now have a static page (`app/`), its image (`Containerfile`), the
manifests (`deploy/base`, and `deploy/dev` for the environment) and the CI
(`.tekton/build.yaml`).

The push to `main` starts the CI. In the Tekton Dashboard you should see a
run `build-...` in namespace `ci-sandbox` succeed within a minute or two.
Then:

```sh
git pull
git log --oneline -2
```

You should see a commit by the team's CI, `deploy/dev: hello <commit>`: the
run built the image, pushed `registry.example.org/sandbox/hello:<commit>` to
Harbor, and wrote that tag into `deploy/dev/kustomization.yaml`.

## 4. Deploy it with the team's Argo CD

The team's Argo CD deploys the Applications in `apps/` of `sandbox-gitops`.
Add one, copied from the demo's:

```sh
cd ..
git clone ssh://git@forgejo.example.org:2222/example/sandbox-gitops.git
git clone ssh://git@forgejo.example.org:2222/example/platform-gitops.git
cd sandbox-gitops && mkdir apps
sed 's/platform-/sandbox-/g' ../platform-gitops/apps/hello-dev.yaml > apps/hello-dev.yaml
git add -A && git commit -m "Deploy hello to dev" && git push
```

The Application takes `deploy/dev` of `sandbox-hello` and deploys it to
`dev-sandbox-hello`. Within three minutes ("Refresh" on `root` is
immediate), the team's Argo CD shows `hello-dev` Synced and Healthy. Then:

```sh
curl https://sandbox-hello-dev.apps.lab.example.org/
```

You should see "Hello from team sandbox", with the commit the CI built.

## 5. Remove the team

A team goes in two pull requests. Back in this repository, on a new branch,
add one line to `applications/example/sandbox/team.yaml`:

```yaml
removed: true
```

Propose it. pac-bot deletes the team's generated `argocd/` folder, and the
report shows the team's Applications and `ns-dev-sandbox-hello` as removed.
Merge. Within a few minutes Argo CD deletes the team's Argo CD, Dashboard,
environment and CI objects; Crossplane deletes its memberships, deploy keys,
CI user and webhooks; and about ten minutes later the namespace cleanup
deletes `team-sandbox` and `ci-sandbox`:

```sh
kubectl get namespace team-sandbox ci-sandbox
```

You should see "not found" for both. Then delete the folder in a second pull
request:

```sh
git rm -r applications/example/sandbox
```

The merge check takes the team's namespaces out of `tenants.yaml`; it would
have refused this step without the first one.

What holds the team's work stays, by design: Crossplane never deletes it.
Remove it by hand:

- Keycloak, realm `example`: the group `team-sandbox` and the clients
  `argocd-lab-team-sandbox`, `tekton-lab-team-sandbox`;
- Forgejo: the repositories `example/sandbox-gitops` and
  `example/sandbox-hello`, then the team `sandbox`;
- Harbor: the project `sandbox` (delete its repository `hello` first);
- Artifact Keeper: the repositories `sandbox-*`.

## What you did

As a platform admin, you created a team and an environment with one small
file each, and let the merge check generate the rest. As the team, you built
and deployed an application without touching this repository: the platform
decides *where* a team may deploy, the team decides *what*.

## Next steps

- As a team member, change an application and follow it to the cluster:
  [Ship your first change](ship-your-first-change.md).
- See the merge check refuse a change: [Your first platform change](your-first-platform-change.md).
- Variations: [Add a team](../how-to/add-a-team.md),
  [Add an environment](../how-to/add-an-environment.md),
  [Deploy an application](../how-to/deploy-an-application.md),
  [Build with CI](../how-to/build-with-ci.md).
- Everything a team gets: [What a team gets](../reference/team-resources.md).
- Why it works this way: [Multi-tenancy](../explanation/multi-tenancy.md).

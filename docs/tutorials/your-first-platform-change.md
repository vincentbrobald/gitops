# Your first platform change

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you change the platform the only way it changes: through a
pull request that the merge check renders before anything reaches the
cluster. You give the demo application a second environment, `test`, make a
mistake on purpose, read how the check reports it, fix it, merge, and watch
Argo CD apply the change. Then you take the environment away again.

You need: permission to open pull requests in this repository, a clone of
it, and `kubectl` with the admin kubeconfig of cluster `lab`
(`export KUBECONFIG=/root/lab/lab-cluster/kubeconfig`).

## 1. Make the change, with a mistake

Start from an up-to-date `main`:

```sh
git switch main && git pull
git switch -c hello-test
```

An environment is a folder under the application's `env/`. Create
`applications/example/platform/hello/env/test/kustomization.yaml`, with a
typo in the second file name:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: [../../base, listener.yaml]
```

and the listeners file it means, copied from the environment `dev`:

```sh
sed 's/platform-hello-dev/platform-hello-test/g' \
  applications/example/platform/hello/env/dev/listeners.yaml \
  > applications/example/platform/hello/env/test/listeners.yaml
```

Run the layout check the merge check starts with:

```sh
python3 tools/teams.py check
```

You should see two errors: `argocd-namespaces.yaml` and `tenants.yaml` are
"not current". They list every namespace, and yours is new. You don't fix
them: the merge check will. The typo is not among the errors, because this
check looks at the tree, not at what Kustomize builds from it.

## 2. Let the merge check find it

```sh
git add applications/example/platform/hello/env/test
git commit -m "hello: environment test"
git push -u origin hello-test
```

Open a pull request for `hello-test` against `main`, and watch it:

1. A first run of `Pipelines as Code CI / gitops-check` fails within a
   minute, and a commit by pac-bot appears on your branch: "Generated files
   (tools/teams.py, tools/ci.py)". This first run only made the namespace
   lists; it stops on purpose so that the next run checks them.
2. A second run renders `main` and your branch with a render-only Argo CD,
   compares them, and fails. Its report, a comment on the pull request,
   starts with **gitops-check failed: 1 error(s)**:

   > ns-test-platform-hello: ... Unable to generate manifests in
   > applications/example/platform/hello/env/test: ... accumulating resources
   > from 'listener.yaml': ... no such file or directory

   The table below it says the same: `ns-test-platform-hello`, **render
   failed**. The Application exists in the rendering (an ApplicationSet
   makes one per environment folder), but Argo CD can't build what it would
   deploy. On the cluster, this would have been a broken Application; here,
   the merge button is blocked.

## 3. Fix it

Pull pac-bot's commit first, then fix the name:

```sh
git pull
sed -i 's/listener.yaml\]/listeners.yaml]/' applications/example/platform/hello/env/test/kustomization.yaml
git commit -am "hello test: the listeners file's name" && git push
```

The check runs again and turns green. Read its report:

- `addons`, changed: the diff of `AppProject tenants` gains
  `test-platform-hello` among the namespaces Argo CD may deploy to.
- `ns-test-platform-hello`, added: eight objects, the Namespace, its
  ResourceQuota, LimitRange, CiliumNetworkPolicy, two RoleBindings, the
  ListenerSet `apps` and the Certificate.

That is the whole effect of your change on the cluster, before it happens.

## 4. Merge and watch it apply

Merge the pull request. Argo CD polls the repository every three minutes:

```sh
kubectl -n argocd get application ns-test-platform-hello -w
```

You should see it appear and become Synced and Healthy within a few
minutes (Ctrl-C to stop watching). Then:

```sh
kubectl get namespace test-platform-hello --show-labels
kubectl -n test-platform-hello get resourcequota,listenerset,certificate
```

You should see the namespace labelled with its organization, team,
application and environment and with Pod Security `restricted`, an empty
quota, and the ListenerSet and Certificate ready. The team can now deploy to
it.

## 5. Take it away again

Removing is the same path:

```sh
git switch main && git pull
git switch -c hello-test-remove
git rm -r applications/example/platform/hello/env/test
git commit -m "hello: remove environment test" && git push -u origin hello-test-remove
```

Open the pull request. pac-bot updates the namespace lists again, and the
report shows `ns-test-platform-hello` **removed**, with its eight objects.
That is the warning to read before every such merge: removing a namespace
deletes everything in it. Merge it, and within a few minutes
`kubectl get namespace test-platform-hello` finds nothing.

## What you did

You proposed a change, let the merge check generate what follows from it,
saw it block a mistake with the error Argo CD would have shown on the
cluster, and read the exact difference your change makes before merging it.
Every change to this repository goes this way, a team or a Crossplane object
as much as a namespace.

## Next steps

- The everyday version of these steps: [Propose a change](../how-to/propose-a-change.md).
- Everything the check blocks or reports: [Merge checks](../reference/merge-checks.md).
- Why it renders instead of linting: [Rendering before merging](../explanation/merge-checks.md).
- External objects through the same path: [Manage an external object from Git](manage-an-external-object.md).

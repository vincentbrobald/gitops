# Manage an external object from Git

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you create a Keycloak group from this repository, watch
Crossplane make it, change it behind Crossplane's back and see the change
undone, and finally remove it from Git, to find it still in Keycloak. The
same mechanism makes the teams' groups, Forgejo repositories, Harbor projects
and Artifact Keeper repositories.

You need: everything [Your first platform change](your-first-platform-change.md)
needs, and an administrator login to Keycloak's console
(https://oauth.example.org/admin/, realm `example`). The group is named
`tutorial-alice` here: use `tutorial-<your user name>`.

## 1. Describe the group

A Keycloak group is a Crossplane *managed resource* of kind `Group`. Create
`clusters/lab/crossplane/tutorial-group.yaml`:

```yaml
apiVersion: group.keycloak.m.crossplane.io/v1alpha1
kind: Group
metadata:
  name: tutorial-alice
  namespace: crossplane-system
spec:
  managementPolicies: [Observe, Create, Update, LateInitialize]
  providerConfigRef: {kind: ClusterProviderConfig, name: default}
  forProvider:
    realmId: example
    name: tutorial-alice
    description: Made by Crossplane from Git
```

`forProvider` is what the group should be. `managementPolicies` is what
Crossplane may do to it: observe it, create it, update it, and record the ID
Keycloak gives it (`LateInitialize`). `Delete` is missing on purpose.
`providerConfigRef` names the credentials Crossplane uses for Keycloak.

List the file in `clusters/lab/crossplane/kustomization.yaml`, under
`resources`:

```yaml
  - tutorial-group.yaml
```

Commit on a branch, push, and open a pull request. The report shows one
change: `crossplane-providers` gains
`group.keycloak.m.crossplane.io/Group crossplane-system/tutorial-alice`.
Merge it.

## 2. Watch Crossplane make it

Within a few minutes Argo CD applies the object, and Crossplane creates the
group in Keycloak:

```sh
kubectl -n crossplane-system get groups.group.keycloak.m.crossplane.io tutorial-alice
```

You should see `SYNCED True`, `READY True`, and an `EXTERNAL-NAME`: the ID
Keycloak assigned, which Crossplane now uses to find the group. In the
console, under Groups, you should see `tutorial-alice` with the
description from Git.

## 3. Change it behind Crossplane's back

In the console, open the group and change its description to "Changed in the
console". Save. Then wait, refreshing the page now and then.

Within about ten minutes (Crossplane compares every object with the service
at an interval) you should see the description back to "Made by Crossplane
from Git". Git is the source: a change made anywhere else is undone, without
anyone noticing it first.

To change the group, change the file and propose it, like any change.

## 4. Remove it from Git

Remove the file and its line in `kustomization.yaml` on a new branch, and
propose it. The report shows the Group as removed from `crossplane-providers`.
Merge, and after Argo CD's next sync:

```sh
kubectl -n crossplane-system get groups.group.keycloak.m.crossplane.io tutorial-alice
```

You should see "not found". Now look in Keycloak's console: `tutorial-alice`
is still there. Without `Delete` in its policies, Crossplane lets go of the
object instead of deleting it. A file removed by mistake can't destroy a
group, a repository or a registry project that people and systems depend on.

Delete the group by hand in the console to finish.

## What you did

You declared an object in another service as a Kubernetes object, let
Crossplane create it and keep it as declared, and saw the two rules the
platform relies on: Git wins over console edits, and removing something from
Git never deletes it in the service.

## Next steps

- Adopt an object that already exists: [Take over an existing external object](../how-to/take-over-an-existing-object.md).
- A kind not installed yet: [Add or remove a Crossplane kind](../how-to/add-a-crossplane-kind.md).
- What each provider manages: [Crossplane providers](../reference/crossplane-providers.md).
- Why it works this way: [Crossplane](../explanation/crossplane.md).

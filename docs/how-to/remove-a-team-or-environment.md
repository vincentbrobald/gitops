# Remove a team or an environment

> How-to · [Documentation](../../README.md#documentation)

Take an environment, or a whole team, off the platform. What goes and what
stays: [What a team gets](../reference/team-resources.md#when-a-team-is-removed).

## An environment

1. Delete `applications/<org>/<team>/<ns>/env/<env>/` (and the whole `<ns>/`
   if it was the last environment).
2. Commit and [propose the change](propose-a-change.md); the merge check updates the namespace lists.
   The report shows the Namespace going: **everything in it is deleted.**
3. Check: `kubectl get namespace <env>-<team>-<ns>` is not found.

## A team

Two pull requests, so that Argo CD deletes the team's objects while its
project still permits the team's namespaces. Why:
[Multi-tenancy](../explanation/multi-tenancy.md#removing-a-team).

1. Add `removed: true` to `applications/<org>/<team>/team.yaml` and
   [propose the change](propose-a-change.md). The merge check deletes the
   team's generated `argocd/` folder (a commit by pac-bot); the report shows
   the team's Applications and its environments' as removed. Merge.
2. Wait for the cluster to finish:

   ```sh
   kubectl -n argocd get applications -l example.org/team=<team>   # nothing
   kubectl get namespace team-<team> ci-<team>                      # not found
   ```

   Argo CD deletes everything but the namespaces `team-<team>` and
   `ci-<team>`; Crossplane deletes what it may (memberships, deploy keys, the
   CI user, its token, the webhooks, Artifact Keeper permissions); then the
   namespace cleanup deletes the two namespaces, 10 to 15 minutes after the
   merge. `kubectl -n namespace-cleanup logs -l job-name --tail=20` says what
   it waits for.
3. Delete `applications/<org>/<team>/` and propose the change: the merge check
   updates `tenants.yaml`. It refuses this step if `main` doesn't have
   `removed: true` yet.
4. If they should go too, remove by hand what Crossplane leaves (no `Delete`):
   the Keycloak group `team-<team>` and clients `argocd-lab-team-<team>`,
   `tekton-lab-team-<team>`; the Forgejo team and repositories; the Harbor
   project `<team>`; the Artifact Keeper repositories `<team>-*`.

## If a removal stalls

`kubectl -n namespace-cleanup logs job/<latest>` names what the cleanup waits
for. Crossplane objects that stay (`kubectl -n <ns> get managed`) tell why in
their conditions:

```sh
kubectl -n <ns> get managed -o jsonpath='{range .items[*]}{.kind}/{.metadata.name}: {.status.conditions[?(@.type=="Synced")].message}{"\n"}{end}'
```

If the external object is gone already, or may stay, let Crossplane release
the object instead of deleting it:

```sh
kubectl -n <ns> patch <kind>.<group> <name> --type=merge -p '{"spec":{"managementPolicies":["Observe"]}}'
```

Crossplane then removes its finalizer without touching the service. Remove
by hand what it leaves there.

## An application of a team

That is the team's own change: delete its file in `apps/` of `<team>-gitops`;
its Argo CD prunes it.

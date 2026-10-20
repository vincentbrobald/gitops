# Move objects between Applications

> How-to · [Documentation](../../README.md#documentation)

Move live objects from one Application to another (a rename, a split, a new
folder) without Argo CD deleting and recreating them. Argo CD tracks an
object by an annotation naming its Application, so the order of the steps is
what matters.

## Before you start

Record the UIDs of the objects to move:

```sh
kubectl -n argocd get application <old> -o jsonpath='{range .status.resources[*]}{.kind} {.namespace}/{.name}{"\n"}{end}' > objects.txt
# then, per object: kubectl get <kind> <name> -n <ns> -o jsonpath='{.metadata.uid}'
```

A recreated object has a new UID; comparing them at the end proves the move.

## Between two live Applications

1. **Keep:** make the old Application stop pruning the objects. Either add
   `argocd.argoproj.io/sync-options: Prune=false` to them (kustomize
   `commonAnnotations`, a chart template), or set the old Application's
   `syncPolicy.automated.prune: false` in the same change as step 2. Merge.
2. **Move:** take the objects out of the old Application's source and into
   the new one's. Merge. The new Application applies them and rewrites their
   tracking annotation; the old one no longer counts them.
3. **Restore:** remove the `Prune=false` annotation or set `prune: true`
   again. Merge.
4. Check: same UIDs; both Applications Synced, nothing awaiting pruning:

   ```sh
   kubectl -n argocd get application <old> -o jsonpath='{.status.resources[?(@.requiresPruning==true)].name}'
   ```

## Renaming an Application

Look at its finalizers first:

```sh
kubectl -n argocd get application <old> -o jsonpath='{.metadata.finalizers}'
```

| Finalizer | Rename |
|---|---|
| none | safe: remove the old one and add the new one in one change. The old Application is deleted without touching its objects; the new one adopts them |
| `resources-finalizer.argocd.argoproj.io` | deleting the old Application deletes its objects. Keep the name, or use the steps above (an ApplicationSet adds this finalizer to what it generates) |

## Handing objects to a controller

To give objects to a controller outside Argo CD (trust-manager, an operator),
do steps 1 and 2 without a new Application, then remove Argo CD's
annotations from the objects so no Application counts them:

```sh
kubectl annotate <kind> <name> -n <ns> argocd.argoproj.io/tracking-id- argocd.argoproj.io/sync-options-
```

Never let Argo CD and the controller write the same object at once: if their
output differs, they rewrite each other forever.

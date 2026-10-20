# Add or remove a Crossplane kind

> How-to · [Documentation](../../README.md#documentation)

Install a managed-resource kind a provider ships before using it, or remove
one no longer used. Why kinds are activated one by one:
[Crossplane](../explanation/crossplane.md#only-the-kinds-in-use).

## Add a kind

1. Find its MRD name, `<plural>.<group>`:

   ```sh
   kubectl get managedresourcedefinitions | grep -i <kind>
   ```

2. Add it to `spec.activate` in `clusters/lab/crossplane/activation.yaml`, in
   the same pull request as the first object of that kind, or before.
3. [Propose the change](propose-a-change.md).
4. Check after the merge:

   ```sh
   kubectl get managedresourcedefinition <plural>.<group>   # State: Active
   kubectl get crd <plural>.<group>
   ```

Without step 2, objects of the kind fail with "no matches for kind".

If a team chart object uses the kind, also add it to `TENANT_KINDS` in
`tools/teams.py` and run `tools/teams.py generate`, or the project `tenants`
refuses it.

## Remove a kind

An active kind can't be deactivated; it is removed with its CRD, once no
object of the kind exists:

1. Remove it from `activation.yaml` and merge.
2. Check that no object is left: `kubectl get <plural>.<group> -A`.
3. Delete the MRD; Crossplane makes it again, Inactive, at its next reconcile
   of the provider revision:

   ```sh
   kubectl delete managedresourcedefinition <plural>.<group>
   kubectl get managedresourcedefinition <plural>.<group>   # back, State: Inactive
   ```

4. Delete the CRD; it stays gone while the MRD is Inactive:

   ```sh
   kubectl delete crd <plural>.<group>
   ```

# Take over an existing external object

> How-to · [Documentation](../../README.md#documentation)

Let Crossplane manage a Keycloak client, Forgejo repository, Harbor project
or similar that already exists, without changing it. Why this way:
[Crossplane](../explanation/crossplane.md#taking-over-what-exists).

1. Back up the object as the service shows it (its admin API), including IDs
   and secrets, to `/root/lab/lab-secrets/<service>/backups/` (mode 600).
2. Write the managed resource with every setting the object has, its external
   name (the ID the provider uses: a Keycloak client's UUID, `<repo id>/<id>`
   for Forgejo sub-objects), and only `Observe`:

   ```yaml
   metadata:
     annotations:
       crossplane.io/external-name: 0a66a24c-b9ee-42bf-9ce5-a90ec73f2992
   spec:
     managementPolicies: [Observe]
   ```

   References (`...Ref`) aren't resolved while only observing: write IDs
   directly where the object refers to another.
3. [Propose the change](propose-a-change.md) and merge.
4. Compare what Crossplane sees with what you wrote:

   ```sh
   kubectl -n <ns> get <kind> <name> -o yaml   # status.atProvider vs spec.forProvider
   ```

   Fix every difference in the manifest. Providers read some unset values as
   defaults (Keycloak's `useRefreshTokens`: unset means true, read as false):
   set those explicitly.
5. Switch to management and merge:

   ```yaml
   spec:
     managementPolicies: [Observe, Create, Update]
   ```

6. Check: compare the service's own representation with the backup. Expect
   defaults written out explicitly, nothing that changes behaviour; the
   object is `Synced` and `Ready`.

Never add `Delete` to objects others depend on. Document how to hand the
object back (infra's [Hand an object back to Ansible](https://github.com/vincentbrobald/infra/blob/main/docs/how-to/hand-back-to-ansible.md) has examples).

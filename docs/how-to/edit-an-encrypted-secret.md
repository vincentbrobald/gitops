# Edit an encrypted Secret

> How-to · [Documentation](../../README.md#documentation)

Change, add or read a SOPS-encrypted Secret (`*.enc.yaml`). Each folder's
`.sops.yaml` (`clusters/<name>/`, `applications/`) names who its Secrets are
encrypted for.

## Change one

From inside the cluster's folder, with a key that can decrypt:

```sh
cd clusters/lab
SOPS_AGE_KEY_FILE=/root/lab/lab-secrets/sops/admin.agekey sops edit ci/gitops/forgejo-pac.enc.yaml
```

`sops edit` decrypts into your editor and re-encrypts on save. Commit and
[propose the change](propose-a-change.md): the report shows "values changed"
for the key, never the value.

## Add one

1. Write the Secret and encrypt it on its way into the repository, never
   leaving it in clear on disk:

   ```sh
   cd clusters/lab
   kubectl create secret generic my-secret -n my-ns --from-literal=token="$(cat /path/to/token)" \
     --dry-run=client -o yaml \
     | SOPS_AGE_KEY_FILE=/root/lab/lab-secrets/sops/admin.agekey \
       sops encrypt --input-type yaml --output-type yaml --filename-override my-app/secret-my-ns-my-secret.enc.yaml /dev/stdin \
     > my-app/secret-my-ns-my-secret.enc.yaml
   ```

2. List it in the folder's KSOPS generator (`secret-generator.yaml`, `files:`)
   and the generator in its `kustomization.yaml` (`generators:`). In
   `ci/<name>/` folders, `tools/ci.py generate` does this.
3. Propose the change; the report shows the Secret with its key names.

## See which keys one has

```sh
SOPS_AGE_KEY_FILE=/root/lab/lab-secrets/sops/admin.agekey sops decrypt <file> \
  | python3 -c 'import sys,yaml; d=yaml.safe_load(sys.stdin); print(sorted({**(d.get("data") or {}), **(d.get("stringData") or {})}))'
```

Print values only where nobody else sees them.

## Files you don't edit

Secrets under `generated/` belong to deploy-talos.py, and those under
`applications/<org>/<team>/argocd/` to `tools/teams.py`: to replace one,
delete it and run its generator.

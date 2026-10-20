# Create a new site's Secrets

> How-to · [Documentation](../../README.md#documentation)

Every credential of a new site, in the order they depend on each other. Each
step's tool makes what is missing and keeps what exists, so a step can be run
again. Where each Secret ends up: [Encrypted Secrets](../reference/encrypted-secrets.md).
Below, `<secrets>` is the infra playbooks' secrets tree (outside Git) and
`<cluster>` the cluster's name.

1. **Your age key**, which decrypts every Secret in this repository. The
   infra playbooks use it too, to read the credentials kept here:

   ```sh
   mkdir -p <secrets>/sops && age-keygen -o <secrets>/sops/admin.agekey
   age-keygen -y <secrets>/sops/admin.agekey      # its public key: age1...
   ```

   Keep a copy off the host: without it, nothing in Git can be read again.

2. **The services' credentials**: run the infra playbooks
   ([Run the playbooks](https://github.com/vincentbrobald/infra/blob/main/docs/how-to/run-the-playbooks.md)).
   They generate every password, token and key of the services into
   `<secrets>`, including what Crossplane will use: Keycloak's client
   `crossplane-lab`, Forgejo's user `crossplane-lab` and its token, Harbor's
   admin, and an Artifact Keeper API token.

3. **A read-only deploy key for this repository**, which Argo CD and the merge
   check read it with:

   ```sh
   ssh-keygen -q -t ed25519 -N '' -C argocd -f <secrets>/forgejo/gitops-deploy-key
   ```

   Register `gitops-deploy-key.pub` as a read-only deploy key of this
   repository (infra `forgejo.yml`, `deploy_keys`), and name the private key
   in the cluster file (`argocd.repository.auth.sshKeyFile`).

4. **The cluster and its add-ons' Secrets**: `deploy-talos.py create` with
   `argocd.addons.sopsAgeKeyFile` (the cluster's own age key, made if missing)
   and `argocd.addons.sopsRecipients: [<your public key>]`
   ([Keep Secrets in Git](https://github.com/vincentbrobald/talos-install/blob/main/docs/how-to/keep-secrets-in-git.md)).
   It writes `clusters/<cluster>/.sops.yaml` and the add-ons' Secrets
   (`generated/`), and pushes them here. For etcd backups, their own age
   key: [Back up and restore etcd](https://github.com/vincentbrobald/talos-install/blob/main/docs/how-to/back-up-and-restore-etcd.md).

5. **The Secrets no other tool makes**, from the credentials of steps 2 and 3:

   ```sh
   python3 tools/bootstrap.py write --cluster <cluster> --secrets-dir <secrets> \
       --domain example.org --gitops-ssh-key <secrets>/forgejo/gitops-deploy-key
   ```

   It writes the four Crossplane providers' credentials, the merge check's
   deploy key and the Tekton Dashboard's cookie secret, and gives
   `applications/.sops.yaml` the cluster's recipients. Options (host names,
   Keycloak's version): `python3 tools/bootstrap.py --help`.

6. **The teams' and the CI repositories' Secrets**:
   `python3 tools/teams.py generate` and `python3 tools/ci.py generate`
   ([Tools](../reference/tools.md); the merge check runs them too).

7. Commit and [propose the change](propose-a-change.md).

## Check

```sh
SOPS_AGE_KEY_FILE=<secrets>/sops/admin.agekey python3 tools/bootstrap.py check \
    --cluster <cluster> --secrets-dir <secrets> --domain example.org \
    --gitops-ssh-key <secrets>/forgejo/gitops-deploy-key
```

Every line says `same`: the Secrets in Git hold the credentials the services
were set up with. A `differs` means one side changed: the infra playbooks
take a credential from Git when it is there, so run them again, or fix the
Secret ([Edit an encrypted Secret](edit-an-encrypted-secret.md)).

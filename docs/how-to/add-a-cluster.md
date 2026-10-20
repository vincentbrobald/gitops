# Add a cluster

> How-to · [Documentation](../../README.md#documentation)

Deploy a second cluster from this repository, next to `lab`. It gets its own
Argo CD, add-ons, projects and site CA; the site-wide parts (Crossplane, teams,
CI, merge checks) stay on `lab`. Why: [Several clusters](../explanation/several-clusters.md).
The cluster itself is built by deploy-talos.py ([talos-install](https://github.com/vincentbrobald/talos-install)); its site
settings are in infra's [Build a cluster on this site](https://github.com/vincentbrobald/infra/blob/main/docs/how-to/build-a-cluster-on-this-site.md).

The examples use the name `edge`; use yours (1–20 characters of `[a-z0-9-]`).

## 1. Prepare the folder (pull request)

Merge this before building the cluster: deploy-talos.py pushes to the folder
directly, and a folder that no merge-check entry point reaches would fail
every later pull request.

1. **Projects:** create `clusters/edge/addons/projects/`, with copies of
   `lab`'s `default.yaml`, `platform-infra.yaml` and `platform-services.yaml`.
   In `platform-services.yaml`, keep only the namespaces this cluster uses
   (`headlamp`, `ingress`, `talos-backup`). No `preview.yaml` or
   `tenants.yaml`: those belong to `lab`.
2. **Site CA:** copy `clusters/lab/addons/trust-manager.yaml` to
   `clusters/edge/addons/` with its second source's path set to
   `clusters/edge/trust`, and copy `clusters/lab/trust/` to `clusters/edge/trust/`
   (its source includes `base/site-ca`; the relative paths stay valid at the
   same depth).
3. **Anything else the cluster should run:** an overlay
   `clusters/edge/<app>/` including `base/<app>`, patching host names to
   `*.apps.edge.example.org`, and its Application in `clusters/edge/addons/`
   with a project ([Add a platform Application](add-an-application.md)).
   Don't copy `crossplane*`, `registries/`, `teams.yaml`, `ci.yaml`,
   `tekton*`, `pipelines-as-code.yaml` or `argocd-preview.yaml`: they manage
   site-wide objects from `lab`.
4. **Merge check entry point:** in `.gitops-check.yaml`, under `entrypoints`:

   ```yaml
   - name: edge
     cluster: lab          # the in-cluster server, like every cluster's Argo CD
     path: clusters/edge/addons
     recurse: true
   ```

5. [Propose the change](propose-a-change.md). Check: the report lists the new
   folder's Applications (`trust-manager`, ...) and the projects, with no
   "unreached" error.

## 2. Build the cluster

1. Write its cluster file with talos-install (`template`), with this site's
   settings (infra's guide above) and this repository:

   ```yaml
   argocd:
     hostname: argocd.apps.edge.example.org
     repository:
       url: ssh://git@forgejo.example.org:2222/alice/gitops.git
       revision: main
       auth: {method: ssh, sshKeyFile: forgejo-test/deploy_key, knownHosts: auto}
     addons:
       enabled: true                                          # path: clusters/edge
       pushSshKeyFile: lab-secrets/forgejo/gitops-push_key
       sopsAgeKeyFile: lab-secrets/sops/edge.agekey         # created if missing
       sopsRecipients: [age1-replace-with-your-age-public-key]  # the admin key
     application:
       enabled: false        # the app-of-apps 'addons' is the only root
   ```

   The read-only deploy key and the push key are `lab`'s. For a key the new
   cluster doesn't share, add a deploy key to `alice/gitops` in infra's
   `ansible/inventory/group_vars/forgejo.yml` and run `forgejo.yml`.
   Leave `oidc.crossplane` off: the cluster has no Crossplane, so the script
   manages its Headlamp and Grafana clients through Keycloak's API.
2. Build it:

   ```sh
   ./deploy-talos.py plan -f edge.yaml
   ./deploy-talos.py create -f edge.yaml
   ```

   deploy-talos.py writes `clusters/edge/addons/generated/`,
   `clusters/edge/generated/` and `clusters/edge/.sops.yaml`, pushes them to
   `main`, and waits until the add-ons are Synced and Healthy.
3. Register its DNS names (infra's [Register DNS records](https://github.com/vincentbrobald/infra/blob/main/docs/how-to/register-dns-records.md)).

## 3. Check

- On the new cluster: `kubectl -n argocd get applications`: `addons`, the
  generated add-ons and `trust-manager`, all Synced and Healthy.
- `kubectl get cm -A --field-selector metadata.name=site-root-ca | wc -l`: one
  per namespace.
- `https://argocd.apps.edge.example.org` logs you in through Keycloak.
- The next pull request's merge-check report renders both clusters' folders.

## Remove a cluster

Destroy it with deploy-talos.py (`destroy` also removes its generated files
from the repository), then remove the rest of `clusters/edge/` and its entry
point in a pull request. Its Keycloak clients go with `destroy`; its DNS
records with `opnsense-dns.py remove --owner deploy-talos.py:edge`.

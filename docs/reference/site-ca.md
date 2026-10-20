# Site CA

> Reference · [Documentation](../../README.md#documentation)

Where the site's root CA comes from and where workloads find it. Why it is
published this way: [One site CA, through trust-manager](../explanation/site-ca.md).

| Item | Value |
|---|---|
| The file | `base/site-ca/site-root-ca.crt` (from infra `pki/root_ca.crt`; step-ca at `pki.example.org`) |
| Source ConfigMap | `cert-manager/site-root-ca-source` (`clusters/lab/trust/source`) |
| Bundle | `site-root-ca` (`clusters/lab/trust/bundle.yaml`), Application `trust-manager` |
| Target | ConfigMap `site-root-ca`, key `site-root-ca.crt`, in every namespace |
| Contents | the site CA only (no default CAs) |

## Using it in a workload

Mount the ConfigMap and point the program at it:

```yaml
volumes:
  - name: site-ca
    configMap: {name: site-root-ca}
containers:
  - name: app
    env:
      - {name: SSL_CERT_DIR, value: /etc/site-ca}   # Go: added to the image's bundle
    volumeMounts:
      - {name: site-ca, mountPath: /etc/site-ca, readOnly: true}
```

Programs that take a CA file use `/etc/site-ca/site-root-ca.crt`
(e.g. oauth2-proxy's `--provider-ca-file`).

## Copies outside trust-manager

Written by deploy-talos.py from the cluster file:

| Copy | From |
|---|---|
| ConfigMap `oidc-ca` in `headlamp` and `monitoring` | `oidc.caFile` |
| ConfigMap `s3-ca` in `talos-backup` | `talosBackup.s3.caFile` |
| Argo CD's OIDC settings (`argocd-cm`, inline) | `oidc.caFile` |

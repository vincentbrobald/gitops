# Change the site CA

> How-to · [Documentation](../../README.md#documentation)

Replace the site's root CA everywhere it is published. Where it lives:
[Site CA](../reference/site-ca.md). The rules: [One site CA, through trust-manager](../explanation/site-ca.md#rules).

1. Replace `base/site-ca/site-root-ca.crt` with the new certificate (PEM,
   from infra `pki/root_ca.crt`). During a rollover, put both certificates in
   the file, old and new, so that services with either one stay trusted.
2. [Propose the change](propose-a-change.md) and merge.
3. Check that every namespace has it:

   ```sh
   kubectl get cm -A --field-selector metadata.name=site-root-ca \
     -o jsonpath='{range .items[*]}{.data.site-root-ca\.crt}{"\x00"}{end}' \
     | python3 -c 'import sys,hashlib;print(len({hashlib.sha256(x).hexdigest() for x in sys.stdin.buffer.read().split(b"\0") if x}), "distinct")'
   ```

   `1 distinct` means every namespace has the new content.
4. Restart what reads the CA only at start (Crossplane's providers, oauth2-proxies,
   Pipelines-as-Code, the teams' Argo CD servers):

   ```sh
   kubectl -n pipelines-as-code rollout restart deploy
   ```

5. Update the copies deploy-talos.py writes from the cluster file
   (`oidc.caFile`, `talosBackup.s3.caFile`, `registry.caFile`): point them at
   the new file and run `deploy-talos.py argocd -f /root/lab/lab.yaml`.

Never delete the Bundle `site-root-ca` to "reset" it: that deletes the
ConfigMap in every namespace.

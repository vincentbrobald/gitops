# Add a platform Application

> How-to · [Documentation](../../README.md#documentation)

Deploy a new platform service or add-on with the platform Argo CD. For a
team's application, see [Deploy an application](deploy-an-application.md)
instead. Projects: [Argo CD projects](../reference/projects.md).

1. Put shared manifests in `base/<app>/` (no cluster names) and the cluster's
   overlay in `clusters/lab/<app>/`: a `kustomization.yaml` including the base
   and patching host names, URLs and the like, plus the cluster's encrypted
   Secrets ([Edit an encrypted Secret](edit-an-encrypted-secret.md)).
   A Helm chart needs no base: the Application names it.
2. Add the Application, `clusters/lab/addons/<app>.yaml`, with its project:

   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: my-service
     namespace: argocd
     annotations:
       argocd.argoproj.io/compare-options: ServerSideDiff=true
   spec:
     project: platform-services       # platform-infra if it needs anything cluster-wide
     source:
       repoURL: ssh://git@forgejo.example.org:2222/alice/gitops.git
       targetRevision: main
       path: clusters/lab/my-service
     destination:
       server: https://kubernetes.default.svc
       namespace: my-service
     syncPolicy:
       automated: {prune: true, selfHeal: true}
       syncOptions: [CreateNamespace=true, ServerSideApply=true]
       retry: {limit: 10, backoff: {duration: 10s, factor: 2, maxDuration: 3m}}
   ```

   If its objects use kinds another Application installs (Crossplane's,
   Pipelines-as-Code's), add `SkipDryRunOnMissingResource=true` to its
   `syncOptions`.
3. Let its project allow it:
   - `platform-services`: add the namespace to `addons/projects/platform-services.yaml`;
   - a chart from a repository not yet used: add the repository to the
     project's `sourceRepos`.
4. [Propose the change](propose-a-change.md). The report shows the new
   Application and everything it renders; a destination or source the project
   doesn't allow is an error there.
5. Check after the merge: `kubectl -n argocd get application my-service`
   Synced and Healthy.

## Serve it over HTTPS

The cluster's ingress gateway terminates TLS for host names listed in the
cluster file (`certManager.extraHosts`, deploy-talos.py). Add the host there,
run deploy-talos.py, and attach the HTTPRoute to the listener `https-<first label>`.

## It calls the site's services

Mount ConfigMap `site-root-ca` (present in every namespace): [Site CA](../reference/site-ca.md#using-it-in-a-workload).

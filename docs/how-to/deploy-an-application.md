# Deploy an application (team)

> How-to · [Documentation](../../README.md#documentation)

For a team: deploy an application into one of your environments with your
own Argo CD. The environment must exist ([Add an environment](add-an-environment.md),
done by the platform). Rules in your namespaces: [Team namespaces](../reference/team-namespaces.md).

1. In an application repository `<org>/<team>-...`, write the manifests:
   a base and one overlay per environment, e.g.

   ```
   deploy/base/   Deployment, Service, HTTPRoute
   deploy/dev/    kustomization.yaml: namespace dev-<team>-<ns>, patches
   ```

   - Pods pass Pod Security `restricted`: non-root, no privilege escalation,
     all capabilities dropped, `seccompProfile: RuntimeDefault`, ports above 1024.
   - Images from `registry.example.org`: upstream images through Harbor's
     proxy caches (`registry.example.org/docker.io/...`), your own from
     project `<team>`.
   - Requests and limits, or the namespace's defaults apply and count
     against its quota.
2. Route traffic through the environment's listener (no `hostnames` needed):

   ```yaml
   apiVersion: gateway.networking.k8s.io/v1
   kind: HTTPRoute
   metadata: {name: my-app}
   spec:
     parentRefs: [{group: gateway.networking.k8s.io, kind: ListenerSet, name: apps, sectionName: <team>-my-app-dev}]
     rules: [{backendRefs: [{name: my-app, port: 80}]}]
   ```

3. In `<team>-gitops`, add `apps/<app>-<env>.yaml`:

   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: my-app-dev
   spec:
     project: default
     source:
       repoURL: ssh://git@forgejo.example.org:2222/<org>/<team>-my-app.git
       targetRevision: main
       path: deploy/dev
     destination:
       server: https://kubernetes.default.svc
       namespace: dev-<team>-my-app
     syncPolicy:
       automated: {prune: true, selfHeal: true}
   ```

   Use the SSH URL above: your Argo CD's credential is for
   `<org>/<team>-*` over SSH only.
4. Push both. Check: in `https://argocd-<team>.apps.lab.example.org` the
   Application is Synced and Healthy (polling every three minutes; "Refresh" is
   immediate), and the host name answers.

To stop deploying it, delete its file in `apps/`: your Argo CD prunes it.
Something refused? [Troubleshoot a team deployment](troubleshoot-a-team-deployment.md).

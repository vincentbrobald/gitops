# Add an environment

> How-to · [Documentation](../../README.md#documentation)

Give a team's application a namespace `<env>-<team>-<ns>`, optionally with
host names and a bigger quota. What every environment gets:
[Team namespaces](../reference/team-namespaces.md).

1. If the application has no base yet, create
   `applications/<org>/<team>/<ns>/base/kustomization.yaml`, shared by its
   environments:

   ```yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization
   resources: [../../../../../base/team-namespace]
   ```

2. Create the environment, `applications/<org>/<team>/<ns>/env/<env>/kustomization.yaml`,
   an overlay of the base:

   ```yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization
   resources:
     - ../../base
     - listeners.yaml              # without host names: leave it out
   components: [../../../../../../base/team-namespace/sizes/medium]   # optional: medium or large
   ```

3. For host names, add `env/<env>/listeners.yaml`: a ListenerSet `apps` with
   one HTTPS listener per host name, named after its first label, and a
   Certificate for each (copy `applications/example/platform/hello/env/dev/listeners.yaml`).
   Host names start with `<team>-` and end in `.apps.lab.example.org`.
4. Commit and [propose the change](propose-a-change.md). The merge check
   updates the namespace lists (the team's Argo CD and the project `tenants`
   learn the namespace) and commits them to your branch; its report shows the
   new Application `ns-<env>-<team>-<ns>`.
5. Check after the merge:

   ```sh
   kubectl get namespace <env>-<team>-<ns>
   kubectl -n <env>-<team>-<ns> get listenerset,certificate
   ```

The team can now deploy there ([Deploy an application](deploy-an-application.md)).

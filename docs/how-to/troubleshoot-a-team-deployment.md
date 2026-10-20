# Troubleshoot a team deployment

> How-to · [Documentation](../../README.md#documentation)

Find why a team's application or pipeline is refused. The rules behind these
errors: [Team namespaces](../reference/team-namespaces.md),
[CI runs](../reference/ci-runs.md).

| Symptom | Cause | Fix |
|---|---|---|
| the team's Argo CD: "namespace ... is not managed" | the destination isn't one of the team's namespaces | use `team-<team>` or one of the team's environments; a new one needs [an environment](add-an-environment.md) |
| the team's Argo CD: authentication required | the repository is outside `<org>/<team>-*`, or an HTTPS URL | use `ssh://git@forgejo.example.org:2222/<org>/<team>-...` |
| ReplicaSet events: forbidden by Pod Security | a root pod, a privileged container, missing `seccompProfile` | follow Pod Security `restricted` |
| sync: denied by `team-routes` | a route on the shared gateway or another namespace's listener | attach to the ListenerSet `apps` of the route's own namespace |
| sync: forbidden for the kind | a quota, network policy, Gateway, ListenerSet or Crossplane object | those are the platform's; ask for them in `applications/` |
| pods `Pending`, quota exceeded | the namespace's quota is used up | lower requests, or ask for size `medium` or `large` |
| a host name doesn't answer | the listener or its certificate isn't ready | `kubectl -n <ns> get listenerset,certificate` |
| a pull request gets no run | its author isn't in the Forgejo team | a member comments `/ok-to-test` |
| TaskRun: forbidden by Pod Security (baseline) | a privileged step, or one with host access | build images with kaniko, not Docker-in-Docker |
| a team member is missing in Forgejo | they never logged in to Forgejo | they log in once; `kubectl -n team-<team> get teammember` |
| Artifact Keeper permissions waiting | the group `team-<team>` doesn't exist there yet | a member logs in to Artifact Keeper once |

## Look

```sh
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail
kubectl -n <ns> describe replicaset <name>
kubectl -n ci-<team> get pipelineruns,taskruns
```

Members see their namespaces with their Keycloak login (`view`: no Secrets).

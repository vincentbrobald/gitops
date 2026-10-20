# Add a team

> How-to · [Documentation](../../README.md#documentation)

Give a new team its Argo CD, repositories, CI and registry project. For a
guided first time: [Onboard a team](../tutorials/onboard-a-team.md). Keys and
names: [Team files](../reference/team-files.md).

1. If the organization is new, create `applications/<org>/organization.yaml`
   (copy `applications/example/organization.yaml`).
2. Create `applications/<org>/<team>/team.yaml`:

   ```yaml
   description: What the team does
   members: [alice, bob]          # Keycloak user names
   repositories: [<team>-api]     # besides <team>-gitops; may be []
   ```

3. Commit `team.yaml` and [propose the change](propose-a-change.md). The merge
   check generates the team's keys and Secrets (`<team>/argocd/`) and
   `clusters/lab/addons/projects/tenants.yaml`, commits them to your branch
   as pac-bot, and checks again. (Or run `python3 tools/teams.py generate`
   yourself first: [tools](../reference/tools.md#what-generate-needs).)
4. Check after the merge:
   - `kubectl -n argocd get applications -l example.org/team=<team>`: four
     Applications Synced and Healthy. `team-<team>-packages` stays Degraded
     until a member logs in to Artifact Keeper once (its group appears there
     then);
   - `https://argocd-<team>.apps.lab.example.org` lets the members in;
   - the Forgejo team `<team>` and its repositories exist.

A member without a Forgejo account yet appears in the team at their first
login (`kubectl -n team-<team> get teammember`).

## Add a member or a repository

Edit `members` or `repositories` in `team.yaml` and propose the change; the
merge check adds what a new repository needs (a deploy key).

## Replace a team's keys or secrets

| To replace | Delete in a pull request (the merge check makes new ones) |
|---|---|
| the Argo CD deploy key | `deploy-keys.yaml` and `repo-credentials.enc.yaml` |
| the CI user's password and the webhooks' secret | `ci-bot.enc.yaml`, `ci-webhook.enc.yaml`, `ci-webhook-pac.enc.yaml` |
| the Dashboard's cookie secret (signs everyone out) | `tekton-dashboard.enc.yaml` |

Next: [give it an environment](add-an-environment.md).

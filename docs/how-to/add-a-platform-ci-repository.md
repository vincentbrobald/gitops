# Add a platform CI repository

> How-to · [Documentation](../../README.md#documentation)

Have Pipelines-as-Code run the pipelines of one of the platform's own
repositories. Keys and generated Secrets: [Platform CI repositories](../reference/ci-repository.md).
Teams' repositories don't need this: the team chart does it.

1. Make sure the repository exists on Forgejo (infra `forgejo.yml`, which also
   gives `crossplane-lab` access when Crossplane manages its settings), and,
   for a Harbor robot, its project exists in `clusters/lab/registries/harbor/projects.yaml`.
2. Create `clusters/lab/ci/<name>/repository.yaml` (copy one next to it):

   ```yaml
   repository: alice/my-tool
   namespace: my-tool
   forgejo:
     repositoryId: 23        # GET /api/v1/repos/alice/my-tool, field id
   harbor:
     project: providers
     robot: my-tool-ci
   ```

3. Add the namespace to the project `platform-services`,
   `clusters/lab/addons/projects/platform-services.yaml`:

   ```yaml
   - server: https://kubernetes.default.svc
     namespace: my-tool
   ```

4. Commit and [propose the change](propose-a-change.md). The merge check makes
   the Secrets (pac-bot's token and a new webhook secret, a robot password)
   and the generated files, commits them to your branch, and checks again;
   the report shows the Application `ci-<name>`.
5. Check after the merge: the repository has a webhook to
   `pac.apps.lab.example.org`, and a push with a `.tekton/` PipelineRun shows
   a status on the commit.

## Settings that already exist

If the collaborator, webhook or deploy keys exist already, write their
external names (`<repository id>/<id>`) so that Crossplane adopts them instead
of creating duplicates ([keys](../reference/ci-repository.md#repositoryyaml)).

## More Secrets for its pipelines

Add `*.enc.yaml` files to the folder (encrypted with sops for the cluster) and
propose the change: the merge check lists them in the generated
`secret-generator.yaml`.

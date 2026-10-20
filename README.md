# gitops

What Argo CD deploys on the clusters of this site: the platform's services,
its teams and their environments, and the settings of the site's services
(Keycloak, Forgejo, Harbor, Artifact Keeper) through Crossplane.

- One folder per cluster, `clusters/<name>/`, synced by a single root
  Application; shared content in `base/`.
- Teams are data: `applications/<org>/<team>/team.yaml` gives a team its own
  Argo CD, repositories, CI and registry project.
- `main` changes through pull requests only, each rendered before and after
  by a merge check that blocks on errors.

New here? Platform admins start with [Onboard a team](docs/tutorials/onboard-a-team.md);
team members with [Ship your first change](docs/tutorials/ship-your-first-change.md).

## Documentation

The documentation follows [Diátaxis](https://diataxis.fr/): tutorials to
learn, how-to guides for tasks, reference to look things up, explanation to
understand.

**Tutorials**

| For | Tutorial | You learn |
|---|---|---|
| platform admins | [Onboard a team](docs/tutorials/onboard-a-team.md) | a team and an environment from two small files, the team's first build and deployment, removing it |
| platform admins | [Your first platform change](docs/tutorials/your-first-platform-change.md) | a pull request through the merge check: the generated files, a blocked mistake, the report, the merge |
| platform admins | [Manage an external object from Git](docs/tutorials/manage-an-external-object.md) | a Keycloak group through Crossplane: created, kept as declared, left in place when removed |
| team members | [Ship your first change](docs/tutorials/ship-your-first-change.md) | your team's tools, a change from pull request to the running page, taking it back |

**How-to guides: platform admins**

| Task | Guide |
|---|---|
| Change anything | [Propose a change](docs/how-to/propose-a-change.md) |
| A new team, member or repository | [Add a team](docs/how-to/add-a-team.md) |
| A namespace for a team's application | [Add an environment](docs/how-to/add-an-environment.md) |
| Take a team or environment away | [Remove a team or an environment](docs/how-to/remove-a-team-or-environment.md) |
| CI for one of the platform's repositories | [Add a platform CI repository](docs/how-to/add-a-platform-ci-repository.md) |
| A new platform service or add-on | [Add a platform Application](docs/how-to/add-an-application.md) |
| A Crossplane kind not installed yet | [Add or remove a Crossplane kind](docs/how-to/add-a-crossplane-kind.md) |
| Manage something that already exists in Keycloak, Forgejo, Harbor | [Take over an existing external object](docs/how-to/take-over-an-existing-object.md) |
| Rename, split or move Applications without recreating objects | [Move objects between Applications](docs/how-to/move-objects-between-applications.md) |
| A Secret | [Edit an encrypted Secret](docs/how-to/edit-an-encrypted-secret.md) |
| A new root CA | [Change the site CA](docs/how-to/change-the-site-ca.md) |
| Another cluster deployed from this repository | [Add a cluster](docs/how-to/add-a-cluster.md) |
| New Tekton, Pipelines-as-Code or Dashboard release | [Upgrade Tekton](docs/how-to/upgrade-tekton.md) |

**How-to guides: teams**

| Task | Guide |
|---|---|
| Ship an application | [Deploy an application](docs/how-to/deploy-an-application.md) |
| Pipelines, images, packages | [Build with CI](docs/how-to/build-with-ci.md) |
| Something is refused | [Troubleshoot a team deployment](docs/how-to/troubleshoot-a-team-deployment.md) |

**Reference**
- [Repository layout](docs/reference/layout.md): what lives where, who writes it, every Application
- [Team files](docs/reference/team-files.md): `organization.yaml`, `team.yaml`, names, generated files
- [What a team gets](docs/reference/team-resources.md): everything made for a team, by Application
- [Team namespaces](docs/reference/team-namespaces.md): quotas, permissions, admission policies, host names, Pod rules
- [CI runs](docs/reference/ci-runs.md): what a team's pipeline gets and may use
- [Platform CI repositories](docs/reference/ci-repository.md): `repository.yaml`, its Secrets
- [Argo CD projects](docs/reference/projects.md): what each Application may deploy
- [Crossplane providers](docs/reference/crossplane-providers.md): what each manages, credentials, provider configs
- [Namespace cleanup](docs/reference/namespace-cleanup.md): which namespaces it deletes, when, with which rights
- [Merge checks](docs/reference/merge-checks.md): the steps, what blocks, `.gitops-check.yaml`
- [Tools](docs/reference/tools.md): `teams.py`, `ci.py`, `generated.py`
- [Site CA](docs/reference/site-ca.md): where the CA comes from, how to use it
- [Encrypted Secrets](docs/reference/encrypted-secrets.md): every SOPS Secret, its keys, who makes it

**Explanation**
- [Design decisions](docs/explanation/design-decisions.md): the choices, the alternatives considered, when to revisit them
- [Architecture](docs/explanation/architecture.md): one root per cluster, two writers, data instead of manifests
- [Several clusters](docs/explanation/several-clusters.md): what each cluster has, what exists once for the site
- [Multi-tenancy](docs/explanation/multi-tenancy.md): what teams control, what the platform keeps, and why
- [Crossplane](docs/explanation/crossplane.md): external objects from Git, and the conventions that keep it safe
- [Bounded Applications](docs/explanation/projects.md): why every Application belongs to a restricted project
- [One site CA, through trust-manager](docs/explanation/site-ca.md): one source for every namespace, and its rules
- [Rendering before merging](docs/explanation/merge-checks.md): why every change is rendered before it merges

The clusters themselves, and the files marked `Generated by deploy-talos.py`,
come from deploy-talos.py: see [talos-install](https://github.com/vincentbrobald/talos-install).

## License

MIT (LICENSE), © 2026 Vincent Brobald.

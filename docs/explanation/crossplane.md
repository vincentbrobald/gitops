# Crossplane

> Explanation · [Documentation](../../README.md#documentation)

Why external objects (Keycloak, Forgejo, Harbor, Artifact Keeper) are
Crossplane objects in this repository, and the conventions that keep that
safe. Which provider manages what: [Crossplane providers](../reference/crossplane-providers.md).

## Why Crossplane

Ansible sets the services up; after that, what lives *inside* them (clients,
groups, organizations, repositories, projects) is declared here, next to the
workload that needs it, and reconciled continuously. A console edit is
undone; a deleted object comes back; a team's whole footprint is one folder.
Crossplane's providers run in the cluster, so the same pull request and merge
check govern a Keycloak client and a Deployment.

## No Delete for what matters

Managed resources here use `managementPolicies: [Observe, Create, Update]`.
Without `Delete`, removing the Kubernetes object (from Git, or by pruning)
leaves the external object in place. Namespaced resources of Crossplane v2
have no `deletionPolicy`; this is how they orphan. The cost is manual cleanup;
the gain is that a mistaken removal can't destroy a repository, a project or
a client other systems depend on.

## IDs the server assigns

A Keycloak group or client, a Forgejo team or repository, a Harbor project
get their ID from the server. Crossplane records it (the external name) in an
update after creation, and only with `LateInitialize` in the policies; without
it, after a provider restart, the object would be created again. So:
`LateInitialize`, unless the external name is written in the manifest.

## Taking over what exists

An object that already exists is adopted by writing its external name and
starting in `[Observe]`: Crossplane reads it and reports what it sees in
`status.atProvider`, changing nothing. Providers write defaults out
explicitly that the service leaves unset (Keycloak's `use.refresh.tokens`, for
one), so the service's own representation is compared too. Only then come
`Create` and `Update`, so that taking over changes no behaviour.

## Ordering without sync waves

An Application whose objects use kinds another Application installs
(Crossplane's managed resources, Pipelines-as-Code's Repository) sets
`SkipDryRunOnMissingResource=true` in its own `syncOptions` and retries until
the kinds exist. Sync waves between Applications wouldn't help: Argo CD
doesn't wait on a child Application's health.

## Only the kinds in use

Providers bring hundreds of kinds; a ManagedResourceActivationPolicy installs
only those listed in `crossplane/activation.yaml` (the chart's default
"everything" policy is off). That keeps the API server's CRD count and memory
down. The price: a new kind must be activated before its first object, and an
active kind can't be deactivated, only deleted with its CRD.

## Forgejo is private

Nothing on this Forgejo is visible without signing in (`REQUIRE_SIGNIN_VIEW`):
a "public" repository is one every signed-in user can read.

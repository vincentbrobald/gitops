# One site CA, through trust-manager

> Explanation · [Documentation](../../README.md#documentation)

Why the site's root CA reaches workloads through trust-manager, and the rules
that follow. The facts: [Site CA](../reference/site-ca.md). To replace it:
[Change the site CA](../how-to/change-the-site-ca.md).

## Why workloads need it

The site's services (Forgejo, Keycloak, Harbor, Artifact Keeper) have
certificates from the site's own CA, which no image trusts. Every workload
that calls them over HTTPS (Crossplane's providers, Pipelines-as-Code, the
Dashboards' oauth2-proxies, the teams' Argo CDs, every CI run) needs the CA
next to it.

## One source

Rather than each Application making its own copy, one file and
[trust-manager](https://cert-manager.io/docs/trust/trust-manager/) serve
them all: a Bundle publishes the file as ConfigMap `site-root-ca` into every
namespace, new ones included, and rewrites it when the file changes. A new
team, environment or CI repository has the CA without asking for it, and
replacing the CA is one change.

The bundle holds the site CA only, not a default CA set: consumers add it to
their image's own trust store (`SSL_CERT_DIR`) rather than replace it.

## Rules

- **Nothing else writes `site-root-ca`.** trust-manager writes the
  certificate without the file's trailing newline. An Application making
  its own copy would differ by that byte, and Argo CD and trust-manager
  would rewrite each other's ConfigMap forever.
- **Don't delete the Bundle.** trust-manager sets the Bundle as owner of
  every `site-root-ca`; deleting the Bundle garbage-collects all of them.
  Change it instead.
- **Restarts after a change.** trust-manager updates the ConfigMaps at once,
  and mounted files follow, but programs that read the CA only at start keep
  the old one until restarted.

## Copies that remain

deploy-talos.py writes three copies from the cluster file (`oidc-ca`,
`s3-ca`, Argo CD's OIDC settings): they belong to the add-ons it renders, and
Argo CD's OIDC settings take the CA only inline.

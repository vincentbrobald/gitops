#!/usr/bin/env python3
"""Organizations, teams and their application namespaces (applications/):
check the layout and write the generated files.

    python3 tools/teams.py generate   # write applications/<org>/<team>/argocd/
    python3 tools/teams.py check      # what the merge check runs: fails when a
                                     # file is invalid or a generated file stale

The merge check also runs `generate` (the target branch's copy, on the pull
request's files: GITOPS_ROOT) and commits what it writes, so running it by
hand is optional. Encrypting needs only the public keys of .sops.yaml.

Layout (docs/reference/team-files.md, docs/reference/team-namespaces.md):

    applications/
      .sops.yaml                         who the teams' Secrets are encrypted for
      <org>/organization.yaml            a Forgejo organization: forgejo, keycloak.realm, owners
      <org>/<team>/team.yaml             a team: description, members, repositories
      <org>/<team>/argocd/               generated, see below
      <org>/<team>/<namespace>/base/kustomization.yaml       the namespace's base (includes base/team-namespace)
      <org>/<team>/<namespace>/env/<env>/kustomization.yaml  an environment: an overlay of ../../base
                                         → namespace <env>-<team>-<namespace>

The ApplicationSets (clusters/<cluster>/addons/teams.yaml) iterate this tree.
What they can't derive is generated into applications/<org>/<team>/argocd/:
- argocd-namespaces.yaml: values of the team's Argo CD, its "in-cluster"
  destination limited to team-<team> (its Applications) and the team's
  environment namespaces;
- deploy-keys.yaml: one read-only deploy key on each of the team's
  repositories (Crossplane), and repo-credentials.enc.yaml its private half,
  an Argo CD credential template for <org>/<team>-* (SOPS-encrypted, made
  once with ssh-keygen and sops: set SOPS to the sops binary if it is not on
  PATH). To replace the key, delete both files and generate.
- ci-bot.enc.yaml, ci-webhook.enc.yaml, ci-webhook-pac.enc.yaml: the team's CI
  (base/team, ci.yaml): the password of its Forgejo user ci-<team> (Secret
  forgejo-bot) and the secret of its repositories' webhooks to
  Pipelines-as-Code (Secret forgejo-webhook for Forgejo, pac-webhook in
  ci-<team> for Pipelines-as-Code), random, made once (SOPS). To replace them,
  delete the three files and generate.
- clusters/<cluster>/addons/projects/tenants.yaml: the platform Argo CD's
  AppProject of the ApplicationSets' Applications, limited to the
  organizations', teams' (team-, ci-) and environment namespaces of the tree
  and to the kinds the team chart and base/team-namespace use (TENANT_KINDS;
  docs/reference/projects.md).
- tekton-dashboard.enc.yaml: the cookie secret of the oauth2-proxy in front
  of the team's Tekton Dashboard (base/team, dashboard.yaml), random, made
  once (SOPS). Delete it and generate to replace it (signs everyone out).

Removing a team takes two changes (docs/how-to/remove-a-team-or-environment.md):
first `removed: true` in its team.yaml (the ApplicationSets drop its
Applications while the tenants project still permits its namespaces;
`generate` deletes its argocd/, which nothing reads any more), then deleting
its folder. `check` refuses a team folder deleted without the first
step: it compares with the target branch (GITOPS_BASE, default origin/main).

Names: organizations, teams and namespaces are lower-case DNS labels; teams
are unique across organizations (namespaces and Keycloak groups use them);
host names in an environment's ListenerSet start with "<team>-" and are
unique.
"""
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# The gitops checkout: GITOPS_ROOT, or the repository this script is in.
ROOT = Path(os.environ.get("GITOPS_ROOT") or Path(__file__).resolve().parent.parent).resolve()
APPS = ROOT / "applications"
# Name rules: lower-case DNS labels of at most 30 (organizations, namespaces)
# and 20 (teams) characters; environments: a letter then up to 7 letters or
# digits; repositories: Forgejo-style names of at most 100 characters.
ORG = re.compile(r"^[a-z]([a-z0-9-]{0,28}[a-z0-9])?$")
TEAM = re.compile(r"^[a-z]([a-z0-9-]{0,18}[a-z0-9])?$")
NS = re.compile(r"^[a-z]([a-z0-9-]{0,28}[a-z0-9])?$")
ENV = re.compile(r"^[a-z][a-z0-9]{0,7}$")
REPO = re.compile(r"^[a-z0-9]([a-z0-9._-]{0,98}[a-z0-9])?$")
# Folder names in a team folder that are not namespaces (argocd/ is generated).
RESERVED = {"argocd"}
# Harbor projects of the platform (clusters/<cluster>/harbor): a team's
# project is named after it, so no team may take these names.
RESERVED_TEAMS = {"library", "providers", "gitops-scanner", "pac-demo"}
# Forgejo's addresses, the generated files of each team (CI_FILES and
# DASHBOARD_FILE in argocd/) and this repository's URL (a source of the
# tenants project).
FORGEJO_SSH = "ssh://git@forgejo.example.org:2222"
FORGEJO_URL = "https://forgejo.example.org"
CI_FILES = ("ci-bot.enc.yaml", "ci-webhook.enc.yaml", "ci-webhook-pac.enc.yaml")
DASHBOARD_FILE = "tekton-dashboard.enc.yaml"
GITOPS = f"{FORGEJO_SSH}/alice/gitops.git"
# What the tenants project permits (docs/reference/projects.md): cluster-scoped, the
# namespaces and the teams' CI logins to Forgejo (ClusterProviderConfig
# ci-<team>, names bounded by the admission policy team-forgejo); namespaced,
# what base/team, its Argo CD chart (hooks too: the Job argocd-redis-secret-init)
# and base/team-namespace render.
TENANT_CLUSTER_KINDS = [("", "Namespace"), ("forgejo.m.crossplane.brobald.be", "ClusterProviderConfig")]
TENANT_KINDS = [
    ("", "ConfigMap"), ("", "LimitRange"), ("", "ResourceQuota"), ("", "Secret"), ("", "Service"),
    ("", "ServiceAccount"), ("apps", "Deployment"), ("apps", "StatefulSet"), ("batch", "Job"), ("argoproj.io", "Application"),
    ("rbac.authorization.k8s.io", "Role"), ("rbac.authorization.k8s.io", "RoleBinding"),
    ("networking.k8s.io", "NetworkPolicy"), ("cilium.io", "CiliumNetworkPolicy"),
    ("cert-manager.io", "Certificate"), ("gateway.networking.k8s.io", "HTTPRoute"),
    ("gateway.networking.k8s.io", "ListenerSet"), ("pipelinesascode.tekton.dev", "Repository"),
    ("artifactkeeper.crossplane.brobald.be", "Permission"), ("artifactkeeper.crossplane.brobald.be", "Repository"),
    ("artifactkeeper.crossplane.brobald.be", "ServiceAccount"), ("artifactkeeper.crossplane.brobald.be", "Token"),
    ("group.keycloak.m.crossplane.io", "Group"), ("group.keycloak.m.crossplane.io", "Memberships"),
    ("openidclient.keycloak.m.crossplane.io", "Client"),
    ("openidgroup.keycloak.m.crossplane.io", "GroupMembershipProtocolMapper"),
    ("harbor.m.crossplane.io", "Project"), ("project.harbor.m.crossplane.io", "MemberGroup"),
    ("robot.harbor.m.crossplane.io", "Account"),
    ("organization.forgejo.m.crossplane.brobald.be", "Organization"),
    ("organization.forgejo.m.crossplane.brobald.be", "OrganizationOwner"),
    ("organization.forgejo.m.crossplane.brobald.be", "Team"),
    ("organization.forgejo.m.crossplane.brobald.be", "TeamMember"),
    ("repository.forgejo.m.crossplane.brobald.be", "DeployKey"),
    ("repository.forgejo.m.crossplane.brobald.be", "Repository"),
    ("repository.forgejo.m.crossplane.brobald.be", "TeamRepository"),
    ("repository.forgejo.m.crossplane.brobald.be", "Webhook"),
    ("user.forgejo.m.crossplane.brobald.be", "PersonalAccessToken"),
    ("user.forgejo.m.crossplane.brobald.be", "User"),
]
HEADER = "# Generated by tools/teams.py: do not edit, run 'python3 tools/teams.py generate'\n# (the merge check compares).\n"


def load(path: Path, errors: list[str]) -> dict | None:
    """Return the YAML mapping in path, or None with a message appended to errors if it isn't one."""
    rel = path.relative_to(ROOT)
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        errors.append(f"{rel}: not YAML: {e}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{rel}: not a mapping")
        return None
    return data


def yaml_docs(path: Path) -> list:
    """Return the mapping documents of the YAML file path; [] if it doesn't parse (no error reported)."""
    try:
        return [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
    except yaml.YAMLError:
        return []


class Team:
    """A team folder applications/<org>/<name>/ as scan() found it.

    repos: its repositories, <name>-gitops first; namespaces: its environment
    namespaces (<env>-<name>-<namespace>), in folder order; removed: its
    team.yaml says removed: true.
    """

    def __init__(self, org: str, name: str, repos: list[str]):
        self.org, self.name, self.repos = org, name, repos
        self.namespaces: list[str] = []
        self.removed = False

    @property
    def dir(self) -> Path:
        """The team's folder, applications/<org>/<team>."""
        return APPS / self.org / self.name


def scan() -> tuple[list[Team], list[str]]:
    """Walk applications/ and return its teams and the layout errors found.

    Checks names, the files allowed at each level, team.yaml, each namespace's
    base and environment overlays, and the ListenerSet host names. A folder
    with an invalid name, a reserved or duplicate team, or a missing or
    invalid team.yaml is reported and skipped; other errors are reported
    while the team is still returned. Reads files only.
    """
    errors: list[str] = []
    teams: list[Team] = []
    # Team name -> its folder, and host name -> the file that claims it, for
    # uniqueness across the whole tree.
    seen: dict[str, str] = {}
    hosts: dict[str, str] = {}
    if not APPS.is_dir():
        return teams, errors
    for f in sorted(APPS.iterdir()):
        if f.is_file() and f.name != ".sops.yaml":
            errors.append(f"applications/{f.name}: only organization directories belong here")
    for od in sorted(p for p in APPS.iterdir() if p.is_dir()):
        rel = od.relative_to(ROOT)
        if not ORG.match(od.name):
            errors.append(f"{rel}: an organization name is a lower-case DNS label of at most 30 characters")
            continue
        if not (od / "organization.yaml").is_file():
            errors.append(f"{rel}: no organization.yaml")
        for f in sorted(p for p in od.iterdir() if p.is_file() and p.name != "organization.yaml"):
            errors.append(f"{f.relative_to(ROOT)}: only organization.yaml and team directories belong here")
        for td in sorted(p for p in od.iterdir() if p.is_dir()):
            trel = td.relative_to(ROOT)
            if not TEAM.match(td.name):
                errors.append(f"{trel}: a team name is a lower-case DNS label of at most 20 characters")
                continue
            if td.name in RESERVED_TEAMS:
                errors.append(f"{trel}: {td.name} is a Harbor project of the platform (RESERVED_TEAMS)")
                continue
            if td.name in seen:
                errors.append(f"{trel}: team {td.name} exists already in {seen[td.name]} (team names are unique)")
                continue
            seen[td.name] = str(trel)
            if not (td / "team.yaml").is_file():
                errors.append(f"{trel}: no team.yaml")
                continue
            t = load(td / "team.yaml", errors)
            if t is None:
                continue
            r = t.get("repositories")
            if not isinstance(r, list) or not all(isinstance(x, str) for x in r):
                errors.append(f"{trel}/team.yaml: repositories must be a list (may be empty)")
                r = []
            # Repositories are named <team>-...; <team>-gitops is added by
            # default, so listing it is an error too.
            for x in r:
                if not (x.startswith(f"{td.name}-") and REPO.match(x)) or x == f"{td.name}-gitops":
                    errors.append(f"{trel}/team.yaml: repository {x!r}: must start with '{td.name}-' "
                                  f"({td.name}-gitops is always there)")
            team = Team(od.name, td.name, [f"{td.name}-gitops"] + sorted(set(r)))
            team.removed = t.get("removed") is True
            teams.append(team)
            for f in sorted(p for p in td.iterdir() if p.is_file() and p.name != "team.yaml"):
                errors.append(f"{f.relative_to(ROOT)}: only team.yaml, argocd/ and namespace directories belong here")
            for nd in sorted(p for p in td.iterdir() if p.is_dir() and p.name not in RESERVED):
                nrel = nd.relative_to(ROOT)
                if not NS.match(nd.name):
                    errors.append(f"{nrel}: a namespace name is a lower-case DNS label of at most 30 characters")
                    continue
                base = nd / "base"
                if not (base / "kustomization.yaml").is_file():
                    errors.append(f"{nrel}: no base/kustomization.yaml (the namespace's base)")
                for f in sorted(p for p in nd.iterdir() if p.name not in ("base", "env")):
                    errors.append(f"{f.relative_to(ROOT)}: only base/ and env/<env>/ belong in a namespace directory")
                envs = sorted(p for p in (nd / "env").iterdir() if p.is_dir()) if (nd / "env").is_dir() else []
                if not envs:
                    errors.append(f"{nrel}: no environment (env/<env>/kustomization.yaml)")
                # Files whose ListenerSets were read already: the base is shared
                # by every environment and must be read once.
                read: set[Path] = set()
                for ed in envs:
                    erel = ed.relative_to(ROOT)
                    if not ENV.match(ed.name):
                        errors.append(f"{erel}: environment {ed.name!r}: lower-case letters and digits, at most 8, starting with a letter")
                        continue
                    ns = f"{ed.name}-{td.name}-{nd.name}"
                    if len(ns) > 63:
                        errors.append(f"{erel}: namespace {ns} is longer than 63 characters")
                        continue
                    # The environment's kustomization must be an overlay of ../../base
                    # (its first document, kind Kustomization or unset).
                    k = yaml_docs(ed / "kustomization.yaml") if (ed / "kustomization.yaml").is_file() else []
                    if not k or k[0].get("kind", "Kustomization") != "Kustomization" \
                            or "../../base" not in [str(r).rstrip("/") for r in k[0].get("resources") or []]:
                        errors.append(f"{erel}/kustomization.yaml: missing, or not an overlay of the base "
                                      "(kind: Kustomization, resources: [../../base, ...])")
                    team.namespaces.append(ns)
                    # Every ListenerSet host name in the environment and its base
                    # must start with "<team>-" (first DNS label) and be claimed
                    # only once across the tree.
                    for f in sorted(ed.rglob("*.y*ml")) + sorted(base.rglob("*.y*ml")):
                        if f in read:
                            continue
                        read.add(f)
                        for d in yaml_docs(f):
                            if d.get("kind") != "ListenerSet":
                                continue
                            for li in (d.get("spec") or {}).get("listeners") or []:
                                h = str(li.get("hostname", ""))
                                frel = f.relative_to(ROOT)
                                if not h.split(".")[0].startswith(f"{td.name}-"):
                                    errors.append(f"{frel}: host name {h!r} must start with '{td.name}-'")
                                elif h in hosts:
                                    errors.append(f"{frel}: host name {h} is already claimed by {hosts[h]}")
                                else:
                                    hosts[h] = str(frel)
    return teams, errors


def cluster() -> str:
    """Return the one cluster with an addons/teams.yaml; exit if there are none or several."""
    cs = sorted(c.name for c in (ROOT / "clusters").iterdir() if (c / "addons" / "teams.yaml").is_file())
    if len(cs) != 1:
        raise SystemExit(f"teams on {len(cs)} clusters ({cs}): applications/ is encrypted for one cluster")
    return cs[0]


def creds_prefix(t: Team) -> str:
    """Return the URL prefix of t's repositories, that of its Argo CD credential template."""
    return f"{FORGEJO_SSH}/{t.org}/{t.name}-"


def static_files(t: Team, c: str, pub: str) -> dict[str, str]:
    """Return the plain generated files of t's argocd/ folder, by name, for cluster c.

    pub is the public half of the team's deploy key, put on each repository.
    """
    keys = "".join(f"""---
apiVersion: repository.forgejo.m.crossplane.brobald.be/v1alpha1
kind: DeployKey
metadata:
  name: {r}-argocd
  namespace: team-{t.name}
spec:
  providerConfigRef: {{kind: ClusterProviderConfig, name: default}}
  forProvider:
    repositoryIdRef: {{name: {r}}}
    title: argocd-{c}
    readOnly: true
    key: {pub}
""" for r in t.repos)
    values = {"configs": {
        "cm": {"cluster.inClusterEnabled": "true"},
        "clusterCredentials": {"in-cluster": {
            "server": "https://kubernetes.default.svc",
            "namespaces": ",".join([f"team-{t.name}"] + t.namespaces),
            "config": {"tlsClientConfig": {"insecure": False}},
        }},
    }}
    return {
        "kustomization.yaml": HEADER + f"""# How the Argo CD of team {t.name} reads the team's repositories on cluster
# {c}: one read-only deploy key on each, whose private half is the Argo CD
# credential template repo-credentials.enc.yaml (SOPS) for
# {creds_prefix(t)}*. Synced with the team's platform part
# (Application team-{t.name}, second source). argocd-namespaces.yaml is a values
# file of the team's Argo CD (Application team-{t.name}-argocd), not part of this.
# The CI's Secrets (ci-*.enc.yaml): the password of the team's Forgejo user
# ci-{t.name} and its webhooks' secret (base/team, ci.yaml). Each object names
# its namespace (team-{t.name}, ci-{t.name}).
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deploy-keys.yaml
generators:
  - secret-generator.yaml
# When the team is removed, Crossplane still signs in as ci-{t.name} with this
# password to delete the user's token: Argo CD keeps the Secret, and the
# namespace cleanup deletes it with team-{t.name}.
patches:
  - patch: |
      apiVersion: v1
      kind: Secret
      metadata:
        name: forgejo-bot
        namespace: team-{t.name}
        annotations:
          argocd.argoproj.io/sync-options: Delete=false
""",
        "secret-generator.yaml": HEADER + f"""apiVersion: viaduct.ai/v1
kind: ksops
metadata:
  name: team-{t.name}-secrets
  annotations:
    config.kubernetes.io/function: |
      exec:
        path: ksops
files:
  - repo-credentials.enc.yaml   # Argo CD credential template: {creds_prefix(t)}*
  - ci-bot.enc.yaml             # team-{t.name}/forgejo-bot: the CI user's password
  - ci-webhook.enc.yaml         # team-{t.name}/forgejo-webhook: the webhooks' config
  - ci-webhook-pac.enc.yaml     # ci-{t.name}/pac-webhook: the same secret, for Pipelines-as-Code
  - tekton-dashboard.enc.yaml   # team-{t.name}/tekton-dashboard-oauth2-proxy: its cookie secret
""",
        "deploy-keys.yaml": HEADER + f"# Read-only, on each of the team's repositories (Repository objects of\n"
                            f"# base/team in this namespace). Removed from Forgejo when this goes.\n" + keys,
        "argocd-namespaces.yaml": HEADER + "# The namespaces the team's Argo CD may deploy to: its own (its\n"
                                  "# Applications), then its environment namespaces.\n"
                                  + yaml.safe_dump(values, sort_keys=False),
    }


def deploy_key_pub(path: Path) -> str | None:
    """Return the public key in deploy-keys.yaml (the first "key: " line), or None if there is none."""
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        if line.strip().startswith("key: "):
            return line.split("key: ", 1)[1].strip()
    return None


def encrypt(target: Path, secret: dict) -> None:
    """Write secret to target SOPS-encrypted, creating its folder; exit if sops fails.

    sops (SOPS, default "sops" on PATH) runs in applications/ to use its
    .sops.yaml, with target's path for the creation rules' path_regex.
    """
    out = subprocess.run([os.environ.get("SOPS", "sops"), "encrypt", "--input-type", "yaml", "--output-type", "yaml",
                          "--filename-override", str(target.relative_to(APPS)), "/dev/stdin"],
                         input=yaml.safe_dump(secret, sort_keys=False), capture_output=True, text=True, cwd=APPS)
    if out.returncode != 0:
        raise SystemExit(f"sops failed for {target.relative_to(ROOT)}: {out.stderr.strip()}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(out.stdout)


def credential(t: Team, private_key: str) -> dict:
    """Return the Argo CD credential template Secret of t: private_key for every repository under creds_prefix(t)."""
    return {"apiVersion": "v1", "kind": "Secret",
            "metadata": {"name": f"repo-creds-{t.name}", "namespace": f"team-{t.name}",
                         "labels": {"argocd.argoproj.io/secret-type": "repo-creds"}},
            "stringData": {"type": "git", "url": creds_prefix(t), "sshPrivateKey": private_key}}


def new_credentials(t: Team, c: str) -> str:
    """Make a new ed25519 key pair, write its private half as t's repo-credentials.enc.yaml
    and return its public half. The plaintext key lives only in a temporary folder."""
    with tempfile.TemporaryDirectory() as tmp:
        key = Path(tmp) / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"argocd-{c}-team-{t.name}",
                        "-f", str(key)], check=True)
        encrypt(t.dir / "argocd" / "repo-credentials.enc.yaml", credential(t, key.read_text()))
        return key.with_suffix(".pub").read_text().strip()


def ci_secrets(t: Team, c: str) -> dict[str, dict]:
    """Return t's three CI Secrets by file name, with a new random password and webhook secret.

    The webhook secret is the same in ci-webhook (Forgejo's side) and
    ci-webhook-pac (Pipelines-as-Code's side) on cluster c.
    """
    password, hook = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    def secret(name: str, ns: str, data: dict) -> dict:
        """Return a Secret manifest named name in namespace ns holding data as stringData."""
        return {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": name, "namespace": ns},
                "stringData": data}
    return {
        "ci-bot.enc.yaml": secret("forgejo-bot", f"team-{t.name}",
                                  {"host": FORGEJO_URL, "username": f"ci-{t.name}", "password": password}),
        "ci-webhook.enc.yaml": secret("forgejo-webhook", f"team-{t.name}",
                                      {"url": f"https://pac.apps.{c}.example.org", "content_type": "json",
                                       "secret": hook}),
        "ci-webhook-pac.enc.yaml": secret("pac-webhook", f"ci-{t.name}", {"webhook.secret": hook}),
    }


def sync_ci(t: Team, c: str, write: bool, errors: list[str]) -> None:
    """Make t's CI Secret files when all are missing and write is set; report otherwise.

    The three share a secret, so having only some of them is an error even
    with write: they are never completed one by one.
    """
    d = t.dir / "argocd"
    have = [n for n in CI_FILES if (d / n).is_file()]
    if len(have) == len(CI_FILES):
        return
    if have:
        errors.append(f"{d.relative_to(ROOT)}: {', '.join(CI_FILES)} go together: delete them and run "
                      "'python3 tools/teams.py generate' (new secrets)")
    elif not write:
        errors.append(f"{d.relative_to(ROOT)}: CI secrets missing: run 'python3 tools/teams.py generate' and commit")
    else:
        for name, secret in ci_secrets(t, c).items():
            encrypt(d / name, secret)
            print(f"wrote {(d / name).relative_to(ROOT)} (new secret)")


def sync_dashboard(t: Team, write: bool, errors: list[str]) -> None:
    """Make t's Tekton Dashboard cookie secret file if missing and write is set; report it missing otherwise."""
    f = t.dir / "argocd" / DASHBOARD_FILE
    if f.is_file():
        return
    if not write:
        errors.append(f"{f.relative_to(ROOT)}: missing: run 'python3 tools/teams.py generate' and commit")
        return
    # oauth2-proxy takes a cookie secret of 16, 24 or 32 bytes: 32 characters.
    encrypt(f, {"apiVersion": "v1", "kind": "Secret",
                "metadata": {"name": "tekton-dashboard-oauth2-proxy", "namespace": f"team-{t.name}"},
                "stringData": {"cookie-secret": secrets.token_hex(16)}})
    print(f"wrote {f.relative_to(ROOT)} (new secret)")


def sync(teams: list[Team], write: bool, errors: list[str]) -> None:
    """Bring each team's argocd/ folder up to date (write) or report what isn't (check).

    A removed team's folder is deleted. Otherwise the deploy key pair is made
    when both its files are missing, then the CI and dashboard Secrets and the
    plain generated files; files in argocd/ that aren't generated are errors.
    Existing Secrets are never replaced.
    """
    c = cluster()
    for t in teams:
        d = t.dir / "argocd"
        if t.removed:
            if d.is_dir():
                if write:
                    shutil.rmtree(d)
                    print(f"removed {d.relative_to(ROOT)} (team marked removed)")
                else:
                    errors.append(f"{d.relative_to(ROOT)}: the team is marked removed: run "
                                  "'python3 tools/teams.py generate' (it deletes argocd/) and commit")
            continue
        # The deploy key's halves live in two files that must exist together.
        enc, dk = d / "repo-credentials.enc.yaml", d / "deploy-keys.yaml"
        pub = deploy_key_pub(dk)
        if enc.is_file() != (pub is not None):
            errors.append(f"{d.relative_to(ROOT)}: repo-credentials.enc.yaml and deploy-keys.yaml go together: "
                          "delete both and run 'python3 tools/teams.py generate' (a new key)")
            continue
        if pub is None:
            if not write:
                errors.append(f"{d.relative_to(ROOT)}: missing: run 'python3 tools/teams.py generate' and commit")
                continue
            pub = new_credentials(t, c)
            print(f"wrote {enc.relative_to(ROOT)} (new key)")
        sync_ci(t, c, write, errors)
        sync_dashboard(t, write, errors)
        want = static_files(t, c, pub)
        for name, content in want.items():
            f = d / name
            if f.is_file() and f.read_text() == content:
                continue
            if write:
                f.write_text(content)
                print(f"wrote {f.relative_to(ROOT)}")
            else:
                errors.append(f"{f.relative_to(ROOT)} is not current: run 'python3 tools/teams.py generate' and commit")
        for f in sorted(d.iterdir()) if d.is_dir() else []:
            if f.name not in want and f.name != "repo-credentials.enc.yaml" and f.name not in CI_FILES \
                    and f.name != DASHBOARD_FILE:
                errors.append(f"{f.relative_to(ROOT)}: not a generated file (argocd/ is generated)")


def tenants_project(teams: list[Team]) -> str:
    """Return the AppProject tenants: the namespaces of every organization (org-<org>),
    team (team-, ci-) and environment, sorted, and the TENANT_*KINDS. Removed teams
    are still included, so that their Applications can be deleted."""
    orgs = {f"org-{o.name}" for o in APPS.iterdir() if (o / "organization.yaml").is_file()} if APPS.is_dir() else set()
    nss = sorted(orgs | {f"team-{t.name}" for t in teams}
                 | {f"ci-{t.name}" for t in teams} | {n for t in teams for n in t.namespaces})
    kinds = lambda ks: "".join(f"    - group: '{g}'\n      kind: {k}\n" for g, k in ks)
    return HEADER + f"""# The organizations, teams and environments of applications/ (the
# ApplicationSets of addons/teams.yaml): their namespaces only, and the kinds
# the team chart and base/team-namespace use (docs/reference/projects.md).
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: tenants
  namespace: argocd
spec:
  description: The teams' namespaces, Argo CDs, CI and external objects (applications/)
  sourceRepos:
    - {GITOPS}
    - https://argoproj.github.io/argo-helm
  destinations:
""" + "".join(f"    - server: https://kubernetes.default.svc\n      namespace: {n}\n" for n in nss) + \
        "  clusterResourceWhitelist:\n" + kinds(TENANT_CLUSTER_KINDS) + \
        "  namespaceResourceWhitelist:\n" + kinds(TENANT_KINDS)


def sync_project(teams: list[Team], c: str, write: bool, errors: list[str]) -> None:
    """Write cluster c's addons/projects/tenants.yaml if stale (write), or report it stale (check)."""
    f = ROOT / "clusters" / c / "addons" / "projects" / "tenants.yaml"
    content = tenants_project(teams)
    if f.is_file() and f.read_text() == content:
        return
    if write:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
        print(f"wrote {f.relative_to(ROOT)}")
    else:
        errors.append(f"{f.relative_to(ROOT)} is not current: run 'python3 tools/teams.py generate' and commit")


def check_host_key(c: str, errors: list[str]) -> None:
    """Report an error unless the Forgejo SSH host keys in base/team/argocd-values.yaml
    are among those of cluster c's platform Argo CD (addons/generated/argocd.yaml)."""
    def hosts(p: Path) -> set[str]:
        """Return the indented known_hosts lines "[host]:port ssh-<type> <key>" of file p; empty if p is missing."""
        lines = re.findall(r"^\s+(\[[^\]]+\]:\d+ ssh-\S+ \S+)", p.read_text(), re.M) if p.is_file() else []
        return set(lines)
    app = f"clusters/{c}/addons/generated/argocd.yaml"
    team, platform = hosts(ROOT / "base/team/argocd-values.yaml"), hosts(ROOT / app)
    if not (ROOT / app).is_file():
        errors.append(f"{app} is missing: deploy-talos.py push writes it (a new cluster's first step)")
    elif not platform:
        errors.append(f"{app}: no SSH host keys found (moved? update check_host_key)")
    elif not team <= platform:
        errors.append(f"base/team/argocd-values.yaml: the SSH host key differs from the platform Argo CD's "
                      f"({app}): copy it from there")


def check_removals(teams: list[Team], errors: list[str]) -> None:
    """Report each team folder deleted although its team.yaml on the target branch
    (GITOPS_BASE, default origin/main) isn't marked removed: true.

    Without that branch, only a warning is printed.
    """
    base = os.environ.get("GITOPS_BASE", "origin/main")
    def git(*args: str) -> subprocess.CompletedProcess:
        """Run git in ROOT and return the result (output captured, never raises on failure)."""
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    listed = git("ls-tree", "-r", "--name-only", base, "--", "applications")
    if listed.returncode != 0:
        print(f"WARNING: {base} not found: the removal of teams is not checked", file=sys.stderr)
        return
    present = {(t.org, t.name) for t in teams}
    # Only applications/<org>/<team>/team.yaml paths matter: a team present on
    # the target branch but no longer in the tree was deleted.
    for path in listed.stdout.split():
        parts = path.split("/")
        if len(parts) != 4 or parts[3] != "team.yaml" or (parts[1], parts[2]) in present:
            continue
        old = yaml.safe_load(git("show", f"{base}:{path}").stdout or "{}") or {}
        if old.get("removed") is not True:
            errors.append(f"applications/{parts[1]}/{parts[2]}: deleted while {base} doesn't have removed: true "
                          "in its team.yaml: set that first, merge, wait for its namespaces to go, then delete "
                          "the folder (docs/how-to/remove-a-team-or-environment.md)")


def main(argv: list[str]) -> int:
    """Run `generate` or `check`; return 2 (usage on stderr) for other arguments, 1 on errors, else 0.

    Nothing is generated or compared while the layout has errors.
    """
    if argv not in (["generate"], ["check"]):
        print(__doc__, file=sys.stderr)
        return 2
    teams, errors = scan()
    if not errors:
        sync(teams, argv == ["generate"], errors)
        sync_project(teams, cluster(), argv == ["generate"], errors)
        check_host_key(cluster(), errors)
        check_removals(teams, errors)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if not errors and argv == ["check"]:
        print(f"teams: {len(teams)}, environment namespaces: {sum(len(t.namespaces) for t in teams)}, all current")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

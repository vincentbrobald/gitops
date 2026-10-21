#!/usr/bin/env python3
"""The Secrets of a cluster that no other tool makes (docs/reference/encrypted-secrets.md):
written SOPS-encrypted from credentials that exist already, or random.

    python3 tools/bootstrap.py write --cluster lab --secrets-dir DIR --domain DOMAIN [options]
    python3 tools/bootstrap.py check --cluster lab --secrets-dir DIR --domain DOMAIN [options]

`write` makes the Secrets that are missing and never replaces one (a Secret
in the repository wins: the infra playbooks read it back). `check` compares
each existing Secret with what `write` would make, prints "same" or
"differs" (never a value), and exits 1 if one differs.

| Secret (clusters/<cluster>/...) | From |
|---|---|
| crossplane/...-keycloak-credentials | <secrets-dir>/oauth/crossplane-lab-client-secret (Keycloak's client for Crossplane, infra) |
| crossplane/...-forgejo-credentials | <secrets-dir>/forgejo/crossplane-lab-token (the token of Forgejo's user crossplane-lab, infra) |
| crossplane/...-harbor-credentials | <secrets-dir>/registry/harbor-admin-password (Harbor's admin, infra) |
| crossplane/...-artifact-keeper-credentials | <secrets-dir>/artifacts/crossplane-lab-token (Artifact Keeper's API token, infra) |
| argocd-preview/...-creds-forgejo | --gitops-ssh-key: the repository's read-only deploy key (the cluster file's argocd.repository.auth.sshKeyFile) |
| tekton/dashboard/...-oauth2-proxy | random (the Dashboard's cookie secret) |

It also gives applications/.sops.yaml the cluster's recipients when it still
holds the published placeholder. Each folder's secret-generator.yaml lists
these files already.

Host names: oauth., forgejo. and artifacts. under --domain unless given.
sops encrypts for the public keys of the cluster's .sops.yaml; set SOPS to
the binary if it isn't on PATH, and SOPS_AGE_KEY_FILE for `check` (it
decrypts). GITOPS_ROOT: the checkout to work on.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

import yaml

# The gitops checkout: GITOPS_ROOT, or the repository this script is in.
ROOT = Path(os.environ.get("GITOPS_ROOT") or Path(__file__).resolve().parent.parent).resolve()
# The recipient a published applications/.sops.yaml holds until a cluster's
# recipients replace it.
PLACEHOLDER = "age1-replace-with-your-age-public-key"


def read(path: Path) -> str:
    """Return the content of the credential file path, stripped; exit with a message if it is missing."""
    if not path.is_file():
        raise SystemExit(f"missing: {path} (made by the infra playbooks, or by hand: see the module's docstring)")
    return path.read_text().strip()


def secret(namespace: str, name: str, data: dict[str, str], labels: dict[str, str] | None = None) -> dict:
    """Return an Opaque Secret manifest holding data as stringData, with labels if given."""
    meta = {"name": name, "namespace": namespace} | ({"labels": labels} if labels else {})
    return {"apiVersion": "v1", "kind": "Secret", "metadata": meta, "type": "Opaque", "stringData": data}


def wanted(a: argparse.Namespace) -> dict[str, dict | None]:
    """Return the Secret manifest to write for each file, by path relative to the cluster folder.

    Reads the credentials from --secrets-dir (exits if one is missing). The
    argocd-preview repository credentials are None without --gitops-ssh-key.
    The oauth2-proxy cookie secret is new random on every call, so `check`
    compares only its shape (see same()).
    """
    s = a.secrets_dir
    keycloak = a.keycloak_url or f"https://oauth.{a.domain}"
    forgejo = a.forgejo_url or f"https://forgejo.{a.domain}"
    artifacts = a.artifacts_url or f"https://artifacts.{a.domain}"
    harbor_password = read(s / "registry/harbor-admin-password")
    out: dict[str, dict | None] = {
        "crossplane/secret-crossplane-system-keycloak-credentials.enc.yaml": secret(
            "crossplane-system", "keycloak-credentials",
            {"client_id": "crossplane-lab", "client_secret": read(s / "oauth/crossplane-lab-client-secret"),
             "keycloak_version": a.keycloak_version, "realm": "master", "url": keycloak}),
        "crossplane/secret-crossplane-system-forgejo-credentials.enc.yaml": secret(
            "crossplane-system", "forgejo-credentials",
            {"api_token": read(s / "forgejo/crossplane-lab-token"), "host": forgejo}),
        "crossplane/secret-crossplane-system-harbor-credentials.enc.yaml": secret(
            "crossplane-system", "harbor-credentials",
            {"credentials": json.dumps({"username": "admin", "password": harbor_password}),
             "username": "admin", "password": harbor_password}),
        "crossplane/secret-crossplane-system-artifact-keeper-credentials.enc.yaml": secret(
            "crossplane-system", "artifact-keeper-credentials",
            {"url": artifacts, "token": read(s / "artifacts/crossplane-lab-token")}),
        "argocd-preview/secret-argocd-preview-creds-forgejo.enc.yaml": None,
        "tekton/dashboard/secret-tekton-dashboard-oauth2-proxy.enc.yaml": secret(
            "tekton-dashboard", "oauth2-proxy", {"cookie-secret": secrets.token_hex(16)}),
    }
    if a.gitops_ssh_key:
        ssh = a.forgejo_ssh or f"ssh://git@forgejo.{a.domain}:2222/"
        out["argocd-preview/secret-argocd-preview-creds-forgejo.enc.yaml"] = secret(
            "argocd-preview", "creds-forgejo",
            {"type": "git", "url": ssh, "sshPrivateKey": read(a.gitops_ssh_key) + "\n"},
            {"argocd.argoproj.io/secret-type": "repo-creds"})
    return out


def sops(*args: str, cwd: Path, stdin: str | None = None) -> str:
    """Run sops (SOPS, default "sops" on PATH) with args in cwd and return its stdout.

    Running in the cluster folder makes sops pick up that folder's .sops.yaml.
    Exits with sops's error output if it fails.
    """
    p = subprocess.run([os.environ.get("SOPS", "sops"), *args], input=stdin, capture_output=True, text=True, cwd=cwd)
    if p.returncode != 0:
        raise SystemExit(f"sops {args[0]} failed: {p.stderr.strip()}")
    return p.stdout


def data_of(doc: dict) -> dict[str, str]:
    """Return a Secret's values as strings: stringData if it has any, else data base64-decoded."""
    if doc.get("stringData"):
        return {k: str(v) for k, v in doc["stringData"].items()}
    return {k: base64.b64decode(v).decode() for k, v in (doc.get("data") or {}).items()}


def same(rel: str, have: dict[str, str], want: dict[str, str]) -> bool:
    """Tell whether the existing values have match the wanted values want for file rel.

    The random cookie secret only needs the same keys and a length of 16, 24
    or 32; the SSH key is compared without surrounding whitespace, and Harbor's
    credentials JSON by value rather than by text.
    """
    if rel.endswith("oauth2-proxy.enc.yaml"):
        return set(have) == set(want) and len(have["cookie-secret"]) in (16, 24, 32)
    if rel.endswith("creds-forgejo.enc.yaml"):
        have, want = dict(have), dict(want)
        have["sshPrivateKey"], want["sshPrivateKey"] = have["sshPrivateKey"].strip(), want["sshPrivateKey"].strip()
    if rel.endswith("harbor-credentials.enc.yaml"):
        have, want = dict(have), dict(want)
        have["credentials"], want["credentials"] = json.loads(have["credentials"]), json.loads(want["credentials"])
    return have == want


def recipients(cluster: Path) -> str:
    """Return the age recipients (comma-separated) of the first creation rule of the cluster's .sops.yaml."""
    rules = yaml.safe_load((cluster / ".sops.yaml").read_text())["creation_rules"]
    return rules[0]["age"]


def main(argv: list[str]) -> int:
    """Run `write` or `check` (see the module docstring); return 1 if `check` found a difference, else 0."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["write", "check"])
    ap.add_argument("--cluster", required=True, help="the folder clusters/<cluster>")
    ap.add_argument("--secrets-dir", type=Path, required=True, help="the infra playbooks' secrets tree")
    ap.add_argument("--domain", required=True, help="the site's domain (host names below it)")
    ap.add_argument("--keycloak-version", default="26.8.1", help="the Keycloak version infra installs (provider-keycloak needs it)")
    ap.add_argument("--gitops-ssh-key", type=Path, help="private key of this repository's read-only deploy key")
    ap.add_argument("--keycloak-url"), ap.add_argument("--forgejo-url"), ap.add_argument("--artifacts-url")
    ap.add_argument("--forgejo-ssh", help="Forgejo's SSH URL prefix (default ssh://git@forgejo.<domain>:2222/)")
    a = ap.parse_args(argv)
    cluster = ROOT / "clusters" / a.cluster
    if not (cluster / ".sops.yaml").is_file():
        raise SystemExit(f"{cluster}/.sops.yaml is missing: deploy-talos.py push writes it (the cluster's first step)")
    differs = 0
    for rel, want in wanted(a).items():
        path = cluster / rel
        if want is None:
            print(f"{rel}: skipped (no --gitops-ssh-key)")
            continue
        if a.command == "check":
            if not path.is_file():
                print(f"{rel}: missing"); differs += 1
                continue
            have = data_of(yaml.safe_load(sops("decrypt", str(path.relative_to(cluster)), cwd=cluster)))
            ok = same(rel, have, want["stringData"])
            print(f"{rel}: {'same' if ok else 'differs'}")
            differs += not ok
        elif path.is_file():
            print(f"{rel}: kept (exists)")
        else:
            out = sops("encrypt", "--input-type", "yaml", "--output-type", "yaml", "--filename-override",
                       str(path.relative_to(cluster)), "/dev/stdin", cwd=cluster,
                       stdin=yaml.safe_dump(want, sort_keys=False))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(out)
            print(f"{rel}: written")
    apps = ROOT / "applications" / ".sops.yaml"
    if apps.is_file() and PLACEHOLDER in apps.read_text():
        if a.command == "check":
            print("applications/.sops.yaml: still the placeholder"); differs += 1
        else:
            # Replace the placeholder, or a comma-separated run of them, with the
            # cluster's recipients.
            apps.write_text(re.sub(rf"{re.escape(PLACEHOLDER)}(,{re.escape(PLACEHOLDER)})*", recipients(cluster),
                                   apps.read_text()))
            print("applications/.sops.yaml: the cluster's recipients")
    return 1 if differs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

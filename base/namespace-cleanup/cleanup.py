#!/usr/bin/env python3
"""Delete namespaces whose owners are gone and that hold nothing Crossplane
still manages.

A namespace opts in with the label cleanup.example.org/when-orphaned=true and
names its owners with the annotation cleanup.example.org/applications: a
label selector over Argo CD Applications (namespace ARGOCD_NAMESPACE). It is
deleted when, in this order:

1. no Application matches the selector: the namespace is then marked
   orphaned (annotation cleanup.example.org/orphaned-since);
2. it has stayed orphaned for GRACE_SECONDS (an Application recreated
   meanwhile clears the mark);
3. no Crossplane managed resource (CRDs of category "managed") is left in it:
   Crossplane deletes their external objects first, which needs the
   namespace to exist.

Owners mark their namespaces argocd.argoproj.io/sync-options: Delete=false,
so that Argo CD deletes everything in them but not the namespaces.

Environment: ARGOCD_NAMESPACE (argocd), GRACE_SECONDS (600), DRY_RUN (false).
A busy or restarting API server (429, 5xx, no connection) is retried a few
times, honouring Retry-After; then the run fails and the next one starts over.
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SA = "/var/run/secrets/kubernetes.io/serviceaccount"
API = "https://kubernetes.default.svc"
LABEL = "cleanup.example.org/when-orphaned"
OWNERS = "cleanup.example.org/applications"
SINCE = "cleanup.example.org/orphaned-since"
ARGOCD_NAMESPACE = os.environ.get("ARGOCD_NAMESPACE", "argocd")
GRACE = int(os.environ.get("GRACE_SECONDS", "600"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

CTX = ssl.create_default_context(cafile=f"{SA}/ca.crt")
TOKEN = open(f"{SA}/token").read().strip()


RETRY_CODES = {429, 500, 502, 503, 504}
ATTEMPTS = 5


def call(method: str, path: str, body: dict | None = None, ctype: str = "application/json") -> dict:
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(ATTEMPTS):
        req = urllib.request.Request(API + path, method=method, data=data,
                                     headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_CODES or attempt == ATTEMPTS - 1:
                raise
            after = e.headers.get("Retry-After", "")
            wait = min(int(after), 30) if after.isdigit() else 2 ** attempt
            print(f"{method} {path}: HTTP {e.code}, retrying in {wait}s", flush=True)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == ATTEMPTS - 1:
                raise
            wait = 2 ** attempt
            print(f"{method} {path}: {e}, retrying in {wait}s", flush=True)
        time.sleep(wait)
    raise AssertionError("unreachable")


def log(ns: str, msg: str) -> None:
    print(f"{ns}: {msg}", flush=True)


def managed_kinds() -> list[tuple[str, str, str]]:
    kinds = []
    for crd in call("GET", "/apis/apiextensions.k8s.io/v1/customresourcedefinitions")["items"]:
        spec = crd["spec"]
        if spec["scope"] == "Namespaced" and "managed" in spec["names"].get("categories", []):
            version = next(v["name"] for v in spec["versions"] if v.get("storage"))
            kinds.append((spec["group"], version, spec["names"]["plural"]))
    return kinds


def remaining(ns: str, kinds: list[tuple[str, str, str]]) -> list[str]:
    left = []
    for group, version, plural in kinds:
        try:
            items = call("GET", f"/apis/{group}/{version}/namespaces/{ns}/{plural}?limit=50")["items"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        left += [f"{plural}.{group}/{i['metadata']['name']}" for i in items]
    return left


def annotate(ns: str, value: str | None) -> None:
    call("PATCH", f"/api/v1/namespaces/{ns}", {"metadata": {"annotations": {SINCE: value}}},
         ctype="application/merge-patch+json")


def main() -> int:
    sel = urllib.parse.quote(f"{LABEL}=true")
    namespaces = call("GET", f"/api/v1/namespaces?labelSelector={sel}")["items"]
    kinds = None
    for n in namespaces:
        meta = n["metadata"]
        ns, notes = meta["name"], meta.get("annotations") or {}
        if meta.get("deletionTimestamp"):
            log(ns, "already being deleted")
            continue
        owners = notes.get(OWNERS)
        if not owners:
            log(ns, f"no {OWNERS} annotation: skipped")
            continue
        apps = call("GET", f"/apis/argoproj.io/v1alpha1/namespaces/{ARGOCD_NAMESPACE}/applications"
                           f"?labelSelector={urllib.parse.quote(owners)}")["items"]
        if apps:
            if SINCE in notes:
                log(ns, f"owners back ({len(apps)} Application(s)): no longer orphaned")
                if not DRY_RUN:
                    annotate(ns, None)
            continue
        if SINCE not in notes:
            log(ns, f"no Application matches {owners!r}: orphaned, deleted after {GRACE}s")
            if not DRY_RUN:
                annotate(ns, str(int(time.time())))
            continue
        waited = int(time.time()) - int(notes[SINCE])
        if waited < GRACE:
            log(ns, f"orphaned for {waited}s of {GRACE}s")
            continue
        if kinds is None:
            kinds = managed_kinds()
        left = remaining(ns, kinds)
        if left:
            log(ns, f"waiting for Crossplane: {len(left)} managed resource(s) left, e.g. {', '.join(left[:3])}")
            continue
        log(ns, "orphaned, no managed resource left: deleting" + (" (dry run)" if DRY_RUN else ""))
        if not DRY_RUN:
            call("DELETE", f"/api/v1/namespaces/{ns}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

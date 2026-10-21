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

Environment: ARGOCD_NAMESPACE (argocd), GRACE_SECONDS (600), DRY_RUN (false),
RUN_SECONDS (200). A busy or restarting API server (429, 5xx, no connection)
is retried a few times, honouring Retry-After, within RUN_SECONDS for the
whole run; then the run fails and the next one starts over. RUN_SECONDS stays
below the Job's activeDeadlineSeconds, so that a run ends with its own error
rather than being killed.
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# In-cluster service account files (CA, token) and the API server address.
SA = "/var/run/secrets/kubernetes.io/serviceaccount"
API = "https://kubernetes.default.svc"
LABEL = "cleanup.example.org/when-orphaned"
OWNERS = "cleanup.example.org/applications"
SINCE = "cleanup.example.org/orphaned-since"
ARGOCD_NAMESPACE = os.environ.get("ARGOCD_NAMESPACE", "argocd")
GRACE = int(os.environ.get("GRACE_SECONDS", "600"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
# Monotonic time by which the whole run must be done; retries never wait past it.
DEADLINE = time.monotonic() + int(os.environ.get("RUN_SECONDS", "200"))

CTX = ssl.create_default_context(cafile=f"{SA}/ca.crt")
TOKEN = open(f"{SA}/token").read().strip()


# HTTP statuses retried as a busy or restarting API server, and the number of
# tries per request (first attempt included).
RETRY_CODES = {429, 500, 502, 503, 504}
ATTEMPTS = 5


def call(method: str, path: str, body: dict | None = None, ctype: str = "application/json") -> dict:
    """Send a request to the API server and return the decoded JSON response.

    body is sent as JSON with Content-Type ctype; an empty response body
    returns {}. A retryable status (RETRY_CODES), a connection error or a
    timeout is retried up to ATTEMPTS times; any other HTTP error, or running
    out of attempts or of time before DEADLINE, raises the last
    urllib.error.HTTPError / URLError / TimeoutError.
    """
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(ATTEMPTS):
        req = urllib.request.Request(API + path, method=method, data=data,
                                     headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": ctype})
        # The timeout is at most 30s and never runs past DEADLINE (but at least 1s).
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=max(1, min(30, DEADLINE - time.monotonic()))) as r:
                return json.loads(r.read() or b"{}")
        # HTTPError is a URLError, so it must be caught first. Wait for
        # Retry-After (capped at 30s) when the server sends whole seconds,
        # otherwise back off exponentially (1, 2, 4, 8s); give up rather than
        # sleep past DEADLINE.
        except urllib.error.HTTPError as e:
            after = e.headers.get("Retry-After", "")
            wait = min(int(after), 30) if after.isdigit() else 2 ** attempt
            if e.code not in RETRY_CODES or attempt == ATTEMPTS - 1 or time.monotonic() + wait >= DEADLINE:
                raise
            print(f"{method} {path}: HTTP {e.code}, retrying in {wait}s", flush=True)
        except (urllib.error.URLError, TimeoutError) as e:
            wait = 2 ** attempt
            if attempt == ATTEMPTS - 1 or time.monotonic() + wait >= DEADLINE:
                raise
            print(f"{method} {path}: {e}, retrying in {wait}s", flush=True)
        time.sleep(wait)
    raise AssertionError("unreachable")


def log(ns: str, msg: str) -> None:
    """Print msg prefixed with the namespace name, flushed at once for the Job's log."""
    print(f"{ns}: {msg}", flush=True)


def managed_kinds() -> list[tuple[str, str, str]]:
    """Return (group, storage version, plural) of every namespaced CRD in category "managed"."""
    kinds = []
    for crd in call("GET", "/apis/apiextensions.k8s.io/v1/customresourcedefinitions")["items"]:
        spec = crd["spec"]
        if spec["scope"] == "Namespaced" and "managed" in spec["names"].get("categories", []):
            version = next(v["name"] for v in spec["versions"] if v.get("storage"))
            kinds.append((spec["group"], version, spec["names"]["plural"]))
    return kinds


def remaining(ns: str, kinds: list[tuple[str, str, str]]) -> list[str]:
    """Return "plural.group/name" of the managed resources of kinds left in namespace ns.

    Only the first page (50) of each kind is listed: enough to tell whether
    any is left and to name a few. A kind whose API returns 404 (CRD removed
    since it was listed) is skipped.
    """
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
    """Set the orphaned-since annotation of namespace ns to value; None removes it (merge patch)."""
    call("PATCH", f"/api/v1/namespaces/{ns}", {"metadata": {"annotations": {SINCE: value}}},
         ctype="application/merge-patch+json")


def main() -> int:
    """Run one pass over the opted-in namespaces (see the module docstring) and return 0.

    Each namespace advances at most one step per run: mark orphaned, wait for
    the grace period, wait for Crossplane, delete. With DRY_RUN only the log
    is written. API errors propagate and fail the run.
    """
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
        # The managed kinds are listed once per run, and only if a namespace gets this far.
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

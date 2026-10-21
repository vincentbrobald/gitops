#!/usr/bin/env python3
"""Refuse edits by hand of what deploy-talos.py generates.

    python3 tools/generated.py check   # what the merge check runs

deploy-talos.py (talos-install) owns, under each cluster folder,
addons/generated/ (its Applications) and generated/ (its manifests and
Secrets by topic), and writes generated/CHECKSUMS: the sha256 of each of
those files. A file that differs from its checksum, or a file there that
CHECKSUMS doesn't list, was changed by hand: change the cluster file
(/root/lab/<cluster>.yaml) and run deploy-talos.py instead (it pushes its
files to main directly, as the only writer of these folders).
"""
import hashlib
import os
import sys
from pathlib import Path

# The gitops checkout: GITOPS_ROOT, or the repository this script is in.
ROOT = Path(os.environ.get("GITOPS_ROOT") or Path(__file__).resolve().parent.parent).resolve()
# The folders under each cluster folder that deploy-talos.py owns.
OWNED = ("addons/generated", "generated")


def check_cluster(c: Path, errors: list[str]) -> int:
    """Check cluster folder c's generated files against its CHECKSUMS; return how many it lists.

    Appends a message to errors for each file missing, changed or not listed,
    and for owned files without a CHECKSUMS (then returns 0).
    """
    sums = c / "generated" / "CHECKSUMS"
    owned = sorted(f for top in OWNED if (c / top).is_dir() for f in (c / top).rglob("*") if f.is_file())
    if not sums.is_file():
        if owned:
            errors.append(f"{c.relative_to(ROOT)}: generated files without generated/CHECKSUMS")
        return 0
    # CHECKSUMS lines are "<sha256> <path relative to the cluster folder>",
    # as sha256sum writes them; blank and # lines are skipped.
    listed = {}
    for line in sums.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        listed[rel.strip()] = digest
    for rel, digest in sorted(listed.items()):
        f = c / rel
        if not f.is_file():
            errors.append(f"{f.relative_to(ROOT)}: listed in CHECKSUMS but missing")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            errors.append(f"{f.relative_to(ROOT)}: changed by hand (deploy-talos.py generates it)")
    for f in owned:
        rel = str(f.relative_to(c))
        if rel != "generated/CHECKSUMS" and rel not in listed:
            errors.append(f"{f.relative_to(ROOT)}: added by hand in a folder deploy-talos.py owns")
    return len(listed)


def main(argv: list[str]) -> int:
    """Run `check` over every cluster folder; return 2 (usage on stderr) for other arguments, 1 on errors, else 0."""
    if argv != ["check"]:
        print(__doc__, file=sys.stderr)
        return 2
    errors: list[str] = []
    n = sum(check_cluster(c, errors) for c in sorted((ROOT / "clusters").iterdir()) if c.is_dir())
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if not errors:
        print(f"generated files: {n}, all as deploy-talos.py wrote them")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

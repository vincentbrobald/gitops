#!/usr/bin/env python3
"""Generate the diagrams of this repository's documentation (docs/*.svg).

Usage: docs/diagrams.py [docs directory]"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

# Palette: a fill colour per box kind, and its border colour under the same
# key with a "b" suffix (Svg.box and Svg.legend rely on that pairing).
C = {
    "bg": "#ffffff", "ink": "#1f2933", "muted": "#52606d", "line": "#7b8794",
    "host": "#f5f7fa", "hostb": "#9aa5b1",
    "net": "#e8f1fb", "netb": "#4a7fc1",
    "lan": "#fdf5e6", "lanb": "#c98a1c",
    "cp": "#fde8e1", "cpb": "#c4572e",
    "wk": "#e3f4e8", "wkb": "#2f8a4c",
    "vip": "#f1e8fb", "vipb": "#7a4fb5",
    "ext": "#eef0f2", "extb": "#7b8794",
    "tool": "#ffffff", "toolb": "#52606d",
}
# Font stack set once on the root <svg>, inherited by every <text>.
FONT = "font-family=\"-apple-system,'Segoe UI',Helvetica,Arial,sans-serif\""


class Svg:
    """An SVG document built as a list of element strings, written by save().

    Coordinates are in pixels from the top left; text is XML-escaped.
    """

    def __init__(self, w, h, title, desc):
        """Start a w x h drawing with an accessible title and description,
        the arrowhead marker "a" and a background rectangle."""
        self.w, self.h = w, h
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d" {FONT} font-size="13">',
            f"<title id=\"t\">{escape(title)}</title>",
            f"<desc id=\"d\">{escape(desc)}</desc>",
            "<defs><marker id=\"a\" viewBox=\"0 0 10 10\" refX=\"9\" refY=\"5\" markerWidth=\"7\" markerHeight=\"7\" "
            f"orient=\"auto-start-reverse\"><path d=\"M0,0 L10,5 L0,10 z\" fill=\"{C['line']}\"/></marker></defs>",
            f'<rect width="{w}" height="{h}" fill="{C["bg"]}"/>',
        ]

    def box(self, x, y, w, h, kind, lines=(), title=None, dashed=False, rx=8, align="middle", size=13):
        """Draw a rounded box in the colours of kind (a key of C).

        title, if given, goes bold in the top left corner in the border colour.
        lines are centred vertically as a block; the first is the heading (bold
        when there is no title, ink colour, full size), the others are smaller
        and muted. align is "middle" (centred) or "start" (12px from the left).
        """
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{C[kind]}" '
                          f'stroke="{C[kind + "b"]}" stroke-width="1.5"{dash}/>')
        if title:
            self.text(x + 12, y + 20, title, bold=True, anchor="start", color=C[kind + "b"])
        if lines:
            # Line height size + 4; the block's centre sits on the box's centre,
            # +0.35 em to move from the baseline to the visual middle of a line.
            n = len(lines)
            lh = size + 4
            top = y + h / 2 - (n - 1) * lh / 2 + size * 0.35
            tx = x + w / 2 if align == "middle" else x + 12
            for i, ln in enumerate(lines):
                bold = i == 0 and not title
                self.text(tx, top + i * lh, ln, bold=bold, anchor=align, size=size if i == 0 else size - 1,
                          color=C["ink"] if i == 0 else C["muted"])

    def text(self, x, y, s, bold=False, anchor="start", size=13, color=None, italic=False):
        """Add text s with its baseline at y; anchor is an SVG text-anchor (start, middle, end)."""
        self.parts.append(f'<text x="{x}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
                          f'fill="{color or C["ink"]}"{" font-weight=\"600\"" if bold else ""}'
                          f'{" font-style=\"italic\"" if italic else ""}>{escape(s)}</text>')

    def line(self, pts, arrow_end=True, arrow_start=False, dashed=False, color=None, label=None, lx=None, ly=None,
             anchor="middle"):
        """Draw a polyline through pts ((x, y) pairs), with arrowheads at either end.

        label, if given, is drawn at (lx, ly) with label().
        """
        d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
        attrs = ""
        if arrow_end:
            attrs += ' marker-end="url(#a)"'
        if arrow_start:
            attrs += ' marker-start="url(#a)"'
        if dashed:
            attrs += ' stroke-dasharray="5 4"'
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color or C["line"]}" stroke-width="1.6"{attrs}/>')
        if label:
            self.label(lx, ly, label, anchor)

    def label(self, x, y, s, anchor="middle", size=12):
        """Draw small muted text s at (x, y) on a nearly opaque background patch,
        so that it stays readable over the lines it crosses."""
        # The patch's width is estimated from the character count (about
        # 0.56 em per character) plus 5px padding on each side.
        w = len(s) * size * 0.56 + 10
        x0 = {"middle": x - w / 2, "start": x - 5, "end": x - w + 5}[anchor]
        self.parts.append(f'<rect x="{x0:.1f}" y="{y - size - 1}" width="{w:.1f}" height="{size + 7}" rx="3" '
                          f'fill="{C["bg"]}" fill-opacity="0.92"/>')
        self.text(x, y + 1, s, anchor=anchor, size=size, color=C["muted"])

    def legend(self, x, y, items):
        """Draw a row of legend entries from (x, y), 150px apart.

        items are (kind, text, dashed) triples: a small swatch in kind's colours,
        dashed or not, followed by the text.
        """
        for i, (kind, s, dashed) in enumerate(items):
            xx = x + i * 150
            dash = ' stroke-dasharray="4 3"' if dashed else ""
            self.parts.append(f'<rect x="{xx}" y="{y - 11}" width="16" height="12" rx="3" fill="{C[kind]}" '
                              f'stroke="{C[kind + "b"]}" stroke-width="1.3"{dash}/>')
            self.text(xx + 22, y, s, size=12, color=C["muted"])

    def save(self, path):
        """Close the document and write it to path, overwriting any existing file."""
        self.parts.append("</svg>")
        Path(path).write_text("\n".join(self.parts) + "\n")


def flow(out):
    """Write the diagram of a change's path, pull request to cluster, to out (flow.svg)."""
    s = Svg(900, 660, "gitops: from a pull request to the cluster",
            "A pull request is checked by rendering before it merges; each cluster's Argo CD applies main; "
            "Crossplane carries objects into the site's services.")
    s.text(20, 32, "gitops — from a pull request to the cluster", bold=True, size=18)
    s.text(20, 52, "Every change is rendered before it merges; only deploy-talos.py writes to main directly.",
           size=12, color=C["muted"])
    s.box(20, 92, 170, 64, "tool", ["you", "a branch, a pull request"])
    s.box(250, 80, 300, 172, "ext", title="Forgejo · alice/gitops")
    s.box(270, 110, 260, 52, "tool", ["pull request", "status, report, pac-bot's commit"])
    s.box(270, 186, 260, 52, "tool", ["main (protected)", "merges only when the check is green"])
    s.box(600, 80, 280, 172, "net", title="merge check · gitops-ci")
    s.box(615, 110, 250, 56, "wk", ["tools/ scripts", "check the tree; generate what follows"])
    s.box(615, 176, 250, 62, "wk", ["gitops-check", "renders before and after", "with argocd-preview"])
    s.line([(190, 124), (270, 136)], label="push", lx=228, ly=118)
    s.line([(530, 128), (615, 128)])
    s.line([(615, 150), (530, 150)])
    s.label(572, 108, "runs on it", size=11)
    s.line([(400, 162), (400, 186)], label="merge", lx=450, ly=178)
    s.box(20, 196, 190, 64, "tool", ["deploy-talos.py", "the add-ons it renders"])
    s.line([(210, 228), (270, 222)], dashed=True, label="pushes", lx=240, ly=246)
    s.box(20, 300, 860, 252, "net", title="each cluster · clusters/<name>/")
    s.box(40, 336, 250, 76, "wk", ["Argo CD", "app-of-apps addons:", "clusters/<name>/addons/"])
    s.line([(400, 238), (400, 270), (262, 270), (262, 336)], label="polls main (3 min)", lx=331, ly=274)
    s.box(330, 336, 250, 76, "wk", ["Applications, ApplicationSets", "each bounded by an AppProject"])
    s.box(620, 336, 240, 76, "wk", ["Kubernetes objects", "add-ons, services, teams'", "namespaces, CI"])
    s.line([(290, 374), (330, 374)])
    s.line([(580, 374), (620, 374)])
    s.box(330, 452, 250, 76, "cp", ["Crossplane providers", "managed resources from Git", "(cluster lab only)"])
    s.line([(455, 412), (455, 452)])
    s.box(250, 584, 410, 60, "ext", ["Keycloak, Forgejo, Harbor, Artifact Keeper",
                                     "groups, clients, teams, repositories, projects, robots"])
    s.line([(455, 528), (455, 584)], label="their APIs", lx=500, ly=562, anchor="start")
    s.save(out)


def tenancy(out):
    """Write the diagram of what the platform and a team each control to out (tenancy.svg)."""
    s = Svg(900, 610, "gitops: a team's bounds",
            "The platform decides where a team may deploy, from applications/; the team decides what, "
            "from its own repositories.")
    s.text(20, 32, "gitops — a team's bounds", bold=True, size=18)
    s.text(20, 52, "The platform decides where a team may deploy; the team decides what.",
           size=12, color=C["muted"])
    s.box(20, 80, 260, 100, "tool", ["this repository (platform)", "applications/<org>/<team>/team.yaml",
                                     "<ns>/base, <ns>/env/<env>"])
    s.box(320, 80, 260, 100, "ext", ["site services (Crossplane)", "Keycloak group, Forgejo team",
                                     "repositories, Harbor project", "Artifact Keeper repositories"])
    s.box(620, 80, 260, 100, "tool", ["the team's repositories", "<team>-gitops: apps/",
                                      "<team>-<app>: code, deploy/, .tekton/"])
    s.box(20, 222, 260, 70, "wk", ["platform Argo CD", "ApplicationSets, project tenants"])
    s.line([(150, 180), (150, 222)])
    s.line([(280, 240), (320, 160)], label="creates", lx=292, ly=200, anchor="end")
    s.box(20, 330, 860, 200, "net", title="cluster lab")
    s.line([(150, 292), (150, 330)], label="creates the namespaces", lx=160, ly=318,
           anchor="start")
    s.box(40, 366, 250, 100, "wk", ["<env>-<team>-<ns>", "quota, network policy", "Pod Security restricted",
                                    "ListenerSet, certificate"])
    s.box(325, 366, 250, 100, "wk", ["ci-<team>", "pipelines as user ci-<team>", "Pod Security baseline"])
    s.box(610, 366, 250, 100, "wk", ["team-<team>", "the team's Argo CD", "its Tekton Dashboard"])
    s.line([(750, 180), (735, 366)], label="syncs apps/", lx=752, ly=300, anchor="start")
    s.line([(680, 180), (480, 366)], label="webhook", lx=595, ly=262)
    s.line([(400, 366), (420, 180)], label="pushes images", lx=411, ly=262)
    s.line([(735, 466), (735, 500), (165, 500), (165, 466)], label="deploys, to its environments only",
           lx=450, ly=504)
    s.text(450, 566, "The team's Argo CD may write only its namespaces, through ClusterRole team-deployer: "
                     "no quotas, network policies,", anchor="middle", size=12, color=C["muted"])
    s.text(450, 584, "listeners or anything cluster-wide. Admission policies keep host names and routes "
                     "within the team.", anchor="middle", size=12, color=C["muted"])
    s.save(out)


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    flow(d / "flow.svg")
    tenancy(d / "tenancy.svg")

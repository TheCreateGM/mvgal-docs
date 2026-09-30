#!/usr/bin/env python3
"""MVGAL docs site generator.

Reads the Obsidian vault markdown docs (docs/*.md) and renders the static
HTML site (site/*.html) with a consistent sidebar, meta tags and footer.

Obsidian constructs that have no plain-Markdown equivalent are handled here so
the published site matches the vault:
  * ``> [!type]`` callouts        -> styled <div class="callout">
  * ```mermaid fences             -> <div class="mermaid"> + vendored mermaid.js
  * ```dataview fences            -> static HTML, precomputed from frontmatter
  * [[docs/NOTE|alias]] wikilinks  -> <a href="note.html">
  * vault-relative NOTE.md links    -> <a href="note.html">
Anything not recognised is rendered as a visible notice, never dropped.

Usage:
    python3 tools/generate_site.py
"""

import datetime
import json
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = ROOT / "site"
VAULT = ROOT                 # MOC.md and README.md live beside docs/, not in it.

VERSION = "0.7.16"
BASE_URL = "https://thecreategm.github.io/mvgal-docs/site/"
SITE_NAME = "MVGAL Documentation"
ABOUT = "Multi-Vendor GPU Aggregation Layer for Linux"
PUBLISHED = "2026-08-31"
MODIFIED = "2026-09-30"
OWNER = "TheCreateGM"
REPO = "mvgal-docs"
BLOB = f"https://github.com/{OWNER}/{REPO}/blob/main"

# Vendored, no CDN. Commit cec1bb7 removed the octicon/CDN dependencies and
# this stays dependency-free: mermaid ships as one UMD bundle next to styles.css.
MERMAID_JS = "mermaid.min.js"
MERMAID_VERSION = "10.9.3"

OCTICONS_CSS = ""

PAGES = [
    ("quickstart.html", "Quick Start", "Quick Start — MVGAL Documentation",
     "Inspect an installed MVGAL build, enumerate GPUs, and check daemon status. Package availability varies by distribution.",
     "MVGAL quick start, install MVGAL, COPR install, mvgald daemon, mvgal-info, get started, Fedora RHEL CentOS",
     "QUICKSTART.md"),
    ("install.html", "Installation", "Installation — MVGAL Documentation",
     "Review package availability or build MVGAL from source. Includes prerequisites and Secure Boot notes.",
     "MVGAL install, COPR, dnf install mvgal, Fedora RHEL CentOS, kernel module, Secure Boot, MOK, prerequisites",
     "INSTALL.md"),
    ("secure_boot.html", "Secure Boot", "Secure Boot & MOK Enrollment — MVGAL Documentation",
     "Enroll the MVGAL signing key with MOK for Secure Boot systems: mvgal-enroll-mok, manual enrollment, verification with mokutil, and troubleshooting.",
     "MVGAL Secure Boot, MOK enrollment, mvgal-enroll-mok, mokutil, DKMS signing, UEFI, kernel module signing",
     "SECURE_BOOT.md"),
    ("build.html", "Building", "Building — MVGAL Documentation",
     "Build MVGAL from source with CMake, Meson or Zig on Fedora and RHEL. Prerequisites, build options, targets and packaging.",
     "MVGAL build, build from source, CMake, Meson, Zig, compile MVGAL, Fedora RHEL build, packaging RPM",
     "BUILD.md"),
    ("architecture.html", "Architecture", "Architecture — MVGAL Documentation",
     "MVGAL system architecture, kernel module, userspace runtime and API layers: kernel HAL, vendor drivers, runtime daemon, execution engine, scheduler, Rust safety crates, API interception and tooling.",
     "MVGAL architecture, kernel module, read-only GPU discovery, runtime capability probes, userspace APIs",
     "ARCHITECTURE.md"),
    ("design.html", "Design", "Design — MVGAL Documentation",
     "MVGAL design goals, component boundaries, and distinctions between proposed and verified behavior.",
     "MVGAL design, architecture decisions, DRM meta-driver, C++20 daemon, Unix socket IPC, LD_PRELOAD, design goals",
     "DESIGN.md"),
    ("api.html", "API Reference", "API Reference — MVGAL Documentation",
     "Public C API reference for MVGAL: initialization, context management, execution control, scheduling strategies, stats, fences and semaphores.",
     "MVGAL API, C API reference, mvgal_init, context management, execution control, scheduling strategy, fences, semaphores, mvgal_ functions",
     "API.md"),
    ("strategies.html", "Scheduling Strategies", "Scheduling Strategies — MVGAL Documentation",
     "Public MVGAL scheduling strategy identifiers and the current limitations on runtime dispatch.",
     "MVGAL scheduling, GPU scheduler, round-robin, least-load, bin-packing, GPU-aware, hybrid, RLD, REP, PPL, workload distribution, memory heap",
     "STRATEGIES.md"),
    ("memory.html", "Memory Management", "Memory Management — MVGAL Documentation",
     "MVGAL memory APIs and runtime capability limits for allocation, DMA-BUF, and peer transfers.",
     "MVGAL memory, unified VRAM, DMA-BUF, PCIe P2P, host-RAM staging, memory manager, NUMA, memory flags, prefetching, Rust memory safety",
     "MEMORY.md"),
    ("hardware.html", "Hardware Compatibility", "Hardware Compatibility — MVGAL Documentation",
     "Recognized PCI GPU vendors, native driver ownership, and how to inspect runtime capability reports.",
     "MVGAL hardware, supported GPUs, AMD RDNA, NVIDIA Turing Ampere Ada, Intel Arc, Moore Threads MTT, driver support, kernel requirements, feature matrix",
     "HARDWARE_COMPATIBILITY.md"),
    ("steam.html", "Steam / Proton", "Steam / Proton — MVGAL Documentation",
     "Steam and Proton helper components, their environment variables, and capability-dependent behavior.",
     "MVGAL Steam, Proton, gaming, Vulkan layer, frame pacer, AFR, NTSYNC, DXVK, VKD3D-Proton, ENABLE_MVGAL, MVGAL_STRATEGY",
     "STEAM_INTEGRATION.md"),
    ("power.html", "Power Management", "Power Management — MVGAL Documentation",
     "MVGAL power interfaces and capability-dependent vendor controls; unsupported operations are reported explicitly.",
     "MVGAL power management, runtime capability probing, native driver controls",
     "POWER_MANAGEMENT.md"),
    ("troubleshooting.html", "Troubleshooting", "Troubleshooting — MVGAL Documentation",
     "Troubleshoot MVGAL: daemon not starting, Vulkan layer missing, Secure Boot / MOK failures, GPU not detected, kernel module, common fixes and diagnostics.",
     "MVGAL troubleshooting, daemon, Vulkan layer, MOK, Secure Boot, GPU not detected, kernel module, common fixes, diagnostics",
     "TROUBLESHOOTING.md"),
    ("status.html", "Project Status", "Project Status — MVGAL Documentation",
     "MVGAL source version, release provenance, and verified runtime capability boundaries.",
      "MVGAL status, source version 0.7.14, release provenance, capability boundaries",
      "STATUS.md"),
    ("changelog.html", "Changelog", "Changelog — MVGAL Documentation",
      "MVGAL release history and changelog: source release history through v0.7.14, bug fixes, new features, known issues and release notes.",
      "MVGAL changelog, release notes through v0.7.14, version history, DKMS, Secure Boot",
      "CHANGELOG.md"),
]

NAV_LABELS = {f: label for f, label, *_ in PAGES}

NAV_SECTIONS = [
    ("Getting Started", [
        ("index.html", "Home", "file-code"),
        ("quickstart.html", "Quick Start", "rocket"),
        ("install.html", "Installation", "download"),
        ("secure_boot.html", "Secure Boot", "shield-lock"),
        ("build.html", "Building", "tools"),
    ]),
    ("Architecture & Design", [
        ("architecture.html", "Architecture", "stack"),
        ("design.html", "Design", "book"),
    ]),
    ("Core Subsystems", [
        ("api.html", "API Reference", "terminal"),
        ("strategies.html", "Scheduling Strategies", "git-branch"),
        ("memory.html", "Memory Management", "cpu"),
        ("power.html", "Power Management", "zap"),
    ]),
    ("Ecosystem", [
        ("hardware.html", "Hardware Compatibility", "server"),
        ("steam.html", "Steam / Proton", "gamepad-2"),
    ]),
    ("Project", [
        ("troubleshooting.html", "Troubleshooting", "bug"),
        ("status.html", "Project Status", "pulse"),
        ("changelog.html", "Changelog", "checklist"),
    ]),
]

def octicon(name, size=16, extra_class=""):
    return ""

NAV_COUNT = len(PAGES) + 1

MD = markdown.Markdown(
    extensions=["fenced_code", "tables", "toc", "attr_list"],
    output_format="html5",
)
# Callout bodies are converted with a second instance so the nested conversion
# cannot clobber the outer document's parser state.
CALLOUT_MD = markdown.Markdown(
    extensions=["fenced_code", "tables", "toc", "attr_list"],
    output_format="html5",
)

# "QUICKSTART" -> "quickstart.html", so [[docs/API|API]] can be resolved.
NOTE_HTML = {entry[5][:-3]: entry[0] for entry in PAGES}

# Per-page counts of each Obsidian construct that was converted, reported by
# main() so a regression (a callout that stopped rendering) is visible.
TALLY: dict[str, dict] = {}

CALLOUT_TYPES = {
    "note": "Note", "abstract": "Abstract", "summary": "Summary", "tldr": "TL;DR",
    "info": "Info", "todo": "Todo", "tip": "Tip", "hint": "Hint",
    "success": "Success", "check": "Check", "done": "Done",
    "question": "Question", "help": "Help", "faq": "FAQ",
    "warning": "Warning", "caution": "Caution", "attention": "Attention",
    "important": "Important",
    "failure": "Failure", "fail": "Fail", "missing": "Missing",
    "danger": "Danger", "error": "Error", "bug": "Bug",
    "example": "Example", "quote": "Quote", "cite": "Cite",
}

# "> [!warning] Title" — Obsidian's real form has a space after the '>'.
CALLOUT_OPEN = re.compile(r"^>[ \t]*\[!([A-Za-z]+)\]([+-]?)[ \t]*(.*)$")
MERMAID_FENCE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
DATAVIEW_FENCE = re.compile(r"^```dataview[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
WIKILINK = re.compile(r"\[\[([^\[\]|]+?)(?:\\?\|([^\[\]]*?))?\]\]")
# Protected so a literal [[...]] or $env inside a snippet survives untouched.
CODE_REGION = re.compile(r"(`+[^`]*`+|<pre\b.*?</pre>|<code\b.*?</code>)", re.S)


def _scalar(v: str):
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
    return v.strip("'\"")


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split an Obsidian note into (frontmatter mapping, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}, text
    meta = {}
    for line in parts[1].splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = _scalar(val.strip())
    return meta, parts[2].lstrip("\n")


def strip_frontmatter(text: str) -> str:
    return split_frontmatter(text)[1]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escattr(s: str) -> str:
    return esc(s).replace('"', "&quot;").replace("'", "&#39;")


def _note_index() -> list[dict]:
    """One record per vault note, for Dataview precomputation."""
    skip = {".tmp", ".obsidian", "site", "package", ".git"}
    notes = []
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in skip or path.name == "README.md" and rel.parts[0] == "package":
            continue
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        st = path.stat()
        stem = path.stem
        notes.append({
            "name": stem,
            "path": rel.as_posix(),
            "folder": rel.parent.as_posix(),
            "link": NOTE_HTML.get(stem, stem + ".html"),
            "mtime": datetime.date.fromtimestamp(st.st_mtime),
            "ctime": datetime.date.fromtimestamp(st.st_ctime),
            "meta": meta,
        })
    return notes


# ── Obsidian constructs ─────────────────────────────────────────────────────

def extract_callouts(text: str) -> tuple[str, list[str], list[str]]:
    """Replace > [!type] blockquotes with placeholders.

    The body is converted as its own markdown document so lists, tables and
    fenced code inside a callout still render. Returns
    (text, rendered blocks, unknown type names).
    """
    lines = text.split("\n")
    out: list[str] = []
    blocks: list[str] = []
    unknown: list[str] = []
    i = 0
    while i < len(lines):
        m = CALLOUT_OPEN.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        kind, fold, title = m.group(1).lower(), m.group(2), m.group(3).strip()
        label = CALLOUT_TYPES.get(kind)
        if label is None:
            label = kind.replace("-", " ").title()
            unknown.append(kind)
        if not title:
            title = label
        elif fold == "+":
            title = f"{label} \u25be {title}"
        elif fold == "-":
            title = f"{label} \u25b8 {title}"
        i += 1
        body: list[str] = []
        while i < len(lines):
            ln = lines[i]
            if CALLOUT_OPEN.match(ln):
                # A sibling callout after a blank line, not body text: plain
                # Markdown would merge the two blockquotes, Obsidian does not.
                break
            if ln.startswith(">"):
                body.append(re.sub(r"^[> \t]+", "", ln).rstrip())
                i += 1
            elif not ln.strip():
                j = i
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and lines[j].startswith(">"):
                    body.extend([""] * (j - i))
                    i = j
                else:
                    break
            elif body and ln[0] in " \t":
                body.append(ln)          # lazy continuation of the last line
                i += 1
            else:
                break
        CALLOUT_MD.reset()
        inner = CALLOUT_MD.convert("\n".join(body).strip())
        blocks.append(
            f'<div class="callout callout-{escattr(kind)}">'
            f'<div class="callout-title">{escattr(title)}</div>'
            f'<div class="callout-body">{inner}</div>'
            f"</div>"
        )
        out.append(f"\x00CALLOUT{len(blocks) - 1}\x00")
    return "\n".join(out), blocks, unknown


def preprocess_mermaid(text: str) -> tuple[str, int]:
    """Turn ```mermaid fences into raw <div class="mermaid"> blocks.

    The diagram source is HTML-escaped, so the browser hands mermaid back the
    exact original text via textContent — <br/> in labels keeps working.
    """
    count = 0

    def sub(m: re.Match) -> str:
        nonlocal count
        count += 1
        return f'<div class="mermaid">\n{esc(m.group(1).strip())}\n</div>\n'

    return MERMAID_FENCE.sub(sub, text), count


def mermaid_script() -> str:
    return (
        f'<script src="{MERMAID_JS}"></script>\n'
        "<script>\n"
        "if (window.mermaid) {\n"
        "  mermaid.initialize({startOnLoad: true, securityLevel: 'strict',\n"
        "    theme: 'neutral', flowchart: {htmlLabels: true, useMaxWidth: true}});\n"
        "}\n"
        "</script>\n"
    )


MD_LINK = re.compile(r'<a href="([^":]+\.md)(#[^"]*)?">')


def resolve_links(html: str) -> tuple[str, int]:
    """Point both Obsidian wikilinks and vault-relative .md links at the site.

    Markdown links such as ``[Build Guide](BUILD.md)`` are correct inside the
    vault but 404 on the published site, where the note is ``build.html``.
    Anything that has no published page (e.g. MOC.md) becomes a visible
    ``wikilink-missing`` span rather than a dead link.
    """
    count = 0
    parts = CODE_REGION.split(html)

    def wiki(m: re.Match) -> str:
        nonlocal count
        target = m.group(1).replace("\\", "").strip()
        label = (m.group(2) or "").replace("\\", "").strip() or target
        href = NOTE_HTML.get(target.rsplit("/", 1)[-1])
        if href is None:
            return f'<span class="wikilink-missing">{escattr(label)}</span>'
        count += 1
        return f'<a href="{href}">{escattr(label)}</a>'

    def md(m: re.Match) -> str:
        nonlocal count
        stem = m.group(1).rsplit("/", 1)[-1]
        href = NOTE_HTML.get(stem[:-3])
        if href is not None:
            count += 1
            return f'<a href="{href}{m.group(2) or ""}">'
        if (VAULT / stem).is_file():
            # A real note that this site does not publish (MOC.md, README.md).
            # Link to its source rather than leaving a dead href.
            return f'<a href="{BLOB}/{stem}{m.group(2) or ""}" class="external">'
        return m.group(0)

    for i in range(0, len(parts), 2):     # odd indices are protected regions
        parts[i] = WIKILINK.sub(wiki, parts[i])
        parts[i] = MD_LINK.sub(md, parts[i])
    return "".join(parts), count


# ── Dataview: the subset of the query language this vault actually uses ──────

DV_TABLE = re.compile(r"^TABLE\s+(?:WITHOUT\s+ID)?\s*$", re.I)
DV_LIST = re.compile(r"^LIST\b", re.I)
DV_CLAUSE = re.compile(r"^(FROM|WHERE|SORT)\b", re.I)
DV_FROM = re.compile(r'^FROM\s+(?:"([^"]+)"|#([A-Za-z0-9_/-]+))\s*$', re.I)
DV_WHERE = re.compile(r"^WHERE\s+(.+)$", re.I)
DV_SORT = re.compile(r"^SORT\s+(\S+)\s+(ASC|DESC)\s*$", re.I)
DV_DATE = re.compile(r"^date\((\d{4})-(\d{2})-(\d{2})\)$", re.I)
DV_CMP = re.compile(r"^(\S+)\s*(>=|<=|!=|=|>|<)\s*(.+)$")


def dataview_field(rec: dict, key: str):
    if key == "file.link":
        return rec["link"]
    if key == "file.name":
        return rec["name"]
    if key == "file.path":
        return rec["path"]
    if key == "file.folder":
        return rec["folder"]
    if key == "file.mtime":
        return rec["mtime"]
    if key == "file.ctime":
        return rec["ctime"]
    return rec["meta"].get(key, "")


def _sort_key(value) -> tuple:
    if isinstance(value, datetime.date):
        return (0, value.toordinal(), "")
    return (1, 0, str(value))


def _dv_where(expr: str, rec: dict) -> bool:
    m = DV_CMP.match(expr.strip())
    if not m:
        return True
    key, op, lit = m.group(1), m.group(2), m.group(3).strip()
    d = DV_DATE.match(lit)
    if d:
        want = datetime.date(int(d.group(1)), int(d.group(2)), int(d.group(3)))
    else:
        want = lit.strip("'\"")
    got = dataview_field(rec, key)
    if got == "" or got is None:
        return op == "!="
    ga, wa = _sort_key(got), _sort_key(want)
    c = (ga > wa) - (ga < wa)
    return {"=": c == 0, "!=": c != 0, ">": c > 0, "<": c < 0,
            ">=": c >= 0, "<=": c <= 0}[op]


def _dv_unsupported(query: str) -> str:
    return (
        '<div class="callout callout-warning"><div class="callout-title">Dataview</div>'
        '<div class="callout-body">This query uses Dataview syntax the site '
        'generator does not precompute. Open the note in the Obsidian vault, or '
        'simplify the query to <code>TABLE</code>/<code>LIST</code> with '
        '<code>FROM</code>, <code>WHERE</code> and <code>SORT</code>.<br>'
        f"<code>{escattr(query.strip().splitlines()[0])}</code></div></div>"
    )


def render_dataview(query: str, notes: list[dict] | None = None) -> str:
    """Precompute a Dataview query into static HTML.

    Supports TABLE [WITHOUT ID] and LIST with FROM "folder" / FROM #tag,
    WHERE <field> <op> <literal> and SORT <field> ASC|DESC. Anything outside
    that subset renders a visible notice instead of silently vanishing.
    """
    notes = _note_index() if notes is None else notes
    lines = [l.strip() for l in query.strip().splitlines() if l.strip()]
    if not lines:
        return _dv_unsupported(query)
    if DV_TABLE.match(lines[0]):
        mode = "table"
    elif DV_LIST.match(lines[0]):
        mode = "list"
    else:
        return _dv_unsupported(query)

    columns: list[tuple[str, str]] = []
    head = 1
    while head < len(lines) and not DV_CLAUSE.match(lines[head]):
        spec = lines[head].rstrip(",").strip()
        if spec:
            am = re.match(r'^(\S+)\s+AS\s+"(.*)"$', spec, re.I)
            if am:
                columns.append((am.group(1), am.group(2) or am.group(1)))
            elif mode == "table":
                columns.append((spec, spec.rsplit(".", 1)[-1]))
        head += 1

    source = ("tag", "mvgal")
    where = sort = None
    for line in lines[head:]:
        m = DV_FROM.match(line)
        if m:
            source = ("folder", m.group(1)) if m.group(1) else ("tag", m.group(2))
            continue
        m = DV_WHERE.match(line)
        if m:
            where = m.group(1)
            continue
        m = DV_SORT.match(line)
        if m:
            sort = (m.group(1), m.group(2).upper())
            continue
        return _dv_unsupported(query)

    kind, value = source
    if kind == "folder":
        rows = [r for r in notes if value in ("", "/") or r["path"].startswith(value + "/")
                or r["folder"] == value]
    else:
        rows = [r for r in notes
                if value in [t.lstrip("#") for t in r["meta"].get("tags", [])]]
    if where:
        rows = [r for r in rows if _dv_where(where, r)]
    if sort:
        rows = sorted(rows, key=lambda r: _sort_key(dataview_field(r, sort[0])),
                      reverse=sort[1] == "DESC")

    if mode == "list":
        if not rows:
            return '<p class="dv-empty">No matching notes.</p>'
        items = "".join(
            f'<li><a href="{r["link"]}">{escattr(r["name"])}</a></li>' for r in rows
        )
        return f'<ul class="dv-list">{items}</ul>'

    if not columns:
        return _dv_unsupported(query)
    head_cells = "".join(f"<th>{escattr(alias)}</th>" for _, alias in columns)
    body_rows = []
    for r in rows:
        cells = []
        for key, _alias in columns:
            val = dataview_field(r, key)
            if key == "file.link":
                cells.append(f'<td><a href="{r["link"]}">{escattr(r["name"])}</a></td>')
            elif isinstance(val, datetime.date):
                cells.append(f"<td>{val.isoformat()}</td>")
            else:
                cells.append(f"<td>{escattr(str(val))}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    if not body_rows:
        body_rows.append(f'<tr><td colspan="{len(columns)}" class="dv-empty">'
                         "No matching notes.</td></tr>")
    return ('<div class="table-wrap"><table class="dv-table">'
            f"<thead><tr>{head_cells}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody></table></div>")


def extract_dataview(text: str) -> tuple[str, list[str]]:
    """Replace ```dataview fences with placeholders holding precomputed HTML."""
    blocks: list[str] = []

    def sub(m: re.Match) -> str:
        blocks.append(render_dataview(m.group(1)))
        return f"\x00DATAVIEW{len(blocks) - 1}\x00"

    return DATAVIEW_FENCE.sub(sub, text), blocks


def inject_blocks(html: str, blocks: list[str], prefix: str) -> str:
    for idx, block in enumerate(blocks):
        html = html.replace(f"\x00{prefix}{idx}\x00", block)
    return html


def json_ld_doc(title: str, desc: str, url: str, keywords: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title,
        "name": title,
        "description": desc,
        "url": url,
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE_URL + "index.html"},
        "publisher": {"@type": "Organization", "name": "MVGAL",
                      "logo": {"@type": "ImageObject", "url": BASE_URL + "favicon.svg"}},
        "about": ABOUT,
        "keywords": keywords,
        "datePublished": PUBLISHED,
        "dateModified": MODIFIED,
        "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL + "index.html"},
            {"@type": "ListItem", "position": 2, "name": title, "item": url},
        ]},
    }
    return json.dumps(data, ensure_ascii=False)


def json_ld_index() -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "headline": "MVGAL — Multi-Vendor GPU Aggregation Layer for Linux",
        "name": "MVGAL — Multi-Vendor GPU Aggregation Layer for Linux",
        "description": "MVGAL explores cross-vendor GPU discovery and application integration on Linux. Runtime capabilities are probed; unsupported submission and allocation paths fail explicitly.",
        "url": BASE_URL + "index.html",
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE_URL + "index.html"},
        "publisher": {"@type": "Organization", "name": "MVGAL",
                      "logo": {"@type": "ImageObject", "url": BASE_URL + "favicon.svg"}},
        "about": ABOUT,
        "keywords": "MVGAL, Linux GPU discovery, kernel module, userspace runtime, Vulkan, OpenCL, CUDA, runtime capabilities",
        "datePublished": PUBLISHED,
        "dateModified": MODIFIED,
    }
    return json.dumps(data, ensure_ascii=False)


def app_header(active_page: str) -> str:
    return f"""<header class="app-header">
  <div class="header-left">
    <button class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false">&#9776;</button>
    <div class="header-repo">
      <span class="header-repo-owner">{OWNER}</span>
      <span class="header-repo-slash">/</span>
      <a class="header-repo-name" href="index.html">{REPO}</a>
    </div>
    <span class="badge-accent badge">Public</span>
  </div>
  <div class="header-search" role="search" aria-label="Search documentation">
    {octicon("search", 16)}
    <input id="docs-search" type="search" role="combobox" aria-autocomplete="list" aria-haspopup="listbox" autocomplete="off" placeholder="Search documentation" aria-label="Search documentation" aria-controls="docs-search-results" aria-expanded="false">
    <kbd>/</kbd>
    <div class="search-results" id="docs-search-results" role="listbox" aria-label="Documentation pages" hidden></div>
  </div>
  <div class="header-actions">
    <a href="quickstart.html" class="btn btn-primary">
      {octicon("repo-push", 16)}
      <span>Get Started</span>
    </a>
    <a href="changelog.html" class="btn btn-sm">
      {octicon("tag", 14)}
      <span>v{VERSION}</span>
    </a>
  </div>
</header>
<script>
(function(){{
  var TOAST_OK = '{octicon("check", 16, "toast-icon")}';
  var TOAST_INFO = '{octicon("info", 16, "toast-icon")}';
  var toastTimer = null;
  function showToast(msg, kind) {{
    kind = kind || 'success';
    var t = document.getElementById('mvgal-toast');
    if (!t) {{
      t = document.createElement('div');
      t.id = 'mvgal-toast';
      t.className = 'toast';
      document.body.appendChild(t);
    }}
    t.className = 'toast toast-' + kind + ' show';
    t.innerHTML = (kind === 'success' ? TOAST_OK : TOAST_INFO) + '<span>' + msg + '</span>';
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function() {{ t.classList.remove('show'); }}, 2200);
  }}
  window._showToast = showToast;

  var searchInput = document.getElementById('docs-search');
  var searchResults = document.getElementById('docs-search-results');
  var searchPages = {json.dumps([{"href": page[0], "title": page[2].split(" — ")[0], "description": page[3]} for page in PAGES], ensure_ascii=False)};
  function closeSearch() {{
    if (!searchInput || !searchResults) return;
    searchResults.hidden = true;
    searchInput.setAttribute('aria-expanded', 'false');
  }}
  if (searchInput && searchResults) {{
    searchInput.addEventListener('input', function() {{
      var query = searchInput.value.trim().toLocaleLowerCase();
      searchResults.replaceChildren();
      if (!query) {{ closeSearch(); return; }}
      var matches = searchPages.filter(function(page) {{
        return (page.title + ' ' + page.description).toLocaleLowerCase().includes(query);
      }}).slice(0, 8);
      matches.forEach(function(page) {{
        var link = document.createElement('a');
        link.href = page.href;
        link.setAttribute('role', 'option');
        link.textContent = page.title;
        searchResults.appendChild(link);
      }});
      if (!matches.length) {{
        var empty = document.createElement('p');
        empty.textContent = 'No matching pages';
        searchResults.appendChild(empty);
      }}
      searchResults.hidden = false;
      searchInput.setAttribute('aria-expanded', 'true');
    }});
    searchInput.addEventListener('keydown', function(e) {{
      if (e.key === 'Escape') {{ closeSearch(); searchInput.blur(); }}
      if (e.key === 'Enter' && searchResults.querySelector('a')) {{
        window.location.href = searchResults.querySelector('a').href;
      }}
    }});
    document.addEventListener('click', function(e) {{
      if (!e.target.closest('.header-search')) closeSearch();
    }});
  }}
  document.addEventListener('keydown', function(e) {{
    var inInput = e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
    if (e.key === '/' && !inInput) {{
      e.preventDefault();
      if (searchInput) searchInput.focus();
    }}
  }});

  var toggle = document.querySelector('.menu-toggle');
  var sidebar = document.querySelector('nav.sidebar');
  var backdrop = document.querySelector('.sidebar-backdrop');
  function setSidebarOpen(open) {{
    if (!sidebar || !toggle) return;
    sidebar.classList.toggle('open', open);
    document.body.classList.toggle('sidebar-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (backdrop) backdrop.hidden = !open;
    if (open) sidebar.querySelector('a')?.focus();
  }}
  if (toggle && sidebar) {{
    toggle.addEventListener('click', function(){{ setSidebarOpen(!sidebar.classList.contains('open')); }});
    if (backdrop) backdrop.addEventListener('click', function() {{ setSidebarOpen(false); toggle.focus(); }});
    document.addEventListener('keydown', function(e) {{
      if (e.key === 'Escape' && sidebar.classList.contains('open')) {{ setSidebarOpen(false); toggle.focus(); }}
    }});
    sidebar.querySelectorAll('a').forEach(function(a){{
      a.addEventListener('click', function(){{
        setSidebarOpen(false);
      }});
    }});
  }}
}})();
</script>
"""


def repo_tabs(active_page: str) -> str:
    tabs = [
        ("index.html", "Code", True, "Code"),
        ("api.html", "API", False, "API"),
        ("architecture.html", "Architecture", False, "Architecture"),
        ("status.html", "Status", False, "Status"),
        ("changelog.html", "Changelog", False, "Changelog"),
    ]
    items = []
    for href, label, is_code, display in tabs:
        is_active = active_page == href or (is_code and active_page == "index.html")
        count = ""
        if is_code:
            count = f'<span class="tab-count">{NAV_COUNT}</span>'
        items.append(f'<a class="repo-tab{" active" if is_active else ""}" href="{href}">{label}{count}</a>')
    return f"""<div class="repo-tabs">
{chr(10).join(items)}
</div>
"""


def breadcrumbs(active_page: str, title: str = "") -> str:
    page_title = title or NAV_LABELS.get(active_page, "Home")
    md_filename = ""
    for entry in PAGES:
        if entry[0] == active_page:
            md_filename = entry[5]
            break
    if active_page == "index.html":
        md_filename = "README.md"
    file_label = md_filename or "index.html"
    return f"""<div class="breadcrumbs">
  <a class="crumb-link" href="index.html">{OWNER}</a>
  <span class="crumb-slash">/</span>
  <a class="crumb-link" href="index.html">{REPO}</a>
  <span class="crumb-slash">/</span>
  <span class="crumb" title="{OWNER}/{REPO}/blob/main/{file_label}">blob</span>
  <span class="crumb-slash">/</span>
  <span class="crumb" title="{OWNER}/{REPO}/blob/main/{file_label}">main</span>
  <span class="crumb-slash">/</span>
  <a class="crumb-current" href="{active_page}">{esc(file_label)}</a>
</div>
"""


def sidebar(active: str) -> str:
    links_html = []
    links_html.append(f'<div class="sidebar-brand">')
    links_html.append(f'  <div class="sb-title">{octicon("file-directory", 16)} Documentation</div>')
    links_html.append(f'  <div class="sb-sub">v{VERSION} · GPL-2.0/3.0 · MIT/Apache-2.0</div>')
    links_html.append(f'</div>')

    for section_name, section_items in NAV_SECTIONS:
        links_html.append(f'<div class="sidebar-section-title">{section_name}</div>')
        links_html.append(f'<div class="sidebar-section">')
        for fname, label, icon in section_items:
            cls = ' class="active"' if fname == active else ""
            links_html.append(f'<a href="{fname}"{cls}>{octicon(icon, 16, "nav-icon")}<span>{label}</span></a>')
        links_html.append(f'</div>')
        if section_name != NAV_SECTIONS[-1][0]:
            links_html.append(f'<div class="sidebar-divider"></div>')

    return f"""<nav class="sidebar">
{chr(10).join(links_html)}
</nav>
"""


FOOTER = f"""  </main>
  <footer>
    <div>© 2026 MVGAL Project · v{VERSION} · <a href="status.html" style="color: inherit; text-decoration: none;">Project Status</a></div>
    <div class="footer-links">
      <a href="changelog.html">Changelog</a>
      <a href="troubleshooting.html">Troubleshooting</a>
      <a href="api.html">API Reference</a>
      <a href="architecture.html">Architecture</a>
      <a href="hardware.html">Hardware</a>
    </div>
  </footer>
  </div>
  </div>
"""

FOOTER_TAIL = """</body>
</html>
"""


def page_header_actions(active_page: str) -> str:
    if active_page == "index.html":
        return ""
    return f"""<div class="page-header-actions">
  <button class="btn btn-sm" title="Copy link" onclick="window._showToast&&window._showToast('Link copied to clipboard');try{{if(navigator.clipboard)navigator.clipboard.writeText(location.href).catch(function(){{}});}}catch(e){{}}">
    {octicon("link", 14)}
    <span>Copy link</span>
  </button>
  <a href="quickstart.html" class="btn btn-sm btn-primary">
    {octicon("check-circle", 14)}
    <span>Quick Start</span>
  </a>
</div>
"""


def render_markdown(fname: str, md_src: str) -> tuple[str, dict]:
    """Convert one vault note to HTML, resolving Obsidian-only constructs."""
    src = (DOCS / md_src).read_text(encoding="utf-8")
    md_text, callouts, unknown = extract_callouts(strip_frontmatter(src))
    md_text, mermaid_n = preprocess_mermaid(md_text)
    md_text, dataview = extract_dataview(md_text)
    MD.reset()
    body = MD.convert(md_text)
    body = inject_blocks(body, callouts, "CALLOUT")
    body = inject_blocks(body, dataview, "DATAVIEW")
    body, links = resolve_links(body)
    return body, {
        "callouts": len(callouts),
        "unknown_callout_types": unknown,
        "mermaid": mermaid_n,
        "dataview": len(dataview),
        "links": links,
    }


def render_doc_page(fname: str, label: str, title: str, desc: str, keywords: str, md_src: str) -> str:
    body, stats = render_markdown(fname, md_src)
    TALLY.setdefault(fname, stats)
    url = BASE_URL + fname
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="{esc(keywords)}">
<meta name="author" content="MVGAL Project">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="generator" content="MVGAL docs site generator">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE_URL}favicon.svg">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{BASE_URL}favicon.svg">
<script type="application/ld+json">{json_ld_doc(title, desc, url, keywords)}</script>
<link rel="stylesheet" href="styles.css">
{OCTICONS_CSS}
</head>
<body>
{app_header(fname)}
<div class="app-shell">
{sidebar(fname)}
<button class="sidebar-backdrop" type="button" aria-label="Close navigation" hidden></button>
<div class="content-wrap">
{repo_tabs(fname)}
<main>
{breadcrumbs(fname)}
    <div class="page-header">
  <div></div>
  {page_header_actions(fname)}
</div>
{body}
"""
    html += FOOTER
    html += mermaid_script() if TALLY[fname]["mermaid"] else ""
    html += FOOTER_TAIL
    return html



def render_index() -> str:
    title = "MVGAL — Multi-Vendor GPU Aggregation Layer for Linux"
    desc = "MVGAL explores cross-vendor GPU discovery and application integration on Linux. Runtime capabilities are probed; unsupported submission and allocation paths fail explicitly."
    keywords = "MVGAL, Linux GPU discovery, kernel module, userspace runtime, Vulkan, OpenCL, CUDA, runtime capabilities"
    url = BASE_URL + "index.html"
    fname = "index.html"

    cards_spec = [
        ("quickstart.html", "Quick Start", "Inspect GPUs and check daemon status.", "rocket", "Linux", "Diagnostics"),
        ("install.html", "Installation", "Check package availability or build from source.", "download", "CMake", "2 methods"),
        ("secure_boot.html", "Secure Boot", "MOK enrollment for packages that install signed modules.", "shield-lock", "MOK", "UEFI"),
        ("build.html", "Building", "Build with the repository CMake or Meson configuration.", "tools", "CMake", "Build systems"),
        ("architecture.html", "Architecture", "Kernel, runtime, APIs, packaging and tools.", "stack", "C/C++", "Subsystems"),
        ("design.html", "Design", "Design goals and architecture decisions.", "book", "C++20", "Decisions"),
        ("api.html", "API Reference", "Complete public C API reference.", "terminal", "C", "Public headers"),
        ("strategies.html", "Scheduling Strategies", "Scheduling strategy identifiers and availability notes.", "git-branch", "C", "Strategy API"),
        ("memory.html", "Memory Management", "Memory interfaces and capability-dependent support.", "cpu", "DMA-BUF", "Capabilities"),
        ("hardware.html", "Hardware Compatibility", "GPU discovery and runtime capability reporting.", "server", "Vulkan", "4 vendors"),
        ("steam.html", "Steam / Proton", "Steam and Proton integration components.", "gamepad-2", "Proton", "Gaming"),
        ("power.html", "Power Management", "Capability-dependent power controls.", "zap", "DVFS", "Thermal"),
        ("troubleshooting.html", "Troubleshooting", "Common issues and solutions.", "bug", "Linux", "Diagnostics"),
        ("status.html", "Project Status", "Current milestone and status.", "pulse", "Status", "Milestone"),
        ("changelog.html", "Changelog", "Source release history through v0.7.12.", "checklist", "Releases", "release history"),
    ]

    card_html = "\n".join(
        f'''<a class="card" href="{f}">
  <div class="card-header">
    {octicon(icon, 16, "card-icon")}
    <h3>{t}</h3>
  </div>
  <p>{d}</p>
  <div class="card-meta">
    <span class="meta-item"><span class="lang-dot"></span>{lang}</span>
    <span class="meta-item">
      {octicon("dot", 12)}
      {meta}
    </span>
  </div>
</a>'''
        for f, t, d, icon, lang, meta in cards_spec
    )

    body = f"""{breadcrumbs(fname)}
<div class="page-header">
  <div></div>
  <div class="page-header-actions">
    <a href="install.html" class="btn">
      {octicon("download", 16)}
      <span>Install</span>
    </a>
    <a href="quickstart.html" class="btn btn-primary">
      {octicon("check-circle", 16)}
      <span>Quick Start</span>
    </a>
  </div>
</div>
<div class="hero">
  <h1>MVGAL — Multi-Vendor GPU Aggregation Layer</h1>
  <p>GPU discovery and integration components for Linux. Runtime capabilities are probed; unsupported operations fail explicitly.</p>
  <p style="margin-top:16px">
    <span class="badge badge-success">v{VERSION}</span>
    <span class="badge badge-accent">AMD · NVIDIA · Intel · Moore Threads</span>
    <span class="badge">Vulkan · OpenCL · CUDA</span>
  </p>
  <div class="hero-actions">
    <a href="quickstart.html" class="btn btn-primary">
      {octicon("rocket", 16)}
      Get Started
    </a>
    <a href="architecture.html" class="btn">
      {octicon("stack", 16)}
      View Architecture
    </a>
    <a href="api.html" class="btn">
      {octicon("book", 16)}
      API Reference
    </a>
  </div>
</div>
<h2>Documentation</h2>
<div class="card-grid">
{card_html}
</div>
<h2>What is MVGAL?</h2>
<p>Most Linux systems with multiple GPUs (e.g. an AMD RX 7900 + NVIDIA RTX 4080) treat each card as a completely separate device. Applications can only use one at a time, leaving the other idle.</p>
<p>MVGAL explores cross-vendor GPU discovery, runtime interfaces, scheduling, and application integration. The kernel module discovers devices without binding them away from native drivers. As of 0.7.14, unsupported kernel submission and VRAM allocation fail with <code>-EOPNOTSUPP</code>, and the Vulkan ICD does not advertise a synthetic aggregate physical device. Verify each API path and probed capability on the target system.</p>
<h2>Quick Start</h2>
<pre><code># Start the daemon (the unit is mvgal-daemon.service; enable also creates
# the mvgald.service and mvgal.service aliases)
pkexec systemctl enable --now mvgal-daemon

# Verify
mvgal-info          # list detected GPUs
mvgal-status --once # status snapshot
mvgal-compat --system   # check readiness</code></pre>
<h2>License</h2>
<ul>
  <li><strong>Kernel module</strong>: GPL-2.0-only</li>
  <li><strong>Userspace components</strong>: GPL-3.0-only</li>
  <li><strong>Rust crates</strong>: MIT OR Apache-2.0</li>
</ul>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="{esc(keywords)}">
<meta name="author" content="MVGAL Project">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="generator" content="MVGAL docs site generator">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE_URL}favicon.svg">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{BASE_URL}favicon.svg">
<script type="application/ld+json">{json_ld_index()}</script>
<link rel="stylesheet" href="styles.css">
{OCTICONS_CSS}
</head>
<body>
{app_header(fname)}
<div class="app-shell">
{sidebar(fname)}
<div class="content-wrap">
{repo_tabs(fname)}
<main>
{body}
"""
    html += FOOTER
    html += FOOTER_TAIL
    return html


def render_sitemap() -> str:
    urls = ['<url><loc>%sindex.html</loc></url>' % BASE_URL]
    for fname, *_ in PAGES:
        urls.append(f"<url><loc>{BASE_URL}{fname}</loc></url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


def main() -> int:
    SITE.mkdir(parents=True, exist_ok=True)
    TALLY.clear()
    for entry in PAGES:
        out = render_doc_page(*entry)
        (SITE / entry[0]).write_text(out, encoding="utf-8")

    (SITE / "index.html").write_text(render_index(), encoding="utf-8")
    (SITE / "sitemap.xml").write_text(render_sitemap(), encoding="utf-8")

    totals = {"callouts": 0, "mermaid": 0, "dataview": 0, "links": 0}
    unknown: set[str] = set()
    for fname, stats in TALLY.items():
        print(f"  {fname:<24} callouts {stats['callouts']:>3}  "
              f"mermaid {stats['mermaid']:>2}  dataview {stats['dataview']:>2}  "
              f"links {stats['links']:>3}")
        for key in totals:
            totals[key] += stats[key]
        unknown.update(stats["unknown_callout_types"])
    if unknown:
        print(f"  WARNING unstyled callout types: {', '.join(sorted(unknown))}",
              file=sys.stderr)
    print(f"  wrote {len(TALLY) + 1} pages + sitemap.xml at v{VERSION}")
    print(f"  converted {totals['callouts']} callouts, {totals['mermaid']} mermaid "
          f"diagrams, {totals['dataview']} dataview queries, "
          f"{totals['links']} links")
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())

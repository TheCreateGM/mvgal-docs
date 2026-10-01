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
from typing import NamedTuple

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

# Vendored, no CDN. Commit cec1bb7 removed the octicon/CDN dependencies and
# this stays dependency-free: mermaid ships as one UMD bundle next to styles.css.
MERMAID_JS = "mermaid.min.js"
MERMAID_VERSION = "10.9.3"
EDIT = f"https://github.com/{OWNER}/{REPO}/edit/main"


# ── Icons ────────────────────────────────────────────────────────────────────
# Hand-authored 16x16 stroke glyphs, inlined as SVG. No font, no CDN, no
# third-party path data: commit cec1bb7 dropped Primer's octicon dependency and
# this keeps it that way. Stroke-only so every glyph shares one optical weight.

ICONS = {
    "search": '<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/>',
    "rocket": '<path d="M8 1.4c2.1 1.7 3.1 4.1 3.1 6.7v2.2L9.4 11.9H6.6L4.9 10.3V8.1c0-2.6 1-5 3.1-6.7Z"/>'
              '<circle cx="8" cy="7" r="1.4"/><path d="m6.4 12.3-1.3 2.4M9.6 12.3l1.3 2.4"/>',
    "tag": '<path d="M8.5 2H14v5.5l-5.8 5.8a1 1 0 0 1-1.4 0L2 8.8a1 1 0 0 1 0-1.4Z"/>'
           '<circle cx="11" cy="5" r="1"/>',
    "check": '<path d="m3 8.5 3.2 3.2L13 5"/>',
    "check-circle": '<circle cx="8" cy="8" r="6.25"/><path d="m5 8.2 2.2 2.2L11 6.5"/>',
    "x-circle": '<circle cx="8" cy="8" r="6.25"/><path d="m6 6 4 4M10 6l-4 4"/>',
    "info": '<circle cx="8" cy="8" r="6.25"/><path d="M8 7.2v4M8 4.8h.01"/>',
    "alert": '<path d="M8 1.9 15 14H1Z"/><path d="M8 6.2v3.4M8 11.6h.01"/>',
    "question": '<circle cx="8" cy="8" r="6.25"/><path d="M6.2 6.2a1.9 1.9 0 0 1 3.6.8c0 1.3-1.8 1.8-1.8 3M8 12.2h.01"/>',
    "lightbulb": '<path d="M6.2 10.6a3.5 3.5 0 1 1 3.6 0"/>'
                 '<path d="M6.4 12.4h3.2M6.8 14h2.4"/>',
    "link": '<path d="M6.6 9.4 9.4 6.6"/>'
            '<path d="M7 4.6 8.4 3.2a2.8 2.8 0 0 1 4 4L11 10.6"/>'
            '<path d="M9 11.4 7.6 12.8a2.8 2.8 0 0 1-4-4L5 7.4"/>',
    "download": '<path d="M8 2v8"/><path d="m5 7 3 3 3-3"/>'
                '<path d="M2.5 12v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1"/>',
    "shield-lock": '<path d="M8 1.6 13.5 3.5v4.2c0 3.4-2.3 6.1-5.5 7-3.2-.9-5.5-3.6-5.5-7V3.5Z"/>'
                   '<rect x="6.1" y="7" width="3.8" height="3.2" rx=".6"/>',
    "tools": '<path d="M10.6 2.4a3.4 3.4 0 0 0 4 4l-2.3 2.3-3.4-3.4Z"/>'
             '<path d="m8.9 5.3-5.6 5.6a1.4 1.4 0 0 0 2 2l5.6-5.6"/>',
    "stack": '<rect x="2.2" y="2.6" width="11.6" height="3" rx=".7"/>'
             '<rect x="2.2" y="6.9" width="11.6" height="3" rx=".7"/>'
             '<rect x="2.2" y="11.2" width="11.6" height="3" rx=".7"/>',
    "book": '<path d="M2.6 3.1A1 1 0 0 1 3.6 2.1H13v10.8H3.6a1 1 0 0 0-1 1Z"/>'
            '<path d="M2.6 12.9a1 1 0 0 0 1 1H13"/>',
    "terminal": '<rect x="1.8" y="2.6" width="12.4" height="10.8" rx="1.4"/>'
                '<path d="m4.6 6.2 2 1.8-2 1.8M8.4 10.4h3"/>',
    "git-branch": '<circle cx="4.4" cy="3.6" r="1.8"/><circle cx="4.4" cy="12.4" r="1.8"/>'
                  '<circle cx="11.6" cy="6.2" r="1.8"/><path d="M4.4 5.4v5.2M11.6 8v1a3 3 0 0 1-3 3H6.2"/>',
    "cpu": '<rect x="4.4" y="4.4" width="7.2" height="7.2" rx="1"/>'
           '<path d="M6.6 1.8v2.6M9.4 1.8v2.6M6.6 11.6v2.6M9.4 11.6v2.6M1.8 6.6h2.6M1.8 9.4h2.6M11.6 6.6h2.6M11.6 9.4h2.6"/>',
    "zap": '<path d="M9 1.5 3.4 9.2h3.7l-.9 5.3 5.6-7.7H8.1Z"/>',
    "server": '<rect x="1.8" y="2.4" width="12.4" height="4.4" rx="1.1"/>'
              '<rect x="1.8" y="9.2" width="12.4" height="4.4" rx="1.1"/>'
              '<path d="M4.2 4.6h.01M4.2 11.4h.01"/>',
    "gamepad": '<path d="M5.4 5.6h5.2a3.4 3.4 0 0 1 3.3 2.6l.8 3a1.9 1.9 0 0 1-3.2 1.7l-1.5-1.6H5.9l-1.5 1.6a1.9 1.9 0 0 1-3.2-1.7l.8-3a3.4 3.4 0 0 1 3.4-2.6Z"/>'
               '<path d="M4.6 8.2v1.8M3.7 9.1h1.8M10 8.6h.01M11.6 10h.01"/>',
    "bug": '<ellipse cx="8" cy="8.6" rx="3.4" ry="4.4"/><path d="M8 4.2v8.8M4.6 8.6h6.8"/>'
           '<path d="M4.9 6 2.3 4.4M11.1 6l2.6-1.6M4.9 11.2l-2.6 1.6M11.1 11.2l2.6 1.6"/>',
    "pulse": '<path d="M1.6 8.6h2.7l1.5-3.9 2.2 7 1.7-4.4 1 1.3h3.7"/>',
    "checklist": '<path d="m2.2 4.4 1.4 1.4L6 3.4M7.4 4.6h6.4M2.2 10l1.4 1.4L6 9M7.4 10.2h6.4"/>',
    "folder": '<path d="M1.8 4.6a1.2 1.2 0 0 1 1.2-1.2h2.7l1.5 1.8h5.6a1.2 1.2 0 0 1 1.2 1.2v5.2a1.2 1.2 0 0 1-1.2 1.2H3a1.2 1.2 0 0 1-1.2-1.2Z"/>',
    "file-code": '<path d="M9 1.8H4.4a1.2 1.2 0 0 0-1.2 1.2v10a1.2 1.2 0 0 0 1.2 1.2h7.2a1.2 1.2 0 0 0 1.2-1.2V6Z"/>'
                 '<path d="M9 1.8V6h4.2M6.6 8.8 5 10.4l1.6 1.6M9.4 8.8 11 10.4l-1.6 1.6"/>',
    "note": '<rect x="2.6" y="2" width="10.8" height="12" rx="1.3"/>'
            '<path d="M5.2 5.6h5.6M5.2 8h5.6M5.2 10.4h3.4"/>',
    "code": '<path d="m5.4 4.6-3.4 3.4 3.4 3.4M10.6 4.6 14 8l-3.4 3.4M9.2 2.6 6.8 13.4"/>',
    "quote": '<path d="M3 10.4c0-2.6 1.2-4.3 3.4-5.2l.6 1.2c-1.3.7-2 1.6-2.1 2.6h1.9v3.4H3Z"/>'
             '<path d="M9.2 10.4c0-2.6 1.2-4.3 3.4-5.2l.6 1.2c-1.3.7-2 1.6-2.1 2.6H13v3.4H9.2Z"/>',
    "pencil": '<path d="m11.1 2.4 2.5 2.5-8 8-3.2.7.7-3.2Z"/><path d="m9.8 3.7 2.5 2.5"/>',
    "dot": '<circle cx="8" cy="8" r="3" fill="currentColor" stroke="none"/>',
}

ICON_ATTRS = ('viewBox="0 0 16 16" fill="none" stroke="currentColor" '
              'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"')


def octicon(name: str, size: int = 16, extra_class: str = "") -> str:
    """Inline one ICONS glyph. An unknown name yields '' rather than a hole."""
    body = ICONS.get(name)
    if body is None:
        return ""
    cls = f' class="octicon{(" " + extra_class) if extra_class else ""}"'
    return (f'<svg{cls} width="{size}" height="{size}" {ICON_ATTRS} '
            f'aria-hidden="true">{body}</svg>')


# ── Page catalogue: the single source of truth ───────────────────────────────
# One record per page. Nav groups, the index card grid, the search index, the
# breadcrumbs and the sitemap all read from this list, so a label, icon or
# description cannot drift between them again.

class Page(NamedTuple):
    html: str
    label: str
    title: str
    desc: str
    keywords: str
    md: str
    section: str
    icon: str
    card: str      # shorter blurb for the index grid
    lang: str
    meta: str


PAGES = [
    Page("quickstart.html", "Quick Start", "Quick Start — MVGAL Documentation",
         "Inspect an installed MVGAL build, enumerate GPUs, and check daemon status. Package availability varies by distribution.",
         "MVGAL quick start, install MVGAL, COPR install, mvgald daemon, mvgal-info, get started, Fedora RHEL CentOS",
         "QUICKSTART.md", "Getting Started", "rocket",
         "Inspect GPUs and check daemon status.", "Linux", "Diagnostics"),
    Page("install.html", "Installation", "Installation — MVGAL Documentation",
         "Review package availability or build MVGAL from source. Includes prerequisites and Secure Boot notes.",
         "MVGAL install, COPR, dnf install mvgal, Fedora RHEL CentOS, kernel module, Secure Boot, MOK, prerequisites",
         "INSTALL.md", "Getting Started", "download",
         "Check package availability or build from source.", "CMake", "2 methods"),
    Page("secure_boot.html", "Secure Boot", "Secure Boot & MOK Enrollment — MVGAL Documentation",
         "Enroll the MVGAL signing key with MOK for Secure Boot systems: mvgal-enroll-mok, manual enrollment, verification with mokutil, and troubleshooting.",
         "MVGAL Secure Boot, MOK enrollment, mvgal-enroll-mok, mokutil, DKMS signing, UEFI, kernel module signing",
         "SECURE_BOOT.md", "Getting Started", "shield-lock",
         "MOK enrollment for packages that install signed modules.", "MOK", "UEFI"),
    Page("build.html", "Building", "Building — MVGAL Documentation",
         "Build MVGAL from source with CMake, Meson or Zig on Fedora and RHEL. Prerequisites, build options, targets and packaging.",
         "MVGAL build, build from source, CMake, Meson, Zig, compile MVGAL, Fedora RHEL build, packaging RPM",
         "BUILD.md", "Getting Started", "tools",
         "Build with the repository CMake or Meson configuration.", "CMake", "Build systems"),
    Page("architecture.html", "Architecture", "Architecture — MVGAL Documentation",
         "MVGAL system architecture, kernel module, userspace runtime and API layers: kernel HAL, vendor drivers, runtime daemon, execution engine, scheduler, Rust safety crates, API interception and tooling.",
         "MVGAL architecture, kernel module, read-only GPU discovery, runtime capability probes, userspace APIs",
         "ARCHITECTURE.md", "Architecture & Design", "stack",
         "Kernel, runtime, APIs, packaging and tools.", "C/C++", "Subsystems"),
    Page("design.html", "Design", "Design — MVGAL Documentation",
         "MVGAL design goals, component boundaries, and distinctions between proposed and verified behavior.",
         "MVGAL design, architecture decisions, DRM meta-driver, C++20 daemon, Unix socket IPC, LD_PRELOAD, design goals",
         "DESIGN.md", "Architecture & Design", "book",
         "Design goals and architecture decisions.", "C++20", "Decisions"),
    Page("api.html", "API Reference", "API Reference — MVGAL Documentation",
         "Public C API reference for MVGAL: initialization, context management, execution control, scheduling strategies, stats, fences and semaphores.",
         "MVGAL C API, mvgal_init, context management, execution control, scheduling strategy, fences, semaphores, mvgal_ functions",
         "API.md", "Core Subsystems", "terminal",
         "Complete public C API reference.", "C", "Public headers"),
    Page("strategies.html", "Scheduling Strategies", "Scheduling Strategies — MVGAL Documentation",
         "Public MVGAL scheduling strategy identifiers and the current limitations on runtime dispatch.",
         "MVGAL scheduling, GPU scheduler, round-robin, least-load, bin-packing, GPU-aware, hybrid, RLD, REP, PPL, workload distribution, memory heap",
         "STRATEGIES.md", "Core Subsystems", "git-branch",
         "Scheduling strategy identifiers and availability notes.", "C", "Strategy API"),
    Page("memory.html", "Memory Management", "Memory Management — MVGAL Documentation",
         "MVGAL memory APIs and runtime capability limits for allocation, DMA-BUF, and peer transfers.",
         "MVGAL memory, unified VRAM, DMA-BUF, PCIe P2P, host-RAM staging, memory manager, NUMA, memory flags, prefetching, Rust memory safety",
         "MEMORY.md", "Core Subsystems", "cpu",
         "Memory interfaces and capability-dependent support.", "DMA-BUF", "Capabilities"),
    Page("hardware.html", "Hardware Compatibility", "Hardware Compatibility — MVGAL Documentation",
         "Recognized PCI GPU vendors, native driver ownership, and how to inspect runtime capability reports.",
         "MVGAL hardware, supported GPUs, AMD RDNA, NVIDIA Turing Ampere Ada, Intel Arc, Moore Threads MTT, driver support, kernel requirements, feature matrix",
         "HARDWARE_COMPATIBILITY.md", "Ecosystem", "server",
         "GPU discovery and runtime capability reporting.", "Vulkan", "4 vendors"),
    Page("steam.html", "Steam / Proton", "Steam / Proton — MVGAL Documentation",
         "Steam and Proton helper components, their environment variables, and capability-dependent behavior.",
         "MVGAL Steam, Proton, gaming, Vulkan layer, frame pacer, AFR, NTSYNC, DXVK, VKD3D-Proton, ENABLE_MVGAL, MVGAL_STRATEGY",
         "STEAM_INTEGRATION.md", "Ecosystem", "gamepad",
         "Steam and Proton integration components.", "Proton", "Gaming"),
    Page("power.html", "Power Management", "Power Management — MVGAL Documentation",
         "MVGAL power interfaces and capability-dependent vendor controls; unsupported operations are reported explicitly.",
         "MVGAL power management, runtime capability probing, native driver controls",
         "POWER_MANAGEMENT.md", "Core Subsystems", "zap",
         "Capability-dependent power controls.", "DVFS", "Thermal"),
    Page("troubleshooting.html", "Troubleshooting", "Troubleshooting — MVGAL Documentation",
         "Troubleshoot MVGAL: daemon not starting, Vulkan layer missing, Secure Boot / MOK failures, GPU not detected, kernel module, common fixes and diagnostics.",
         "MVGAL troubleshooting, daemon, Vulkan layer, MOK, Secure Boot, GPU not detected, kernel module, common fixes, diagnostics",
         "TROUBLESHOOTING.md", "Project", "bug",
         "Common issues and solutions.", "Linux", "Diagnostics"),
    Page("status.html", "Project Status", "Project Status — MVGAL Documentation",
         f"MVGAL source version, release provenance, and verified runtime capability boundaries.",
         f"MVGAL status, source version {VERSION}, release provenance, capability boundaries",
         "STATUS.md", "Project", "pulse",
         "Current milestone and status.", "Status", "Milestone"),
    Page("changelog.html", "Changelog", "Changelog — MVGAL Documentation",
         f"MVGAL release history and changelog: source release history through v{VERSION}, bug fixes, new features, known issues and release notes.",
         f"MVGAL changelog, release notes through v{VERSION}, version history, DKMS, Secure Boot",
         "CHANGELOG.md", "Project", "checklist",
         f"Source release history through v{VERSION}.", "Releases", "Release history"),
]

# The home page is navigation-only: it is not a PAGES entry (nothing renders it
# from a note) but it must lead the first nav section and count toward NAV_COUNT.
HOME = ("index.html", "Home", "file-code")
SECTION_ORDER = ["Getting Started", "Architecture & Design", "Core Subsystems",
                 "Ecosystem", "Project"]

NAV_SECTIONS = [
    (section,
     ([HOME] if section == SECTION_ORDER[0] else [])
     + [(p.html, p.label, p.icon) for p in PAGES if p.section == section])
    for section in SECTION_ORDER
]

NAV_LABELS = {p.html: p.label for p in PAGES}
NAV_LABELS[HOME[0]] = HOME[1]
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
NOTE_HTML = {p.md[:-3]: p.html for p in PAGES}

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

# Which glyph each callout kind wears. Types that share a severity share a
# glyph, so the icon reads as the severity ladder rather than 28 identities.
CALLOUT_ICONS = {
    "note": "note", "abstract": "info", "summary": "info", "tldr": "info",
    "info": "info", "todo": "checklist",
    "tip": "lightbulb", "hint": "lightbulb",
    "success": "check-circle", "check": "check-circle", "done": "check-circle",
    "question": "question", "help": "question", "faq": "question",
    "warning": "alert", "caution": "alert", "attention": "alert",
    "important": "alert", "missing": "alert",
    "failure": "x-circle", "fail": "x-circle", "danger": "x-circle",
    "error": "x-circle", "bug": "bug",
    "example": "code", "quote": "quote", "cite": "quote",
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
            f'<div class="callout-title"><span class="callout-icon">'
            f'{octicon(CALLOUT_ICONS.get(kind, "info"), 12)}</span>'
            f'<span class="callout-label">{escattr(title)}</span></div>'
            f'<div class="callout-body">{inner}</div>'
            f"</div>"
        )
        out.append(f"\x00CALLOUT{len(blocks) - 1}\x00")
    return "\n".join(out), blocks, unknown


# ── Post-processing of converted HTML ───────────────────────────────────────
# Markdown emits these constructs as bare block-level elements. Left alone they
# escape their container's styling and overflow the page.

# A lone placeholder line becomes "<p>SENTINEL</p>", so injecting a <div> into
# it yields "<p><div>…</div></p>": invalid nesting that browsers silently split.
BLOCK_SENTINEL = re.compile(r"<p>(\x00(?:CALLOUT|DATAVIEW)\d+\x00)</p>")
# python-markdown's tables extension emits a bare <table>; the dataview
# renderer emits <table class="dv-table"> and is already wrapped.
BARE_TABLE = re.compile(r"<table>(.*?)</table>", re.S)
HEADING = re.compile(r'<h([1-6])\s+id="([^"]+)"([^>]*)>(.*?)</h\1>', re.S)


def unwrap_placeholders(html: str) -> str:
    return BLOCK_SENTINEL.sub(r"\1", html)


def wrap_tables(html: str) -> str:
    """Give every body table a horizontal scroll container of its own."""
    return BARE_TABLE.sub(
        lambda m: f'<div class="table-wrap"><table>{m.group(1)}</table></div>', html)


def add_heading_anchors(html: str) -> str:
    """Add the hover permalink the stylesheet's .anchor-link rules expect."""
    def sub(m: re.Match) -> str:
        level, hid, attrs, inner = m.groups()
        return (f'<h{level} id="{hid}"{attrs}>{inner}'
                f'<a class="anchor-link" href="#{hid}" aria-label="Permalink to this section"></a>'
                f'</h{level}>')

    return HEADING.sub(sub, html)


def outline(tokens: list[dict], max_level: int = 3) -> str:
    """Build the right-rail "On this page" nav from the toc extension's tokens.

    The h1 is the page title and already sits above the rail, so level 1 is
    skipped. Tokens nest, so the tree is walked rather than read flat.
    """
    items: list[str] = []

    def walk(toks: list[dict]) -> None:
        for t in toks:
            if t["level"] <= max_level and t["level"] > 1:
                items.append(f'<li class="outline-item outline-l{t["level"]}">'
                             f'<a href="#{t["id"]}">{t["html"]}</a></li>')
            walk(t.get("children", []))

    walk(tokens)
    if not items:
        return ""
    return ('<div class="outline-title">On this page</div>'
            f'<ul class="outline-list">{"".join(items)}</ul>')


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
    """Load the vendored mermaid bundle, themed to match the GitHub palette.

    Mermaid bakes its theme into the SVG at render time and cannot restyle it
    afterwards, so a scheme change has to re-initialize and re-run over the
    original sources, which live in each .mermaid div's textContent.
    """
    return (
        f'<script src="{MERMAID_JS}"></script>\n'
        "<script>\n"
        "(function () {\n"
        "  if (!window.mermaid) return;\n"
        "  var P = {\n"
        "    fontFamily: getComputedStyle(document.body).fontFamily,\n"
        "    primaryColor: '#ddf4ff', primaryTextColor: '#1f2328',\n"
        "    primaryBorderColor: '#0969da', lineColor: '#656d76',\n"
        "    secondaryColor: '#f6f8fa', tertiaryColor: '#ffffff'\n"
        "  };\n"
        "  var D = {\n"
        "    fontFamily: P.fontFamily,\n"
        "    primaryColor: '#161b22', primaryTextColor: '#e6edf3',\n"
        "    primaryBorderColor: '#58a6ff', lineColor: '#8b949e',\n"
        "    secondaryColor: '#0d1117', tertiaryColor: '#1f2328'\n"
        "  };\n"
        "  var sources = Array.prototype.map.call(\n"
        "    document.querySelectorAll('.mermaid'),\n"
        "    function (el) { return el.textContent; });\n"
        "  if (!sources.length) return;\n"
        "  var nodes = document.querySelectorAll('.mermaid');\n"
        "  function draw(dark) {\n"
        "    mermaid.initialize({\n"
        "      startOnLoad: false, securityLevel: 'strict',\n"
        "      theme: 'base',\n"
        "      themeVariables: dark ? D : P,\n"
        "      flowchart: { htmlLabels: true, useMaxWidth: true }\n"
        "    });\n"
        "    // run() only renders nodes it has not already seen, so clear the\n"
        "    // marker and restore the source text before each pass.\n"
        "    for (var i = 0; i < nodes.length; i++) {\n"
        "      nodes[i].removeAttribute('data-processed');\n"
        "      nodes[i].textContent = sources[i];\n"
        "    }\n"
        "    return mermaid.run({ nodes: nodes, suppressErrors: true });\n"
        "  }\n"
        "  var mq = window.matchMedia('(prefers-color-scheme: dark)');\n"
        "  function render() { draw(mq.matches).catch(function () {}); }\n"
        "  render();\n"
        "  if (mq.addEventListener) mq.addEventListener('change', render);\n"
        "  else if (mq.addListener) mq.addListener(render);\n"
        "})();\n"
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


# A vault note's inbound links are the main way to navigate it, so the site
# shows them. Scanned once from the raw markdown rather than the rendered HTML,
# because a rendered link has already been rewritten to an .html href.
MD_TARGET = re.compile(r"\]\(([^):\s]+\.md)(?:#[^)]*)?\)")
_LINK_GRAPH: dict[str, set[str]] | None = None


def link_graph() -> dict[str, set[str]]:
    """note stem -> stems of the notes that link to it."""
    global _LINK_GRAPH
    if _LINK_GRAPH is not None:
        return _LINK_GRAPH
    graph: dict[str, set[str]] = {stem: set() for stem in NOTE_HTML}
    for page in PAGES:
        source = page.md[:-3]
        parts = CODE_REGION.split((DOCS / page.md).read_text(encoding="utf-8"))
        for i in range(0, len(parts), 2):        # odd indices are code regions
            text = parts[i]
            stems = [m.group(1).replace("\\", "").rsplit("/", 1)[-1]
                     for m in WIKILINK.finditer(text)]
            stems += [m.group(1).rsplit("/", 1)[-1][:-3]
                      for m in MD_TARGET.finditer(text)]
            for stem in stems:
                if stem in graph and stem != source:
                    graph[stem].add(source)
    _LINK_GRAPH = graph
    return graph


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
      {octicon("rocket", 16)}
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
  var searchPages = {json.dumps([{"href": p.html, "title": p.title.split(" — ")[0], "description": p.desc} for p in PAGES], ensure_ascii=False)};
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
    for p in PAGES:
        if p.html == active_page:
            md_filename = p.md
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
    links_html.append(f'  <div class="sb-title">{octicon("folder", 16)} Documentation</div>')
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


def render_markdown(md_src: str) -> tuple[str, dict, dict, list]:
    """Convert one vault note to HTML, resolving Obsidian-only constructs.

    Returns (body, stats, frontmatter, toc_tokens).
    """
    src = (DOCS / md_src).read_text(encoding="utf-8")
    meta, _ = split_frontmatter(src)
    md_text, callouts, unknown = extract_callouts(strip_frontmatter(src))
    md_text, mermaid_n = preprocess_mermaid(md_text)
    md_text, dataview = extract_dataview(md_text)
    MD.reset()
    body = MD.convert(md_text)
    toc = list(MD.toc_tokens)
    # Sentinels are still bare at this point; drop the <p> the converter wrapped
    # them in before the blocks are swapped back in.
    body = unwrap_placeholders(body)
    body = inject_blocks(body, callouts, "CALLOUT")
    body = inject_blocks(body, dataview, "DATAVIEW")
    body = wrap_tables(body)
    body = add_heading_anchors(body)
    body, links = resolve_links(body)
    return body, {
        "callouts": len(callouts),
        "unknown_callout_types": unknown,
        "mermaid": mermaid_n,
        "dataview": len(dataview),
        "links": links,
    }, meta, toc


def render_doc_page(page: Page) -> str:
    fname, title, desc, keywords, md_src = page.html, page.title, page.desc, page.keywords, page.md
    body, stats, meta, toc = render_markdown(md_src)
    TALLY.setdefault(fname, stats)
    url = BASE_URL + fname
    chips = page_chips(meta)
    tags = tag_pills(meta)
    rail = outline(toc)
    backlinks = backlinks_panel(page.md)
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
  <div class="page-header-main">
    {chips}
    {tags}
  </div>
  {page_header_actions(fname)}
</div>
<div class="doc-layout">
<div class="doc-body">
{body}
{backlinks}
</div>
<aside class="doc-rail">
{rail}
<div class="rail-actions">
  <a class="rail-link" href="{EDIT}/{md_src}" target="_blank" rel="noopener">{octicon("pencil", 12)} Edit this page</a>
  <a class="rail-link" href="{BLOB}/{md_src}" target="_blank" rel="noopener">{octicon("code", 12)} View source</a>
</div>
</aside>
</div>
"""
    html += FOOTER
    html += mermaid_script() if TALLY[fname]["mermaid"] else ""
    html += FOOTER_TAIL
    return html



def page_chips(meta: dict) -> str:
    """Vault frontmatter surfaced as read-only property chips."""
    fields = (("tag", "mvgal_version", "v{v}" if meta.get("mvgal_version") else ""),
              ("check", "mvgal_verified", "{v}"),
              ("book", "mvgal_role", "{v}"))
    chips = []
    for icon, key, fmt in fields:
        value = meta.get(key)
        if not value:
            continue
        text = fmt.format(v=esc(str(value)))
        chips.append(
            f'<span class="page-chip"><span class="chip-icon">'
            f'{octicon(icon, 12)}</span>{text}</span>'
        )
    return f'<div class="page-chips">{"".join(chips)}</div>' if chips else ""


def tag_pills(meta: dict) -> str:
    """Frontmatter tags as pills, minus the vault-wide `mvgal` tag."""
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = _scalar(tags)
    tags = [t for t in tags if t and t != "mvgal"]
    if not tags:
        return ""
    pills = "".join(f'<a class="tag-pill" href="#">{octicon("tag", 10)}{esc(str(t))}</a>' for t in tags)
    return f'<div class="page-tags">{pills}</div>'


def backlinks_panel(md_src: str) -> str:
    """Incoming links, i.e. the notes that reference this one."""
    incoming = sorted(link_graph().get(md_src[:-3], ()))
    if not incoming:
        return ""
    items = "".join(
        f'<li><a href="{NOTE_HTML[stem]}">{esc(NAV_LABELS.get(NOTE_HTML[stem], stem))}</a></li>'
        for stem in incoming
    )
    return (
        '<section class="backlinks">\n'
        f'<div class="backlinks-title">{octicon("link", 14)} Linked mentions</div>\n'
        f'<ul class="backlinks-list">{items}</ul>\n'
        '</section>'
    )


def render_index() -> str:
    title = "MVGAL — Multi-Vendor GPU Aggregation Layer for Linux"
    desc = "MVGAL explores cross-vendor GPU discovery and application integration on Linux. Runtime capabilities are probed; unsupported submission and allocation paths fail explicitly."
    keywords = "MVGAL, Linux GPU discovery, kernel module, userspace runtime, Vulkan, OpenCL, CUDA, runtime capabilities"
    url = BASE_URL + "index.html"
    fname = "index.html"

    card_html = "\n".join(
        f'''<a class="card" href="{p.html}">
  <div class="card-header">
    {octicon(p.icon, 16, "card-icon")}
    <h3>{esc(p.label)}</h3>
  </div>
  <p>{esc(p.card)}</p>
  <div class="card-meta">
    <span class="meta-item"><span class="lang-dot"></span>{esc(p.lang)}</span>
    <span class="meta-item">
      {octicon("dot", 12)}
      {esc(p.meta)}
    </span>
  </div>
</a>'''
        for p in PAGES
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
<p>MVGAL explores cross-vendor GPU discovery, runtime interfaces, scheduling, and application integration. The kernel module discovers devices without binding them away from native drivers. As of {VERSION}, unsupported kernel submission and VRAM allocation fail with <code>-EOPNOTSUPP</code>, and the Vulkan ICD does not advertise a synthetic aggregate physical device. Verify each API path and probed capability on the target system.</p>
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
    for p in PAGES:
        urls.append(f"<url><loc>{BASE_URL}{p.html}</loc></url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


def main() -> int:
    SITE.mkdir(parents=True, exist_ok=True)
    TALLY.clear()
    for p in PAGES:
        out = render_doc_page(p)
        (SITE / p.html).write_text(out, encoding="utf-8")

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

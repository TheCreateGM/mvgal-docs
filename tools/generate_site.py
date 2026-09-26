#!/usr/bin/env python3
"""MVGAL docs site generator.

Reads the Obsidian vault markdown docs (docs/*.md) and renders the static
HTML site (site/*.html) with a consistent sidebar, meta tags and footer.

Usage:
    python3 tools/generate_site.py
"""

import json
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = ROOT / "site"

VERSION = "0.7.8"
BASE_URL = "https://thecreategm.github.io/mvgal-docs/site/"
SITE_NAME = "MVGAL Documentation"
ABOUT = "Multi-Vendor GPU Aggregation Layer for Linux"
PUBLISHED = "2026-08-31"
MODIFIED = "2026-09-24"
OWNER = "TheCreateGM"
REPO = "mvgal-docs"

OCTICONS_CSS = ""

PAGES = [
    ("quickstart.html", "Quick Start", "Quick Start — MVGAL Documentation",
     "Get MVGAL running in 5 minutes: install from COPR, start the daemon, verify your GPUs, and use it with applications on Fedora, RHEL and CentOS Stream.",
     "MVGAL quick start, install MVGAL, COPR install, mvgald daemon, mvgal-info, get started, Fedora RHEL CentOS",
     "QUICKSTART.md"),
    ("install.html", "Installation", "Installation — MVGAL Documentation",
     "Install MVGAL from COPR on Fedora, RHEL, AlmaLinux, CentOS Stream and openSUSE. Prerequisites, kernel module, Secure Boot and post-install setup.",
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
     "The 8-layer MVGAL system architecture: kernel HAL, vendor drivers, runtime daemon, execution engine, scheduler, Rust safety crates, API interception and tooling.",
     "MVGAL architecture, 8-layer, kernel module, mvgald daemon, Vulkan layer, OpenCL ICD, CUDA shim, DRM meta-driver, vendor ops",
     "ARCHITECTURE.md"),
    ("design.html", "Design", "Design — MVGAL Documentation",
     "MVGAL design goals and architecture decisions: DRM meta-driver, C++20 daemon with Unix socket IPC, LD_PRELOAD interception and transparent multi-GPU aggregation.",
     "MVGAL design, architecture decisions, DRM meta-driver, C++20 daemon, Unix socket IPC, LD_PRELOAD, design goals",
     "DESIGN.md"),
    ("api.html", "API Reference", "API Reference — MVGAL Documentation",
     "Complete public C API reference for MVGAL: initialization, context management, execution control, scheduling strategies, stats, fences and semaphores.",
     "MVGAL API, C API reference, mvgal_init, context management, execution control, scheduling strategy, fences, semaphores, mvgal_ functions",
     "API.md"),
    ("strategies.html", "Scheduling Strategies", "Scheduling Strategies — MVGAL Documentation",
     "The 10 MVGAL scheduling strategies: Round-Robin, Least-Load, Priority, Affinity, Bin-Packing, GPU-Aware, Hybrid, RLD, REP and PPL, plus the memory heap hierarchy.",
     "MVGAL scheduling, GPU scheduler, round-robin, least-load, bin-packing, GPU-aware, hybrid, RLD, REP, PPL, workload distribution, memory heap",
     "STRATEGIES.md"),
    ("memory.html", "Memory Management", "Memory Management — MVGAL Documentation",
     "MVGAL unified memory manager: DMA-BUF zero-copy, PCIe P2P transfer, host-RAM staging, memory flags, mirroring, prefetching and the Rust memory-safety layer.",
     "MVGAL memory, unified VRAM, DMA-BUF, PCIe P2P, host-RAM staging, memory manager, NUMA, memory flags, prefetching, Rust memory safety",
     "MEMORY.md"),
    ("hardware.html", "Hardware Compatibility", "Hardware Compatibility — MVGAL Documentation",
     "Supported MVGAL GPUs and drivers: AMD RDNA/GCN, NVIDIA Turing/Ampere/Ada, Intel Gen/Xe/Arc and Moore Threads MTT. Feature matrix and kernel requirements.",
     "MVGAL hardware, supported GPUs, AMD RDNA, NVIDIA Turing Ampere Ada, Intel Arc, Moore Threads MTT, driver support, kernel requirements, feature matrix",
     "HARDWARE_COMPATIBILITY.md"),
    ("steam.html", "Steam / Proton", "Steam / Proton — MVGAL Documentation",
     "Use MVGAL with Steam and Proton for multi-GPU gaming: Vulkan layer, frame pacer, alternate frame rendering, NTSYNC and environment variables.",
     "MVGAL Steam, Proton, gaming, Vulkan layer, frame pacer, AFR, NTSYNC, DXVK, VKD3D-Proton, ENABLE_MVGAL, MVGAL_STRATEGY",
     "STEAM_INTEGRATION.md"),
    ("power.html", "Power Management", "Power Management — MVGAL Documentation",
     "MVGAL power management: power curve system, idle state machine, DVFS, gamemode integration, thermal throttling and the mvgal-powercurve tool.",
     "MVGAL power, power management, DVFS, idle states, GPU parking, thermal throttling, gamemode, power curve, mvgal-powercurve",
     "POWER_MANAGEMENT.md"),
    ("troubleshooting.html", "Troubleshooting", "Troubleshooting — MVGAL Documentation",
     "Troubleshoot MVGAL: daemon not starting, Vulkan layer missing, Secure Boot / MOK failures, GPU not detected, kernel module, common fixes and diagnostics.",
     "MVGAL troubleshooting, daemon, Vulkan layer, MOK, Secure Boot, GPU not detected, kernel module, common fixes, diagnostics",
     "TROUBLESHOOTING.md"),
    ("status.html", "Project Status", "Project Status — MVGAL Documentation",
     "Current MVGAL v0.7.8 milestone status, roadmap, feature completion tracker, supported interfaces and upcoming releases.",
     "MVGAL status, project status, roadmap, v0.7.8, milestone, feature tracker, release planning",
     "STATUS.md"),
    ("changelog.html", "Changelog", "Changelog — MVGAL Documentation",
     "MVGAL release history and changelog: all changes between v0.7.4 and v0.7.8, bug fixes, new features, known issues and release notes.",
     "MVGAL changelog, release notes, v0.7.8, v0.7.7, v0.7.6, v0.7.5, v0.7.4, version history, DKMS, Secure Boot",
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


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return text


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
        "description": "MVGAL aggregates multiple GPUs from different vendors (AMD, NVIDIA, Intel, Moore Threads) into one logical device on Linux. Vulkan layer, OpenCL ICD, CUDA shim, unified memory and scheduling.",
        "url": BASE_URL + "index.html",
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE_URL + "index.html"},
        "publisher": {"@type": "Organization", "name": "MVGAL",
                      "logo": {"@type": "ImageObject", "url": BASE_URL + "favicon.svg"}},
        "about": ABOUT,
        "keywords": "MVGAL, multi-GPU, GPU aggregation, heterogeneous GPU, Vulkan layer, OpenCL ICD, CUDA shim, Linux GPU, AMD NVIDIA Intel, unified memory, GPU scheduler",
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
  <div class="search-hint" role="search" aria-label="Search documentation">
    {octicon("search", 16)}
    <span>Search or jump to...</span>
    <kbd>/</kbd>
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

  var search = document.querySelector('.search-hint');
  if (search) {{
    search.addEventListener('click', function() {{
      showToast('Tip: Use the sidebar or type a page URL to navigate', 'info');
    }});
  }}
  document.addEventListener('keydown', function(e) {{
    var inInput = e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
    if (e.key === '/' && !inInput) {{
      e.preventDefault();
      if (search) search.classList.add('hover');
      showToast('Press any page title in the sidebar to jump', 'info');
      setTimeout(function() {{ if (search) search.classList.remove('hover'); }}, 800);
    }}
  }});

  var toggle = document.querySelector('.menu-toggle');
  var sidebar = document.querySelector('nav.sidebar');
  if (toggle && sidebar) {{
    toggle.addEventListener('click', function(){{
      var open = sidebar.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }});
    sidebar.querySelectorAll('a').forEach(function(a){{
      a.addEventListener('click', function(){{
        sidebar.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
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
</body>
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


def render_doc_page(fname: str, label: str, title: str, desc: str, keywords: str, md_src: str) -> str:
    md_text = strip_frontmatter((DOCS / md_src).read_text(encoding="utf-8"))
    MD.reset()
    body = MD.convert(md_text)
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
    return html


def render_index() -> str:
    title = "MVGAL — Multi-Vendor GPU Aggregation Layer for Linux"
    desc = "MVGAL aggregates multiple GPUs from different vendors (AMD, NVIDIA, Intel, Moore Threads) into one logical device on Linux. Vulkan layer, OpenCL ICD, CUDA shim, unified memory and scheduling."
    keywords = "MVGAL, multi-GPU, GPU aggregation, heterogeneous GPU, Vulkan layer, OpenCL ICD, CUDA shim, Linux GPU, AMD NVIDIA Intel, unified memory, GPU scheduler"
    url = BASE_URL + "index.html"
    fname = "index.html"

    cards_spec = [
        ("quickstart.html", "Quick Start", "Get MVGAL running in 5 minutes.", "rocket", "C++", "3 steps"),
        ("install.html", "Installation", "Install from COPR or build from source.", "download", "CMake", "2 methods"),
        ("secure_boot.html", "Secure Boot", "Enroll the MOK key for signed modules.", "shield-lock", "MOK", "UEFI"),
        ("build.html", "Building", "Build with CMake, Meson, or Zig.", "tools", "Meson", "3 build sys"),
        ("architecture.html", "Architecture", "The 8-layer system architecture.", "stack", "Rust", "8 layers"),
        ("design.html", "Design", "Design goals and architecture decisions.", "book", "C++20", "Decisions"),
        ("api.html", "API Reference", "Complete public C API reference.", "terminal", "C", "26 headers"),
        ("strategies.html", "Scheduling Strategies", "10 workload distribution strategies.", "git-branch", "Rust", "10 strategies"),
        ("memory.html", "Memory Management", "Unified VRAM, DMA-BUF, P2P.", "cpu", "DMA-BUF", "4 heaps"),
        ("hardware.html", "Hardware Compatibility", "Supported GPUs and drivers.", "server", "Vulkan", "4 vendors"),
        ("steam.html", "Steam / Proton", "Multi-GPU gaming integration.", "gamepad-2", "Proton", "Gaming"),
        ("power.html", "Power Management", "DVFS, idle states, thermal control.", "zap", "DVFS", "Thermal"),
        ("troubleshooting.html", "Troubleshooting", "Common issues and solutions.", "bug", "Linux", "Diagnostics"),
        ("status.html", "Project Status", "Current milestone and status.", "pulse", "Status", "Milestone"),
        ("changelog.html", "Changelog", "Release history v0.7.4 to v0.7.8.", "checklist", "Releases", "5 versions"),
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
  <p>Combine multiple GPUs from different vendors into one logical device — transparently, without modifying your applications.</p>
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
<p>MVGAL solves this by aggregating all available GPUs — regardless of vendor — into a single logical device. Any application, game, or compute workload can use it without modification.</p>
<h2>Quick Start</h2>
<pre><code># Start the daemon
pkexec systemctl start mvgald
pkexec systemctl enable mvgald   # start on boot

# Verify
mvgal-info          # list detected GPUs
mvgal-status        # real-time utilization
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
    count = 0
    for entry in PAGES:
        fname = entry[0]
        out = render_doc_page(*entry)
        (SITE / fname).write_text(out, encoding="utf-8")
        count += 1
        print(f"  wrote {fname}")

    idx = render_index()
    (SITE / "index.html").write_text(idx, encoding="utf-8")
    count += 1
    print(f"  wrote index.html")

    sm = render_sitemap()
    (SITE / "sitemap.xml").write_text(sm, encoding="utf-8")
    print(f"  wrote sitemap.xml")
    print(f"Done. {count} pages at v{VERSION}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

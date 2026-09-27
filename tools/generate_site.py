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

VERSION = "0.7.13"
BASE_URL = "https://thecreategm.github.io/mvgal-docs/site/"
SITE_NAME = "MVGAL Documentation"
ABOUT = "Multi-Vendor GPU Aggregation Layer for Linux"
PUBLISHED = "2026-08-31"
MODIFIED = "2026-09-27"
OWNER = "TheCreateGM"
REPO = "mvgal-docs"

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
     "MVGAL status, source version 0.7.13, release provenance, capability boundaries",
     "STATUS.md"),
    ("changelog.html", "Changelog", "Changelog — MVGAL Documentation",
     "MVGAL release history and changelog: source release history through v0.7.12, bug fixes, new features, known issues and release notes.",
     "MVGAL changelog, release notes through v0.7.12, version history, DKMS, Secure Boot",
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
<p>MVGAL explores cross-vendor GPU discovery, runtime interfaces, scheduling, and application integration. The kernel module discovers devices without binding them away from native drivers. As of 0.7.12, unsupported kernel submission and VRAM allocation fail with <code>-EOPNOTSUPP</code>, and the Vulkan ICD does not advertise a synthetic aggregate physical device. Verify each API path and probed capability on the target system.</p>
<h2>Quick Start</h2>
<pre><code># Start the daemon
pkexec systemctl start mvgald
pkexec systemctl enable mvgald   # start on boot

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

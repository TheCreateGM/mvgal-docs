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

# (filename, nav label, title, description, keywords, md source)
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
     "Diagnose and fix common MVGAL issues: installation, GPU not detected, kernel module, performance, Steam/Proton, daemon and multi-GPU problems.",
     "MVGAL troubleshooting, fix, GPU not detected, kernel module, performance, daemon not starting, multi-GPU, diagnostics, log collection",
     "TROUBLESHOOTING.md"),
    ("status.html", "Project Status", "Project Status — MVGAL Documentation",
     "Current MVGAL milestone and component status: kernel modules, daemon, Vulkan layer, OpenCL ICD, CUDA shim, memory manager, scheduler and packaging.",
     "MVGAL status, milestone, component status, roadmap, kernel modules, daemon, Vulkan layer, OpenCL ICD, CUDA shim, packaging",
     "STATUS.md"),
    ("changelog.html", "Changelog", "Changelog — MVGAL Documentation",
     "MVGAL release history: all notable changes from v0.7.4 through v0.7.8, including DKMS fixes, Secure Boot support, Vulkan ICD fixes and security hardening.",
     "MVGAL changelog, release notes, v0.7.8, v0.7.7, v0.7.6, v0.7.5, v0.7.4, version history, DKMS, Secure Boot",
     "CHANGELOG.md"),
]

NAV_LABELS = {f: label for f, label, *_ in PAGES}

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


def head_block(title: str, desc: str, keywords: str, url: str, ld: str, og_type: str = "article") -> str:
    return f"""<!DOCTYPE html>
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
<!-- Open Graph -->
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE_URL}favicon.svg">
<meta property="og:locale" content="en_US">
<!-- Twitter Card -->
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{BASE_URL}favicon.svg">
<script type="application/ld+json">{ld}</script>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<button class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false">&#9776;</button>
<script>
(function(){{
  var toggle = document.querySelector('.menu-toggle');
  var sidebar = document.querySelector('nav.sidebar');
  if (!toggle || !sidebar) return;
  toggle.addEventListener('click', function(){{
    var open = sidebar.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }});
  // Close menu when a nav link is clicked (mobile)
  sidebar.querySelectorAll('a').forEach(function(a){{
    a.addEventListener('click', function(){{
      sidebar.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }});
  }});
}})();
</script>
"""


def sidebar(active: str) -> str:
    home_cls = ' class="active"' if active == "index.html" else ""
    links = [f'<a href="index.html"{home_cls}>Home</a>']
    for fname, label, *_ in PAGES:
        cls = ' class="active"' if fname == active else ""
        links.append(f'<a href="{fname}"{cls}>{label}</a>')
    return f"""<nav class="sidebar">
  <div class="brand">
    <div class="logo">MVGAL</div>
    <div class="sub">Multi-Vendor GPU Aggregation Layer · v{VERSION}</div>
  </div>
{chr(10).join(links)}
</nav>
"""


FOOTER = f"""<footer>MVGAL — Multi-Vendor GPU Aggregation Layer for Linux · v{VERSION} · GPL-2.0 (kernel) / GPL-3.0 (userspace) / MIT OR Apache-2.0 (Rust)</footer>
</main>
</body>
</html>
"""


def render_doc_page(fname: str, label: str, title: str, desc: str, keywords: str, md_src: str) -> str:
    md_text = strip_frontmatter((DOCS / md_src).read_text(encoding="utf-8"))
    MD.reset()
    body = MD.convert(md_text)
    url = BASE_URL + fname
    html = head_block(title, desc, keywords, url, json_ld_doc(title, desc, url, keywords))
    html += sidebar(fname)
    html += "<main>\n" + body + "\n" + FOOTER
    return html


def render_index() -> str:
    title = "MVGAL — Multi-Vendor GPU Aggregation Layer for Linux"
    desc = "MVGAL aggregates multiple GPUs from different vendors (AMD, NVIDIA, Intel, Moore Threads) into one logical device on Linux. Vulkan layer, OpenCL ICD, CUDA shim, unified memory and scheduling."
    keywords = "MVGAL, multi-GPU, GPU aggregation, heterogeneous GPU, Vulkan layer, OpenCL ICD, CUDA shim, Linux GPU, AMD NVIDIA Intel, unified memory, GPU scheduler"
    url = BASE_URL + "index.html"
    html = head_block(title, desc, keywords, url, json_ld_index(), og_type="website")
    html += sidebar("index.html")

    cards = [
        ("quickstart.html", "Quick Start", "Get MVGAL running in 5 minutes."),
        ("install.html", "Installation", "Install from COPR or build from source."),
        ("secure_boot.html", "Secure Boot", "Enroll the MOK key for signed modules."),
        ("build.html", "Building", "Build MVGAL from source with CMake, Meson, or Zig."),
        ("architecture.html", "Architecture", "The 8-layer system architecture."),
        ("design.html", "Design", "Design goals and architecture decisions."),
        ("api.html", "API Reference", "Complete public C API reference."),
        ("strategies.html", "Scheduling Strategies", "10 workload distribution strategies."),
        ("memory.html", "Memory Management", "Unified VRAM, DMA-BUF, P2P, and staging."),
        ("hardware.html", "Hardware Compatibility", "Supported GPUs and drivers."),
        ("steam.html", "Steam / Proton", "Multi-GPU gaming integration."),
        ("power.html", "Power Management", "DVFS, idle states, thermal control."),
        ("troubleshooting.html", "Troubleshooting", "Common issues and solutions."),
        ("status.html", "Project Status", "Current milestone and component status."),
        ("changelog.html", "Changelog", "Release history from v0.7.4 to v0.7.8."),
    ]
    card_html = "\n".join(
        f'<a class="card" href="{f}"><h3>{t}</h3><p>{d}</p></a>' for f, t, d in cards
    )

    body = f"""<main>

<div class="hero">
  <h1>MVGAL — Multi-Vendor GPU Aggregation Layer</h1>
  <p>Combine multiple GPUs from different vendors into one logical device — transparently, without modifying your applications.</p>
  <p style="margin-top:12px">
    <span class="badge">v{VERSION}</span>
    <span class="badge">AMD · NVIDIA · Intel · Moore Threads</span>
    <span class="badge">Vulkan · OpenCL · CUDA</span>
  </p>
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
    html += body + FOOTER
    return html


def render_sitemap() -> str:
    urls = ['<url><loc>%sindex.html</loc></url>' % BASE_URL]
    for fname, *_ in PAGES:
        urls.append(f"<url><loc>{BASE_URL}{fname}</loc></url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"  {u}" for u in urls)
        + "\n</urlset>\n"
    )


def main() -> None:
    SITE.mkdir(exist_ok=True)
    for fname, label, title, desc, keywords, md_src in PAGES:
        html = render_doc_page(fname, label, title, desc, keywords, md_src)
        (SITE / fname).write_text(html, encoding="utf-8")
        print(f"  wrote {fname}")
    (SITE / "index.html").write_text(render_index(), encoding="utf-8")
    print("  wrote index.html")
    (SITE / "sitemap.xml").write_text(render_sitemap(), encoding="utf-8")
    print("  wrote sitemap.xml")
    print(f"Done. {len(PAGES) + 1} pages at v{VERSION}.")


if __name__ == "__main__":
    sys.exit(main())
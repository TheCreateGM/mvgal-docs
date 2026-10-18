---
tags: [mvgal, docs, index]
aliases: [Home, Index]
mvgal_version: "0.7.24"
mvgal_verified: 2026-10-18
mvgal_role: index
---

# MVGAL Documentation

Documentation for **MVGAL**, an experimental Linux project for multi-vendor GPU discovery, capability reporting, workload coordination and API-specific integrations.

> These pages describe source version **0.7.24**. The project is not a universal transparent multi-GPU driver. Device ownership stays with native vendor drivers, and actual operation support depends on build options and runtime capability probes.

## Read the documentation

- [HTML site](https://thecreategm.github.io/mvgal-docs/site/index.html)
- [Quick Start](docs/QUICKSTART.md) · [Installation](docs/INSTALL.md) · [Build Guide](docs/BUILD.md)
- [Architecture](docs/ARCHITECTURE.md) · [Codebase Map](docs/CODEBASE.md) · [Design](docs/DESIGN.md)
- [API Reference](docs/API.md) · [Scheduling](docs/STRATEGIES.md) · [Memory](docs/MEMORY.md)
- [Hardware Compatibility](docs/HARDWARE_COMPATIBILITY.md) · [Steam / Proton](docs/STEAM_INTEGRATION.md) · [Power](docs/POWER_MANAGEMENT.md)
- [Project Status](docs/STATUS.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Changelog](docs/CHANGELOG.md) · [Secure Boot](docs/SECURE_BOOT.md)

The source repository is organized around a Linux kernel module (`kernel/`), public interfaces (`include/mvgal/`), userspace APIs and integrations (`src/userspace/`), the C++ daemon (`runtime/daemon/`), Rust components (`safe/` and `runtime/safe/`), tools, bindings, compatibility helpers and package recipes. See the [Codebase Map](docs/CODEBASE.md) for details.

## Current implementation limits

- MVGAL does not bind GPU PCI functions; native vendor drivers continue to own submission and memory management.
- API symbols, strategy names, vendor adapters and ioctl declarations do not establish that an operation works on a given device.
- Unsupported operations must be treated as unsupported; use runtime capability reporting and the documented fallback for each path.
- The Vulkan interception layer and optional ICD are separate. The ICD does not publish a fabricated aggregate physical device.
- Synthetic GPU topologies are a userspace test fixture; they do not create hardware or establish physical multi-vendor validation.
- The latest source changelog notes that one PCI enumeration fix still needs a clean-boot hardware check on the affected system.

## Package artifacts

The [`package/`](package/README.md) directory contains version 0.7.24 RPM, DEB, AppImage and tarball artifacts. Consult its README and the artifact metadata for exact contents and verification details. Files in this repository do not update automatically, and their presence does not imply remote publication or hardware validation.

## Updating the HTML site

The static site is generated from `docs/*.md`:

```sh
python3 tools/generate_site.py
```

The generator derives the displayed version from frontmatter in this file or `MOC.md`, and its reviewed date from documentation frontmatter.

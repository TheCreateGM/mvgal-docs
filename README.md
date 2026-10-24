---
tags: [mvgal, docs, index]
aliases: [Home, Index]
mvgal_version: "0.7.26"
mvgal_verified: 2026-10-24
mvgal_role: index
---

# MVGAL Documentation

Documentation for **MVGAL**, an experimental Linux project for multi-vendor GPU discovery, capability reporting, workload coordination and API-specific integrations.

> These pages describe source version **0.7.26**. The project is not a universal transparent multi-GPU driver. Device ownership stays with native vendor drivers, and actual operation support depends on build options and runtime capability probes.

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

## Recent source changes (through v0.7.26)

- **A built `mvgal-workload` could not be packaged** (v0.7.26) — CMake builds the tool whenever it finds OpenCL, but the RPM files list made its inclusion conditional, so a Fedora build that found OpenCL failed in `%install` with `Installed (but unpackaged) file(s) found: /usr/bin/mvgal-workload`. The files list now always includes what the build produces. The same release fixed the AppImage dependency self-check (the `ldd` walk now resolves `not found` entries and the final check runs against the staged `usr/lib`) and normalized the application icons to 256×256, which the Flatpak, RPM and AppImage exports require.

- **The modules could not be decompressed, so enrolling the MOK could not make them load** (v0.7.25) — they were compressed with `xz -9e`, producing a CRC64 xz stream, and the kernel's xz decoder rejects any check type above CRC32 (`lib/xz/xz_dec_stream.c`; it only carries an internal CRC32). The module failed at decompression with `Invalid parameters`, *before* the Secure Boot signature was checked, so the documented recovery — enroll, reboot, confirm — still left the system broken. CRC64 is xz's default check at every level, so `xz -9` was equally broken. v0.7.25 uses the kernel's own settings (`xz --check=crc32 --lzma2=dict=1MiB`), byte-identical to what DKMS builds. The signer also repairs modules that were already signed correctly but compressed wrongly, and `mvgal-enroll-mok` now re-signs before queueing the certificate.
- **`systemctl reload mvgald` failed permanently** (v0.7.25) — the daemon chowned systemd's `RuntimeDirectory=/run/mvgal` to `root:mvgal`, and systemd requires `root:root`, so every reload after the first start failed with `status=233/RUNTIME_DIRECTORY` while `restart` kept working. Separately, SIGHUP was installed but the handler had no case for it, so a reload did nothing and still reported success. Both are fixed: the daemon leaves the directory alone and now re-reads the configuration on SIGHUP.
- **The D-Bus API refused every non-root call** (v0.7.25) — the methods were registered without `SD_BUS_VTABLE_UNPRIVILEGED`, so sd-bus applied its own default policy and rejected them with `AccessDenied` regardless of the bus policy that allows the `mvgal` group. The GUI and dashboard were dead for members of that group.
- **"Vulkan aggregated ICD: ACTIVE" was a false positive** (v0.7.25) — the staging copy in the opt-in directory was treated as a registration. The ICD now reports registered / available / absent, and never says ACTIVE for the staging copy.
- **The OpenCL ICD registration was frozen at install time** (v0.7.25) — the decision was made from a snapshot of the machine, so on a host where the vendor runtime was installed after MVGAL the manifest stayed parked and every OpenCL application ran without MVGAL in the path. The decision moved to `/usr/lib/mvgal/mvgal-opencl-icd.sh`, which can be re-run, and the manifest is registered by default.
- **The tools stopped describing a system that was not in the state they claimed** (v0.7.25) — module load failures are classified instead of always being blamed on Secure Boot; a multi-GPU strategy is refused on a one-GPU machine; shared system RAM is no longer presented as dedicated VRAM; `mvgal-compat` and `mvgal-dashboard --check` have meaningful exit codes; `mvgal-steam-setup --check` reports the real runtime state; `mvgal-config show-config` shows the effective configuration; and `journalctl -u mvgald` works again because the canonical unit name is used.

## Package artifacts

The [`package/`](package/README.md) directory contains version 0.7.26 RPM, DEB, AppImage, tarball and Flatpak artifacts. Consult its README and the artifact metadata for exact contents and verification details. Files in this repository do not update automatically, and their presence does not imply remote publication or hardware validation.

## Updating the HTML site

The static site is generated from `docs/*.md`:

```sh
python3 tools/generate_site.py
```

The generator derives the displayed version from frontmatter in this file or `MOC.md`, and its reviewed date from documentation frontmatter.

---
tags: [mvgal, status, reference]
aliases: [Project Status, Status]
mvgal_version: "0.7.25"
mvgal_verified: 2026-10-22
mvgal_role: reference
mvgal_order: 5
---

# MVGAL Project Status

## Source version

The source repository reports **0.7.25** in its CMake and Cargo workspace metadata. The source changelog has entries through **0.7.25**. This documentation snapshot was reconciled against that source on 2026-10-22. Package publication and physical hardware validation are separate questions; a successful build or installed artifact does not establish runtime support.

## What the code provides

The source includes a Linux DRM-facing kernel module, GPU discovery and capability reporting, a userspace library/API, the `mvgald` runtime daemon, several API integration targets, management/diagnostic tools, Rust safety crates, language bindings, UI sources, tests and distribution packaging definitions. Exact components depend on build options, dependency discovery and package selection.

v0.7.25 is a packaging and reporting release. Its headline defect made the
modules unloadable and the documented Secure Boot recovery unable to
repair them: the modules were compressed with `xz -9e`, producing a
CRC64 xz stream that the kernel's decoder rejects (it accepts CRC32 and
below), so the module failed at *decompression* — before the signature
was examined. A user who enrolled the MOK correctly still had a system
that would not load MVGAL, and the journal pointed at a signature problem
that was not the cause. CRC64 is xz's default check at every compression
level, so `xz -9` was equally broken. v0.7.25 uses the kernel's own
settings from `scripts/Makefile.modinst`
(`xz --check=crc32 --lzma2=dict=1MiB`), which is also byte-identical to
what DKMS builds.

Two related gaps were closed with it: the daemon had chowned systemd's
`RuntimeDirectory`, which made every `systemctl reload mvgald` fail with
`status=233` while `restart` kept working; and SIGHUP was installed but
the handler had no case for it, so a reload did nothing and reported
success. The remainder of the release is reporting: the Vulkan probe
called a staged manifest "ACTIVE", the D-Bus methods were registered
without `SD_BUS_VTABLE_UNPRIVILEGED` (so sd-bus refused every non-root
call and left the GUI and dashboard dead for members of the `mvgal`
group), the OpenCL ICD registration was frozen at install time, and a
multi-GPU strategy was accepted on a single-GPU host. See
[Changelog](CHANGELOG.md) § v0.7.25.

The 0.7.23–0.7.24 releases mainly fixed correctness and observability issues found by packaging and exercising the installed system. The latest audit fixed daemon device access and D-Bus name ownership checks; PCIe generation, NUMA and class-code reporting; sysfs setup and kernel work/reference lifecycle defects; GPU memory totals; and inert power-control paths. It added `mvgal-workload`, an end-to-end OpenCL workload gate requiring at least two distinct vendors. See [Changelog](CHANGELOG.md) for the full source-derived details.

## Runtime boundaries

- The kernel module is above-driver discovery/control scaffolding. It does not take ownership of GPU PCI functions; native vendor drivers remain in charge of GPU submission and their memory managers.
- Capabilities are intended to come from runtime probes. Unsupported kernel submission and VRAM allocation are not made functional by ioctl declarations or adapter files; callers must honor explicit unsupported results and fallbacks.
- The Vulkan layer and Vulkan ICD are distinct components. The ICD does not provide a fabricated physical device representing multiple vendors.
- API interception, strategy identifiers and memory APIs do not prove safe work distribution. Correctness depends on workload/API semantics, available backend operations and probed capabilities.
- DMA-BUF/P2P paths depend on the device pair and driver support. Host staging is the fallback where supported by the particular userspace path.
- Moore Threads and Adreno adapters and Windows/Steam compatibility code are experimental integration surfaces. Treat each as unvalidated until the exact hardware, driver and workload path has been exercised.

## Build and validation

CMake is the primary broad build; Meson and Cargo cover separate portions. Optional dependencies and build switches determine which targets exist. Unit/integration tests, synthetic topology, successful package builds and physical multi-vendor validation provide different evidence and should be reported separately. The synthetic topology backend is a test fixture and does not create devices.

The latest source changelog records a PCI enumeration reference-lifetime issue that still needs a clean-boot hardware check on the affected host. Do not turn this source-level fix into a claim of completed physical validation.

## Package state

This docs repository's `package/` directory contains **0.7.25** RPM, DEB, AppImage and tarball artifacts as of this update. Its package README and individual manifests should be consulted for exact contents. Presence here does not establish that a remote repository has published the same version or that the artifacts have passed hardware validation.

## Further reading

- [Architecture](ARCHITECTURE.md) and [Codebase Map](CODEBASE.md)
- [Hardware Compatibility](HARDWARE_COMPATIBILITY.md)
- [Build Guide](BUILD.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Source changelog mirror](CHANGELOG.md)

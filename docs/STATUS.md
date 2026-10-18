---
tags: [mvgal, status, reference]
aliases: [Project Status, Status]
mvgal_version: "0.7.24"
mvgal_verified: 2026-10-18
mvgal_role: reference
mvgal_order: 5
---

# MVGAL Project Status

## Source version

The source repository reports **0.7.24** in its CMake and Cargo workspace metadata. The source changelog has entries through **0.7.24**. This documentation snapshot was reconciled against that source on 2026-10-18. Package publication and physical hardware validation are separate questions; a successful build or installed artifact does not establish runtime support.

## What the code provides

The source includes a Linux DRM-facing kernel module, GPU discovery and capability reporting, a userspace library/API, the `mvgald` runtime daemon, several API integration targets, management/diagnostic tools, Rust safety crates, language bindings, UI sources, tests and distribution packaging definitions. Exact components depend on build options, dependency discovery and package selection.

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

This docs repository's `package/` directory contains **0.7.24** RPM, DEB, AppImage and tarball artifacts as of this update. Its package README and individual manifests should be consulted for exact contents. Presence here does not establish that a remote repository has published the same version or that the artifacts have passed hardware validation.

## Further reading

- [Architecture](ARCHITECTURE.md) and [Codebase Map](CODEBASE.md)
- [Hardware Compatibility](HARDWARE_COMPATIBILITY.md)
- [Build Guide](BUILD.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Source changelog mirror](CHANGELOG.md)

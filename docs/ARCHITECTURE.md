---
tags: [mvgal, architecture, reference]
aliases: [Architecture]
mvgal_version: "0.7.22"
mvgal_verified: 2026-10-14
mvgal_role: reference
mvgal_order: 6
---

# MVGAL Architecture

> Source metadata is **0.7.22**; the source changelog documents releases through **0.7.22**. This page follows the current source tree. Earlier design documents describe ambitions that are not all implemented.

## Repository components

| Component | Source location | Responsibility |
|-----------|-----------------|----------------|
| Kernel module | `kernel/` | Character device/UAPI, GPU discovery, vendor adapters, capability probes, synchronization and sysfs reporting |
| Public interfaces | `include/mvgal/` | C API and kernel/userspace data structures |
| Userspace library and API components | `src/userspace/` | API, scheduler, memory and execution code, Vulkan/OpenCL/CUDA components, daemon-related code |
| Runtime daemon | `runtime/daemon/`, `src/userspace/daemon/` | Device registry, IPC, metrics, config, scheduling, memory, and power managers |
| Safety crates | `safe/`, `runtime/safe/` | Rust fence, memory-safety, and capability-model components |
| Tools | `tools/` | `mvgal`, `mvgal-info`, `mvgal-status`, `mvgal-bench`, `mvgal-compat`, `mvgal-config`, `mvgal-enum`, `mvgal-hw-validate`, `mvgal-steam-setup`, and probe components |
| Integrations | `steam/`, `compat/`, `opengl/`, `bindings/` | Compatibility helpers, API interception, and language bindings |
| UI | `ui/`, `dashboard/` | Optional Qt and Haxe UI components |
| Tests and synthetic topology | `src/tests/`, `src/userspace/testing/` | Unit suite, and the synthetic GPU topology backend that substitutes for hardware during rescan so hetero-GPU paths can be exercised deterministically |

## Device ownership and capabilities

The kernel module discovers GPUs through the PCI subsystem and does not register as their PCI driver. The native vendor driver remains responsible for command submission and memory management. MVGAL records capabilities from runtime probes rather than assuming that a vendor adapter can perform an operation.

The 0.7.12 source changelog explicitly says kernel submission, kernel VRAM allocation, DMA-BUF export, and wait-idle are not advertised as supported. Unsupported operations return `-EOPNOTSUPP`; they must not be interpreted as successful no-ops. The Vulkan ICD does not advertise a fabricated aggregate physical device.

## Control and diagnostic flow

```mermaid
flowchart LR
    CLI[CLI and applications] --> US[Userspace APIs and runtime]
    US --> IPC[IPC / device UAPI]
    IPC --> K[MVGAL kernel module]
    K --> PCI[Read-only GPU discovery]
    PCI --> N[Native vendor driver remains owner]
    US --> Probe[Runtime capability probes]
    Probe --> Decision[Supported operations or explicit unsupported result]
```

Use `mvgal --help`, `mvgal-info --help`, and `mvgal-config --help` to inspect commands actually provided by an installed build. Whether an API component was compiled is controlled by build options and dependencies; whether an operation works depends on runtime capabilities.

## CLI output contract

The tools are meant to be parsed, so the split is enforced:

- **stdout** carries only the requested output — a GPU list, `--json`, a table.
  Nothing else. Informational logging goes to stderr.
- **SIGPIPE is ignored** by every tool, so `mvgal ... | head` exits 0 instead of
  dying on signal 13 (shell status 141).

Both were fixed in v0.7.22. The stdout rule previously leaked: the library's
pre-initialisation fallback in `log_internal()` sent INFO and above to stdout,
and the tools that printed `Configuration loaded from ...` were exactly the ones
that never call `mvgal_log_init()`. Note for contributors — routing
`get_default_output()` to stderr is **not** sufficient on its own, because that
function is never reached on that path.

### What `mvgal-bench` actually measures

`mvgal-bench` does not measure GPU performance. It reports:

- **memory bandwidth** — read/write/copy of `mmap`'d **host RAM**
- **compute** — a single-threaded **host CPU** DAXPY

Every figure is now labelled with that hardware path, and the run header states
it explicitly when `/dev/mvgal0` is absent. `--metadata` carries the same
provenance as machine-readable fields:

```json
{ "hardware_path": "host_cpu", "mvgal_device_present": false, "measures_gpu": false }
```

`measures_gpu` is a constant `false` today and is present so a consumer can tell
host figures from GPU figures without inferring it from the tool name (v0.7.22).

## Build configuration

The top-level CMake project defines optional build groups for the kernel module, runtime, API, gaming integration, tools, Rust components, tests, and UI. Vulkan, OpenCL, and other API components may be omitted when dependencies are unavailable. See [BUILD.md](BUILD.md) and the source `CMakeLists.txt` for the exact configuration.

## Related references

- [Status](STATUS.md) summarizes verified implementation boundaries.
- [API](API.md) lists public interfaces; declarations do not guarantee operational backend support.
- [Hardware compatibility](HARDWARE_COMPATIBILITY.md) explains discovery and capability reporting.
- The source repository `CHANGELOG.md` records implementation changes and audit findings.

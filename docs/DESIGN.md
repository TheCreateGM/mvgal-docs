# MVGAL Design Document

**Version:** 0.7.3 | **Last Updated:** August 2026

---

## Design Goals

1. **Transparent multi-vendor GPU aggregation** — applications see one logical GPU regardless of how many physical GPUs exist.
2. **Zero application changes** — interception via Vulkan layer, OpenCL ICD, CUDA shim, and LD_PRELOAD.
3. **Vendor-agnostic scheduling** — AMD, NVIDIA, Intel, and Moore Threads GPUs work together.
4. **Safety-first** — kernel module with DRM registration, Rust safety crates for critical paths.
5. **Low overhead** — target <2% frame time regression for single-GPU pass-through mode.

---

## Architecture Decisions

### Decision 1: Kernel Module as DRM Meta-Driver

**Chosen approach:** A Linux kernel module (`mvgal.ko`) that registers as a DRM client and exposes `/dev/mvgal0` with 10 DRM ioctls.

**Alternatives considered:**
- **Userspace-only daemon:** Simpler to develop, no kernel patching required. Rejected because DMA-BUF zero-copy and cross-device synchronization require kernel-level buffer management.
- **Upstream DRM proposal:** Would integrate natively with the DRM subsystem. Deferred because upstream review cycle is 6-12 months and vendor driver compatibility is uncertain.
- **eBPF-based approach:** Modern, safe, no module loading. Rejected because eBPF programs cannot manage GPU memory or synchronize across vendors at the required latency.

**Tradeoffs:**
- (+) Full control over buffer management and scheduling
- (+) DMA-BUF import/export across vendors
- (-) Requires module signing and MOK enrollment for Secure Boot
- (-) Must track kernel API changes across releases

### Decision 2: C++20 Daemon with IPC over Unix Socket

**Chosen approach:** `mvgald` is a C++20 daemon communicating with clients via Unix socket (`/run/mvgal/mvgal.sock`) using a binary protocol with MVGL magic header and SCM_CREDENTIALS authentication.

**Alternatives considered:**
- **D-Bus as primary IPC:** Simpler, well-supported. Rejected because D-Bus adds ~50μs per message round-trip; GPU workload submission needs sub-10μs latency.
- **Shared memory ring buffer:** Lowest latency. Rejected because it requires mmap setup per client and complicates authentication.
- **gRPC/Protobuf:** Cross-language, schema-defined. Rejected because it adds ~100KB binary dependency and serialization overhead.

**Tradeoffs:**
- (+) Low latency (~2-5μs per IPC call)
- (+) Native Unix credential verification
- (-) Custom binary protocol requires versioning discipline
- (-) No automatic cross-language binding generation

### Decision 3: LD_PRELOAD Interception for All APIs

**Chosen approach:** Transparent interception via Vulkan implicit layer, OpenCL ICD wrapper, CUDA function hooking (40+ functions), and LD_PRELOAD for OpenGL/D3D/Metal/WebGPU.

**Alternatives considered:**
- **Library wrapping (link-time):** Compile against MVGAL lib instead of vendor lib. Rejected because it requires recompilation and breaks binary compatibility.
- **ptrace-based interception:** No library modification needed. Rejected because ptrace has severe performance penalties and breaks anti-cheat.
- **Binary patching:** Modify vendor libraries in-place. Rejected because it violates vendor licenses and breaks with updates.

**Tradeoffs:**
- (+) Zero application changes
- (+) Works with any binary (Steam games, AI frameworks)
- (-) Environment variable setup required per-launch
- (-) Anti-cheat software may flag LD_PRELOAD

### Decision 4: DMA-BUF Zero-Copy with Host-RAM Fallback

**Chosen approach:** Three-tier memory transfer: (1) DMA-BUF zero-copy between GPUs sharing the same IOMMU group, (2) PCIe P2P for GPUs on the same root complex, (3) host-RAM staging as universal fallback.

**Alternatives considered:**
- **CUDA peer-to-peer only:** Works for NVIDIA+NVIDIA. Rejected because MVGAL must handle AMD+NVIDIA+Intel combinations.
- **ROCm hipMemcpyPeer:** AMD-specific. Rejected for the same reason.
- **Always host-staged:** Simplest implementation. Rejected because it adds 2-5ms latency per cross-GPU transfer for large buffers.

**Tradeoffs:**
- (+) Best-case performance with zero-copy
- (+) Universal fallback ensures correctness
- (-) Complex fallback logic with three code paths
- (-) DMA-BUF support varies by driver version

### Decision 5: Rust for Safety-Critical Subsystems

**Chosen approach:** Three Rust crates (`fence_manager`, `memory_safety`, `capability_model`) with C FFI exports for use by the C++ daemon.

**Alternatives considered:**
- **All C++ with RAII:** Would keep the codebase single-language. Rejected because Rust's ownership model eliminates entire classes of bugs (use-after-free, data races) that are critical in GPU synchronization code.
- **All Rust:** Would maximize safety. Rejected because the kernel module must be C (Linux requirement) and the existing IPC/scheduler code is mature C++.
- **Valgrind/ASan in CI:** Runtime detection. Rejected as insufficient alone — static analysis via Rust borrow checker is strictly better for prevention.

**Tradeoffs:**
- (+) Memory safety without garbage collection
- (+) Compile-time enforcement of concurrency safety
- (-) FFI boundary adds complexity
- (-) Two build systems (Cargo + CMake)

### Decision 6: 9 Scheduling Strategies

**Chosen approach:** Nine built-in strategies: Single, Auto, Round-robin, AFR, SFR, Task, Compute offload, Hybrid, Custom. Auto-detect selects the best strategy based on workload type.

**Alternatives considered:**
- **Fixed single strategy:** Simplest. Rejected because different workloads benefit from different strategies (AFR for gaming, compute offload for AI).
- **User-configured only:** No auto-detect. Rejected because most users won't know which strategy is best.
- **ML-based adaptive:** Uses the AI scheduling mode. Deferred because it requires training data and adds model loading overhead.

**Tradeoffs:**
- (+) Covers all common use cases
- (+) Auto-detect reduces user configuration burden
- (-) 9 strategies increase code surface area
- (-) Auto-detect heuristics may be wrong for edge cases

---

## Data Flow

```
Application
    │
    ▼
Interception Layer (Vulkan/CL/CUDA/GL)
    │ serialize workload descriptor
    ▼
IPC Client ──── Unix Socket ────▶ IPC Server (mvgald)
                                       │
                                       ▼
                                  Scheduler
                                  ├─ Select GPU(s) based on strategy
                                  ├─ Check memory availability
                                  └─ Assign priority
                                       │
                                       ▼
                                  Memory Manager
                                  ├─ Allocate VRAM on target GPU(s)
                                  ├─ Import/export DMA-BUF
                                  └─ Fallback to host-RAM if needed
                                       │
                                       ▼
                                  Kernel Module (/dev/mvgal0)
                                  ├─ DRM ioctl submission
                                  ├─ Vendor-specific dispatch (VGDD)
                                  └─ Fence signaling
                                       │
                                       ▼
                                  GPU Hardware
```

---

## Security Model

- **Socket permissions:** `/run/mvgal/mvgal.sock` is mode `0660` (root:root)
- **IPC authentication:** SCM_CREDENTIALS on Unix socket; only root or video group members can connect
- **Kernel module:** Signed at install time; MOK enrollment for Secure Boot
- **Device nodes:** `/dev/mvgal*` owned by root:video, mode 0660
- **pkexec:** All privileged operations use pkexec, never sudo in scripts
- **No firmware flashing:** Vendor-overriding firmware operations are explicitly excluded

---

## Performance Characteristics

| Path | Latency | Notes |
|------|---------|-------|
| Single-GPU pass-through | <2% overhead | No cross-GPU transfer needed |
| DMA-BUF zero-copy | ~5-10μs | Kernel-level buffer mapping |
| PCIe P2P transfer | ~50-200μs | Depends on buffer size and PCIe gen |
| Host-RAM staging | ~2-5ms | CPU copy bottleneck |
| IPC round-trip | ~2-5μs | Unix socket with binary protocol |
| Scheduler decision | ~1-10μs | Priority queue with 16 levels |

---

## Limitations and Known Issues

1. **No direct upstream kernel integration** — the module must be built and signed per-kernel.
2. **Anti-cheat compatibility** — LD_PRELOAD interception may be flagged by kernel-level anti-cheat (EAC, BattlEye).
3. **Network GPU pooling** — remote GPU support is implemented but not yet production-ready.
4. **AI scheduling** — the ML-based scheduler requires training data and is not yet deployed.
5. **Collective communication** — the AllReduce/AllGather/Broadcast library is a stub; no UCX/UCC integration.

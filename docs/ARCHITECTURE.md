# MVGAL Architecture

**Version:** 0.7.0 | **Last Updated:** August 2026

---

## Overview

MVGAL (Multi-Vendor GPU Aggregation Layer for Linux) is an **eight-layer** system that presents two or more heterogeneous GPUs from different vendors as a single logical device to all applications without requiring application changes.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Applications                              │
│          (Games, Blender, PyTorch, OpenCL programs)              │
├──────────────────────────────────────────────────────────────────┤
│                Layer 8: Tooling & Bindings                        │
│  CLI (mvgal-info/status/bench) · Qt Dashboard · REST API ·      │
│  Steam Frame Pacer · Language Bindings (Java, C#, D, Nim, V,    │
│  Crystal, Haxe)                                                  │
├──────────────────────────────────────────────────────────────────┤
│                Layer 7: API Interception                          │
│  VK_LAYER_MVGAL · libmvgal_opencl.so · libmvgal_cuda.so ·       │
│  libmvgal_gl.so (OpenGL LD_PRELOAD) · D3D9/11/12 shims ·        │
│  Metal shim · WebGPU shim · SPIR-V Routing                       │
├──────────────────────────────────────────────────────────────────┤
│                Layer 6: Safety Subsystems (Rust)                  │
│  fence_manager · memory_safety · capability_model                │
│  Memory-safe FFI boundary between C/C++ and Rust                 │
├──────────────────────────────────────────────────────────────────┤
│          Layer 5: Work Distribution Engine (WDE)                  │
│  7+3 Scheduling Strategies · Memory Heap Hierarchy               │
│  (Heaps 0-4) · Workload Analysis → Strategy Selection            │
│  RLD (Render Layer Dist.) · REP (Replication) · PPL (Pipeline)   │
├──────────────────────────────────────────────────────────────────┤
│          Layer 4: Intermediate Framing Layer (IMFL)               │
│  Frame Sessions · Cross-GPU Migration Plans · Steam Profiles   │
│  Execution Context Lifecycle · Migration Path Selection           │
├──────────────────────────────────────────────────────────────────┤
│                Layer 3: Runtime Daemon (mvgald)                   │
│  Scheduler · MemoryManager · PowerManager · MetricsCollector ·   │
│  IpcServer · DeviceRegistry · D-Bus API · Daemon State Machine   │
├──────────────────────────────────────────────────────────────────┤
│          Layer 2: Vendor GPU Driver Dispatch (VGDD)               │
│  struct mvgal_vendor_ops · amdgpu / nvidia / intel / mtt        │
│  Per-vendor command submission · VRAM alloc · power mgmt         │
│  DMA-BUF export/import · PCIe P2P · Utilization query            │
├──────────────────────────────────────────────────────────────────┤
│          Layer 1: Hardware Abstraction Layer (HAL)                │
│  mvgal.ko (char dev → DRM migration path) · PCI enumeration ·   │
│  GPU topology · IOCTL interface · NTSYNC · Cross-GPU DMA-BUF    │
│  /dev/mvgal0 · sysfs interface                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│   │ amdgpu.ko│  │nvidia.ko │  │i915/xe.ko│  │mtgpu-drv │       │
│   │  (AMD)   │  │ (NVIDIA) │  │ (Intel)  │  │  (MTT)   │       │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                    Vendor Kernel Drivers                          │
└──────────────────────────────────────────────────────────────────┘
```

### Layer Summary

| Layer | Name | Abbr. | Source | Language |
|-------|------|-------|--------|----------|
| 1 | Hardware Abstraction Layer | HAL | `kernel/` | C (GPL-2.0) |
| 2 | Vendor GPU Driver Dispatch | VGDD | `kernel/vendors/` | C (GPL-2.0) |
| 3 | Runtime Daemon | Runtime | `runtime/daemon/` | C++20 |
| 4 | Intermediate Framing Layer | IMFL | `src/userspace/execution/` | C17 |
| 5 | Work Distribution Engine | WDE | `src/userspace/scheduler/` | C17 |
| 6 | Safety Subsystems | Safety | `safe/` | Rust |
| 7 | API Interception | Intercept | `src/userspace/intercept/` + `opengl/` | C17 |
| 8 | Tooling & Bindings | Tooling | `tools/` + `steam/` + `ui/` + `bindings/` | C17, Go, Qt |

### Interface Contracts

| Boundary | Mechanism | Protocol/Format |
|----------|-----------|-----------------|
| HAL → VGDD | Function pointer table | `struct mvgal_vendor_ops` |
| HAL → Runtime | IOCTL | `mvgal_uapi.h` (10 ioctls) |
| VGDD → Vendor kdbs | Linux kernel API | DRM, DMA-BUF, PCI subsystem |
| Runtime → IMFL/WDE | Unix socket IPC | MVGAL IPC binary protocol |
| IMFL → WDE | Internal function calls | `execution_plan.h` / `scheduler.h` |
| Runtime → Safety | C FFI (`extern "C"`) | `mvgal_fence_*`, `mvgal_mem_*`, `mvgal_cap_*` |
| Intercept → IMFL | C function calls | `mvgal_execution_*` API |
| Tooling → Runtime | IPC (socket) or REST | MVGAL IPC or HTTP `:7474` |

---

## Layer 1 — Hardware Abstraction Layer (HAL)

**Source:** `kernel/` (9 source files)  
**License:** GPL-2.0-only  
**Device node:** `/dev/mvgal0` (char dev, Phase 1) → future DRM driver (Phase 2)

### Responsibilities

- Registers a character device `/dev/mvgal0` via `alloc_chrdev_region` and `cdev_add`.
- Enumerates all display-class PCI devices at module load and on hotplug events.
- Exposes GPU topology, PCIe link information, and BAR sizes to user space via ioctls.
- Manages cross-GPU DMA-BUF export/import and unified virtual address space.
- Implements kernel-side workload queue with 16 priority levels.
- Provides cross-vendor fence and timeline synchronization primitives.
- NTSYNC kernel module for Windows-compatible sync primitives (WoW64).

### Module Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_debug` | bool | false | Enable verbose kernel log output |
| `max_devices` | uint | 8 | Maximum number of GPUs supported |

### IOCTL Interface

Defined in `include/mvgal/mvgal_uapi.h`:

| IOCTL | Direction | Description |
|-------|-----------|-------------|
| `MVGAL_IOCTL_QUERY_DEVICES` | Read | Number and descriptors of detected GPUs |
| `MVGAL_IOCTL_QUERY_CAPABILITIES` | Read | Aggregate capability profile |
| `MVGAL_IOCTL_SUBMIT_WORKLOAD` | Write | Submit a workload to the scheduler |
| `MVGAL_IOCTL_ALLOC_MEMORY` | Read/Write | Allocate unified virtual memory |
| `MVGAL_IOCTL_FREE_MEMORY` | Write | Free a unified memory allocation |
| `MVGAL_IOCTL_IMPORT_DMABUF` | Write | Import a DMA-BUF file descriptor |
| `MVGAL_IOCTL_EXPORT_DMABUF` | Read | Export a buffer as DMA-BUF |
| `MVGAL_IOCTL_WAIT_FENCE` | Write | Wait for a fence to be signaled |
| `MVGAL_IOCTL_SIGNAL_FENCE` | Write | Signal a fence |
| `MVGAL_IOCTL_SET_GPU_AFFINITY` | Write | Pin a context to specific GPUs |

### Kernel Source Files

| File | Purpose |
|------|---------|
| `mvgal_main.c` | Module init/exit, PCI scan, char dev registration |
| `mvgal_ioctl.c` | IOCTL dispatch table (10 handlers) |
| `mvgal_dma_buf.c` | Cross-GPU DMA-BUF export/import implementation |
| `mvgal_fence.c` | Fence and timeline sync primitives |
| `mvgal_memory.c` | Kernel-side memory management (GEM/buffer objects) |
| `mvgal_sched.c` | Kernel-side workload queue (16 priority levels) |
| `mvgal_sysfs.c` | Sysfs interface for GPU metrics |
| `mvgal_ntsync.c` | NTSYNC Windows-compatible sync primitives |
| `mvgal_p2p.c` | PCIe P2P DMA setup and teardown |

### Char Dev → DRM Driver Migration Path

The current HAL uses a character device (`/dev/mvgal0`) for Phase 1. A full DRM driver is planned:

| Phase | Approach | Status |
|-------|----------|--------|
| Phase 1 (current) | `alloc_chrdev_region` + `cdev_add` | ✅ Implemented |
| Phase 2 | `drm_driver` registration as minor DRM subsystem | 🔄 Planned |
| Phase 2 goals | DRM sync object support, DRM scheduler integration, GEM object lifecycle, `drm_gem_prime_export/import` | 🔄 Planned |
| Rationale | Char dev avoids claiming PCI devices from vendor drivers; DRM path enables native compositor integration | — |

Migration does **not** replace vendor DRM drivers (`amdgpu.ko`, `nvidia.ko`, etc.). MVGAL remains an above-driver coordinator.

---

## Layer 2 — Vendor GPU Driver Dispatch (VGDD)

**Source:** `kernel/vendors/`  
**License:** GPL-2.0-only

### Responsibilities

Each vendor implements the same `struct mvgal_vendor_ops` interface to abstract away vendor-specific GPU driver interactions.

### Vendor Operations

```c
struct mvgal_vendor_ops {
    int  (*init)(struct mvgal_gpu_device *dev);
    void (*fini)(struct mvgal_gpu_device *dev);
    int  (*submit_cs)(struct mvgal_gpu_device *dev, struct mvgal_workload *wl);
    int  (*alloc_vram)(struct mvgal_gpu_device *dev, size_t size, uint64_t *addr);
    void (*free_vram)(struct mvgal_gpu_device *dev, uint64_t addr);
    int  (*wait_idle)(struct mvgal_gpu_device *dev, uint32_t timeout_ms);
    int  (*set_power_state)(struct mvgal_gpu_device *dev, enum mvgal_power_state);
    struct dma_buf *(*export_dmabuf)(struct mvgal_gpu_device *dev, uint64_t addr, size_t size);
    int  (*import_dmabuf)(struct mvgal_gpu_device *dev, struct dma_buf *buf, uint64_t *addr);
    int  (*query_utilization)(struct mvgal_gpu_device *dev, uint32_t *util_percent);
};
```

### Vendor Implementations

| File | Vendor | Driver Interfaces |
|------|--------|-------------------|
| `mvgal_amd.c` | AMD | `amdgpu.ko` via DRM prime + sysfs |
| `mvgal_nvidia.c` | NVIDIA | `nvidia.ko` / `nvidia-open.ko` via procfs + DMA-BUF |
| `mvgal_intel.c` | Intel | `i915.ko` / `xe.ko` via DRM prime |
| `mvgal_mtt.c` | Moore Threads | `mtgpu-drv.ko` via vendor API (experimental) |

### Design Decisions

**No `pci_register_driver`:** MVGAL must not claim PCI devices away from vendor drivers. Using `pci_get_device` in a scan loop allows MVGAL to observe all GPUs without interfering with their existing drivers.

**Vendor ops as function pointers:** Allows compile-time selection of supported vendors and clean degradation when a vendor module is absent.

---

## Layer 3 — Runtime Daemon (mvgald)

**Source:** `runtime/daemon/` (C++20)  
**Socket:** `/run/mvgal/mvgal.sock`  
**PID file:** `/run/mvgal/mvgald.pid`  
**D-Bus:** `org.mvgal.daemon`

### Responsibilities

Central coordination point for all MVGAL operations. Runs as a systemd service, manages GPU state, handles client IPC, and exposes telemetry.

### Subsystems

#### DeviceRegistry (`device_registry.cpp`)

Enumerates GPUs via `/sys/class/drm/cardN/device/` and PCI bus scan. Normalizes vendor-specific metadata into `GpuDevice` objects with:

- PCI slot, vendor/device IDs, DRM node path
- Capabilities: VRAM size/free, bandwidth, compute units, API flags, PCIe gen/lanes, NUMA node
- State: utilization %, memory %, temperature, power draw, clock speed, power state

#### Scheduler (`scheduler.cpp`)

Three scheduling modes:

- `STATIC_PARTITIONING` — divide workload by static weights
- `DYNAMIC_LOAD_BALANCING` — route to GPU with most available capacity
- `APPLICATION_PROFILE` — pre-configured profiles for known applications

Priority queue with 16 levels. Work-stealing when one GPU's queue depth exceeds threshold.

#### MemoryManager (`memory_manager.cpp`)

Coordinates cross-GPU memory allocation. Tracks allocations per GPU, implements DMA-BUF transfer path, PCIe P2P fallback, and host-RAM staging.

#### PowerManager (`power_manager.cpp`)

Power state machine:

```
ACTIVE → SUSTAINED → IDLE → PARK
```

Configurable timeouts:

- `idleTimeoutMs` (default: 5000 ms) — time without workload before going idle
- `sustainedTimeoutMs` (default: 30000 ms) — time in idle before sustained
- `parkTimeoutMs` (default: 60000 ms) — time in sustained before parking

DVFS: adjusts GPU clock based on utilization. Thermal throttling at configurable threshold (default: 85°C).

#### MetricsCollector (`metrics_collector.cpp`)

Polls sysfs at configurable interval (default: 1000 ms). Collects:

- GPU utilization, memory utilization, memory bandwidth (read/write)
- Temperature, power draw, clock speed, queue depth
- Submit latency, execution time, wait time

Exposes telemetry subscription API for clients.

#### IpcServer (`ipc_server.cpp`)

Unix domain socket server. Binary message format:

```
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  magic   │ version  │  type    │ reqId    │ payloadSz│  flags   │ reserved │
│ 'MVGL'   │    1     │ uint32   │ uint32   │ uint32   │ uint32   │ uint32   │
│ 4 bytes  │ 4 bytes  │ 4 bytes  │ 4 bytes  │ 4 bytes  │ 4 bytes  │ 4 bytes  │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

Message types: `HELLO`, `GOODBYE`, `QUERY_DEVICES`, `QUERY_DEVICE_CAPABILITIES`, `QUERY_UNIFIED_CAPABILITIES`, `ALLOC_MEMORY`, `FREE_MEMORY`, `IMPORT_DMABUF`, `EXPORT_DMABUF`, `SUBMIT_WORKLOAD`, `WAIT_WORKLOAD`, `SET_SCHEDULING_MODE`, `SET_GPU_PRIORITY`, `SET_GPU_ENABLED`, `GET_STATISTICS`, `SUBSCRIBE_TELEMETRY`, `UNSUBSCRIBE_TELEMETRY`, `GET_CONFIG`, `SET_CONFIG`, `LOAD_CONFIG`, `SAVE_CONFIG`, `ERROR`.

Authentication: `SCM_CREDENTIALS` — only `video` group members or root may submit workloads.

#### D-Bus API (`org.mvgal.daemon`)

| Interface | Method | Description |
|-----------|--------|-------------|
| `org.mvgal.GPUManager` | `ListGPUs` | Returns array of GPU device paths |
| `org.mvgal.GPUManager` | `GetGPUStats(path)` | Returns utilization, temp, power |
| `org.mvgal.Scheduler` | `GetStrategy` | Returns current scheduling strategy |
| `org.mvgal.Scheduler` | `SetStrategy(string)` | Sets scheduling strategy |
| `org.mvgal.Scheduler` | `GetGPUPriorities` | Returns per-GPU priority levels |
| `org.mvgal.Power` | `GetPowerState(path)` | Returns current power state of a GPU |
| `org.mvgal.Power` | `SetPowerState(path, string)` | Manually set power state |
| `org.mvgal.Config` | `GetConfig` | Returns full daemon configuration |
| `org.mvgal.Config` | `SetConfig(string, variant)` | Set a configuration value |

---

## Layer 4 — Intermediate Framing Layer (IMFL)

**Source:** `src/userspace/execution/` (C17)  
**Header:** `include/mvgal/execution.h`

### Responsibilities

Translates intercepted API calls into scheduler workloads. Manages frame sessions (begin → submit → present lifecycle), generates cross-GPU migration plans, and produces Steam/Proton scheduling profiles.

### Execution Context Lifecycle

```
mvgal_execution_begin_frame()   → allocates frame_id, records API/strategy/app
mvgal_execution_submit()        → creates execution plan, selects GPUs, chooses migration path
mvgal_execution_present()       → finalizes frame, triggers frame pacer if needed
mvgal_execution_get_frame_stats() → returns timing, GPU list, bytes migrated
```

### Migration Path Selection

```
1. DMA-BUF zero-copy   (MVGAL_EXECUTION_MIGRATION_STREAM)
2. PCIe P2P            (MVGAL_EXECUTION_MIGRATION_STREAM with P2P)
3. Host-RAM staging    (MVGAL_EXECUTION_MIGRATION_EVICT)
4. Mirror/replicate    (MVGAL_EXECUTION_MIGRATION_MIRROR)
```

### Frame Session Data

| Field | Type | Description |
|-------|------|-------------|
| `frame_id` | `uint64_t` | Monotonically increasing frame identifier |
| `api` | `enum mvgal_api` | Originating API (Vulkan, OpenCL, CUDA, etc.) |
| `strategy` | `enum mvgal_strategy` | Scheduling strategy assigned to this frame |
| `gpu_mask` | `uint32_t` | Bitmask of GPUs selected for this frame |
| `migration_path` | `enum mvgal_migration` | Selected migration path (stream/P2P/evict/mirror) |
| `bytes_migrated` | `uint64_t` | Total bytes transferred for this frame |
| `start_ns` | `uint64_t` | Frame start timestamp (CLOCK_MONOTONIC) |
| `end_ns` | `uint64_t` | Frame end timestamp |

---

## Layer 5 — Work Distribution Engine (WDE)

**Source:** `src/userspace/scheduler/` + `src/userspace/memory/` (C17)  
**Headers:** `include/mvgal/scheduler.h`, `include/mvgal/memory.h`

### Responsibilities

Selects the optimal work distribution strategy per workload, manages memory allocation across the GPU memory hierarchy, and implements 10 scheduling strategies (7 existing + 3 new).

### Scheduling Strategies

#### Existing Strategies (7)

| Strategy | Enum | Description |
|----------|------|-------------|
| Round-robin | `MVGAL_STRATEGY_ROUND_ROBIN` | Even distribution across all GPUs |
| AFR | `MVGAL_STRATEGY_AFR` | Even frames → GPU 0, odd frames → GPU 1 |
| SFR | `MVGAL_STRATEGY_SFR` | Screen split horizontally or vertically |
| Task-based | `MVGAL_STRATEGY_TASK` | Route by workload type (graphics vs compute) |
| Compute offload | `MVGAL_STRATEGY_COMPUTE_OFFLOAD` | Route compute to highest-FLOPS GPU |
| Hybrid | `MVGAL_STRATEGY_HYBRID` | Adaptive — selects best strategy per workload |
| Single GPU | `MVGAL_STRATEGY_SINGLE_GPU` | Use only the primary GPU |

#### New Strategies (3)

| Strategy | Abbr. | Enum | Description |
|----------|-------|------|-------------|
| Render Layer Distribution | RLD | `MVGAL_STRATEGY_RLD` | Distribute render layers (e.g., UI, world, post-fx) across different GPUs based on layer affinity. Best for complex scenes with separable rendering passes. |
| Replication Mode | REP | `MVGAL_STRATEGY_REPLICATION` | Replicate identical work across GPUs for comparison/redundancy. Useful for scientific computing validation and fault-tolerant rendering. |
| Pipeline Parallelism | PPL | `MVGAL_STRATEGY_PIPELINE_PARALLELISM` | Split a pipeline across GPUs (GPU 0 → pre-process, GPU N → post-process). Best for streaming workloads and media encoding pipelines. |

#### Strategy Selection Criteria

| Workload Type | Recommended Strategy | Rationale |
|--------------|---------------------|-----------|
| Gaming (fast-paced) | AFR, SFR | Minimizes frame latency, even GPU utilization |
| Gaming (complex scenes) | RLD | Separates rendering layers across GPUs |
| AI Training | Compute offload, PPL | Maximizes throughput via batch sharding |
| AI Inference | Round-robin, Task-based | Even load distribution |
| Media encoding | PPL | Pipeline stages across GPUs |
| Scientific computing | REP | Cross-verification of results |
| Mixed workloads | Hybrid | Adaptive strategy selection |

### Memory Heap Hierarchy (Heaps 0–4)

The WDE manages memory across a 5-tier heap hierarchy, each with distinct performance/latency characteristics:

| Heap | Name | Location | Access Latency | Capacity | Best For |
|------|------|----------|---------------|----------|----------|
| Heap 0 | GPU VRAM (local) | On each GPU die | ~1–10 µs | GB–tens of GB | Active rendering, compute working set |
| Heap 1 | GPU VRAM (peer) | On other GPUs via PCIe | ~5–50 µs | GB–tens of GB | Shared data, read-only textures |
| Heap 2 | Host RAM (NIC-attached) | System RAM, NUMA-local | ~100–500 ns | GB–hundreds of GB | Staging, fallback allocations |
| Heap 3 | Host RAM (remote) | System RAM, non-local NUMA | ~200–1000 ns | GB–hundreds of GB | Cold data, persistent storage |
| Heap 4 | SSD/Storage | NVMe / block device swap | ~10–100 µs | TB | Memory oversubscription, checkpoint |

**Allocation Policy:**

```
Request size < 64 MB  →  Heap 0 (GPU with most free VRAM)
Render target         →  Heap 0 (GPU that will write first, from workload history)
Large buffer (>1 GB)  →  Heap 2 (host RAM staging) + stream to Heap 0 as needed
Read-only textures    →  Heap 1 (replicate to peer GPU VRAM)
Cold data             →  Heap 3 (remote NUMA) or Heap 4 (SSD swap)
```

---

## Layer 6 — Safety Subsystems (Rust)

**Source:** `safe/` (3 Rust crates, edition 2021, MSRV 1.75)  
**License:** MIT OR Apache-2.0

### Responsibilities

Memory-safe implementations of critical subsystems that require rigorous lifetime tracking. Each crate exposes a C FFI interface with `#[no_mangle] extern "C"` functions.

### `fence_manager` (~248 LOC)

Cross-device fence lifecycle management.

**State machine:** `Pending → Submitted → Signalled → Reset`

**C FFI:**
```c
uint64_t mvgal_fence_create(uint32_t gpu_index);
void     mvgal_fence_submit(uint64_t handle);
void     mvgal_fence_signal(uint64_t handle);
uint32_t mvgal_fence_state(uint64_t handle);   // 0=Pending 1=Submitted 2=Signalled 3=Reset
void     mvgal_fence_reset(uint64_t handle);
void     mvgal_fence_destroy(uint64_t handle);
```

### `memory_safety` (~230 LOC)

Safe wrappers for cross-GPU memory allocation tracking with reference counting.

**Placements:** `SystemRam`, `GpuVram`, `Mirrored`

**C FFI:**
```c
uint64_t mvgal_mem_track(uint64_t size, uint32_t placement);
void     mvgal_mem_retain(uint64_t handle);
void     mvgal_mem_release(uint64_t handle);
void     mvgal_mem_set_dmabuf(uint64_t handle, int32_t fd);
uint64_t mvgal_mem_size(uint64_t handle);
uint32_t mvgal_mem_placement(uint64_t handle);
uint64_t mvgal_mem_total_system_bytes(void);
uint64_t mvgal_mem_total_gpu_bytes(void);
```

### `capability_model` (~260 LOC)

GPU capability normalization, aggregate profile computation, and JSON serialization.

**Tiers:** `Full` (all GPUs same API set), `ComputeOnly`, `Mixed`

**C FFI:**
```c
uint64_t    mvgal_cap_compute(const GpuCapability *caps, uint32_t count);
void        mvgal_cap_free(uint64_t handle);
uint64_t    mvgal_cap_total_vram(uint64_t handle);
uint32_t    mvgal_cap_tier(uint64_t handle);
const char *mvgal_cap_to_json(uint64_t handle);
```

### Rust/C++ FFI Boundary

The FFI boundary between Rust safety crates (Layer 6) and the C++ daemon (Layer 3) is defined as follows:

```
┌──────────────────────────────────────────────────────────┐
│                   C++ Daemon (mvgald)                    │
│  #include "fence_manager.h"  // C FFI declarations       │
│  #include "memory_safety.h"  // C FFI declarations       │
│  #include "capability_model.h"  // C FFI declarations    │
├──────────────────────────────────────────────────────────┤
│                    extern "C" {                           │
│  mvgal_fence_create()  →  fence_manager::Fence::new()    │
│  mvgal_mem_track()     →  memory_safety::TrackedAlloc    │
│  mvgal_cap_compute()   →  capability_model::compute()    │
│                    }                                      │
├──────────────────────────────────────────────────────────┤
│                Rust Crates (safe/)                        │
│  fence_manager   →  #[no_mangle] extern "C" fn ...       │
│  memory_safety   →  #[no_mangle] extern "C" fn ...       │
│  capability_model  →  #[no_mangle] extern "C" fn ...     │
└──────────────────────────────────────────────────────────┘
```

**Rules:**
- All cross-language calls go through C FFI (`extern "C"`). No direct C++→Rust name mangling.
- Handles are `uint64_t` opaque tokens. No Rust structs exposed across the boundary.
- Memory allocations that cross the boundary use the C allocator (`malloc`/`free`) via `CString` / `Box::into_raw`.
- Error propagation: functions return `int32_t` where `< 0` indicates an error. Extended error info is logged on the Rust side.

---

## Layer 7 — API Interception

**Source:** `src/userspace/intercept/` + `opengl/` (C17)

### Responsibilities

Intercepts application API calls transparently and routes them through the MVGAL pipeline without application modification.

### Vulkan Layer (`src/userspace/intercept/vulkan/`)

`VK_LAYER_MVGAL` is a Vulkan explicit layer registered via `/usr/share/vulkan/implicit_layer.d/VK_LAYER_MVGAL.json`.

Uses the Vulkan loader dispatch-chain pattern. Each intercepted function looks up the next function pointer via `vkGetInstanceProcAddr` / `vkGetDeviceProcAddr`.

**Intercepted functions:**
- Instance: `vkCreateInstance`, `vkDestroyInstance`, `vkEnumeratePhysicalDevices`
- Device: `vkCreateDevice`, `vkDestroyDevice`, `vkGetDeviceQueue`, `vkGetDeviceQueue2`
- Queue: `vkQueueSubmit`, `vkQueueSubmit2`, `vkQueueSubmit2KHR`
- Physical device: `vkGetPhysicalDeviceProperties`, `vkGetPhysicalDeviceFeatures`, `vkGetPhysicalDeviceMemoryProperties`, `vkGetPhysicalDeviceQueueFamilyProperties`, `vkGetPhysicalDeviceProperties2`, `vkGetPhysicalDeviceFeatures2`, `vkGetPhysicalDeviceMemoryProperties2`

**Global state** (`g_mvgal_layer_state`): linked lists of instance, device, queue, and physical device dispatch tables. Protected by `pthread_mutex_t`. Atomic submit counter.

**MVGAL VkPhysicalDevice extensions:**
- `VK_MVGAL_aggregation_device` — query aggregated device properties
- `VK_MVGAL_memory_heaps` — query MVGAL memory heap hierarchy (Heaps 0-4)
- `VK_MVGAL_scheduling_hint` — hint scheduling strategy per queue

**Debug:** `MVGAL_VULKAN_DEBUG=1` enables logging. `MVGAL_VULKAN_LOG_PATH=<path>` redirects to file.

### OpenCL Layer (`src/userspace/intercept/opencl/`)

LD_PRELOAD-based interception. Presents all GPUs as a single MVGAL OpenCL platform. NDRange kernels are partitioned across GPUs by splitting the global work size.

Registered via `/etc/OpenCL/vendors/mvgal.icd`.

### CUDA Shim (`src/userspace/intercept/cuda/`)

LD_PRELOAD-based interception of 40+ CUDA Driver and Runtime API functions. Intercepts:

- `cuLaunchKernel`, `cudaLaunchKernel` — kernel launches
- `cuMemAlloc`, `cudaMalloc`, `cuMemFree`, `cudaFree` — memory management
- `cuMemcpy*`, `cudaMemcpy*` — memory transfers
- Cross-GPU copy detection and memory tracking per GPU

### Direct3D Shims (`src/userspace/intercept/d3d/`)

| Shim | Targets | Approach |
|------|---------|----------|
| D3D9 | Direct3D 9 games | DXVK bridge → Vulkan layer |
| D3D11 | Direct3D 11 applications | DXVK bridge → Vulkan layer |
| D3D12 | Direct3D 12 applications | VKD3D-Proton bridge → Vulkan layer |

All D3D shims intercept `CreateDXGIFactory*`, `CreateDirect3D11Device*`, `CreateDirect3D12Device*` and inject MVGAL into the DXVK/VKD3D-Proton pipeline.

### Metal Shim (`src/userspace/intercept/metal/`)

Interposes `MTLCreateSystemDefaultDevice` and `MTLCopyAllDevices` via `DYLD_INSERT_LIBRARIES`. Routes Metal command buffers through MVGAL scheduling. Note: Metal interception is macOS-only (future).

### WebGPU Shim (`src/userspace/intercept/webgpu/`)

Intercepts `wgpuCreateInstance`, `WGPUAdapter` enumeration. Proxies WebGPU workloads to MVGAL for browser-based compute and ML workloads.

### SPIR-V Routing (`src/userspace/intercept/spirv/`)

Inspects SPIR-V shader modules at pipeline creation time. Routes compute shaders identified as AI/ML kernels to the Compute Offload scheduler. Enables cross-vendor SPIR-V capability probing.

### OpenGL Preload (`opengl/mvgal_gl_preload.c`)

LD_PRELOAD shim intercepting `glXSwapBuffers` and `eglSwapBuffers`. Injects frame pacing telemetry. Actual OpenGL→Vulkan translation is handled by Zink (Mesa).

---

## Layer 8 — Tooling & Bindings

### CLI Tools (`tools/`)

| Tool | Key Functions | Language |
|------|--------------|----------|
| `mvgal-info` | `enumerate_drm_gpus()`, reads `/sys/class/drm/cardN/device/`, JSON output | C |
| `mvgal-status` | `discover_gpus()`, `refresh_gpu_status()`, ANSI progress bars, daemon socket check | C |
| `mvgal-bench` | `bench_memory_bandwidth()`, `bench_compute()`, `bench_scheduling_latency()`, `bench_sync_overhead()` | C |
| `mvgal-compat` | `check_system()`, `check_app()`, 15+ app database, system readiness scoring | C |
| `mvgal-config` | `list_gpus()`, `set_strategy()`, `set_gpu_enabled()`, `show_stats()` | C |
| `mvgal-powercurve` | Per-GPU power curve tuning, DVFS override, thermal threshold config | C |

### Qt Dashboard (`ui/`)

- `mvgal_dashboard.cpp` — Qt5/Qt6 main window with 4 tabs: Overview, Scheduler, Logs, Config
- `GpuWidget` — per-GPU utilization/VRAM progress bars, temperature, power, clock, workload type
- `mvgal_rest_server.go` — Go HTTP server on `:7474`

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/gpus` | Read | All GPU metrics |
| `GET /api/v1/gpus/{id}` | Read | Single GPU |
| `GET /api/v1/scheduler` | Read | Current mode and GPU count |
| `PUT /api/v1/scheduler` | Write | Set scheduling strategy |
| `GET /api/v1/stats` | Read | Aggregate stats (total VRAM, avg utilization, daemon status) |
| `GET /api/v1/logs` | Read | Last 100 lines of daemon log |

### Steam Integration (`steam/`)

- `mvgal_frame_pacer.c` — vsync-aligned frame pacing with ring buffer (depth 8)
- Steam compatibility tool integration (select in Properties → Compatibility)

| Environment Variable | Values | Description |
|----------|--------|-------------|
| `ENABLE_MVGAL` | `0` / `1` | Enable MVGAL for this launch |
| `MVGAL_STRATEGY` | `afr`, `sfr`, `hybrid`, `single`, `rld`, `ppl` | Scheduling strategy |
| `MVGAL_FRAME_PACING` | `0` / `1` | Enable vsync-aligned frame pacing |
| `MVGAL_GPU_MASK` | hex bitmask | Which GPUs to use (e.g. `0x3` = GPU 0+1) |
| `MVGAL_VULKAN_DEBUG` | `0` / `1` | Enable Vulkan layer debug logging |

### Language Bindings (`bindings/`)

| Language | Directory | Status |
|----------|-----------|--------|
| Java | `bindings/java/` | JNI wrappers around C API |
| C# | `bindings/csharp/` | P/Invoke bindings |
| D | `bindings/d/` | D import bindings |
| Nim | `bindings/nim/` | Nim wrapper |
| V | `bindings/v/` | V bindings |
| Crystal | `bindings/crystal/` | Crystal FFI wrappers |
| Haxe | `bindings/haxe/` | Haxe extern bindings |

---

## Data Flow: Gaming Workload (AFR)

```
Game (via Proton/DXVK)
  │
  │ vkQueueSubmit (frame N)
  ▼
VK_LAYER_MVGAL (Layer 7 — Intercept)
  │ intercepts submit, increments atomic counter, logs telemetry
  │ forwards to next layer in dispatch chain
  ▼
Physical ICD (AMD / NVIDIA / Intel)
  │
  │ (parallel) mvgald AFR scheduler
  │   ├─ Frame N   → GPU 0  (even)
  │   └─ Frame N+1 → GPU 1  (odd)
  ▼
Frame pacer (steam/mvgal_frame_pacer.c) [Layer 8 — Tooling]
  │ ring buffer depth 8, background thread
  │ sleep_until_ns(next_vsync_boundary)
  ▼
vkQueuePresentKHR on display-connected GPU
```

## Data Flow: AI Compute Workload

```
PyTorch / TensorFlow
  │
  │ CUDA kernel launch (cudaLaunchKernel)
  ▼
MVGAL CUDA shim (Layer 7 — Intercept, LD_PRELOAD)
  │ intercepts, translates to MVGAL workload submission
  ▼
mvgald Compute Offload scheduler (Layer 3 — Runtime)
  │ shards batch dimension across N GPUs
  │ allocates input tensors via unified memory manager
  │ issues DMA-BUF transfers for cross-GPU data
  ▼
GPU 0 … GPU N-1 (parallel execution)
  │
  │ results collected via write-combined system
  ▼
Application receives aggregated result
```

## Data Flow: Render Layer Distribution (RLD)

```
Game with separable UI / world / post-fx layers
  │
  │ vkQueueSubmit (multiple command buffers per frame)
  ▼
VK_LAYER_MVGAL (Layer 7 — Intercept)
  │ identifies layer boundaries from render passes
  ▼
WDE RLD strategy (Layer 5)
  │   ├─ UI layer       → GPU 0 (simple, latency-sensitive)
  │   ├─ World layer    → GPU 1 (complex geometry, high FLOPS)
  │   └─ Post-FX layer  → GPU 2 (compute-heavy, low VRAM need)
  ▼
IMFL (Layer 4) produces composite plan
  │ DMA-BUF transfer for final composite
  ▼
Display-connected GPU presents final frame
```

---

## Memory Architecture

### Allocation Policy

```
Request size < 64 MB          → Heap 0 (GPU local VRAM)
Render target                 → Heap 0 (write GPU)
Read-only texture             → Heap 1 (replicate to peers)
Large buffer >1 GB            → Heap 2 (host staging → stream to Heap 0)
Persistent/cold data          → Heap 3 (remote NUMA)
Memory oversubscription       → Heap 4 (SSD swap)
```

### Transfer Path

```
Source GPU export
  │
  ├─ DMA-BUF viable?  →  dma_buf_map_attachment (zero-copy, kernel-supported)
  │
  └─ DMA-BUF not viable
       │
       ├─ PCIe P2P viable?  →  pci_p2pdma (requires same root complex, kernel 5.10+)
       │
       └─ Fallback  →  mmap source + DMA to host staging buffer + upload to dest GPU
```

### Memory Flags

| Flag | Value | Description |
|------|-------|-------------|
| `HOST_VALID` | `1<<0` | CPU can access (mapped) |
| `GPU_VALID` | `1<<1` | GPUs can access |
| `CPU_CACHED` | `1<<2` | CPU cached |
| `CPU_UNCACHED` | `1<<3` | CPU uncached (write-combined) |
| `SHARED` | `1<<4` | Shared across GPUs |
| `DMA_BUF` | `1<<5` | Use DMA-BUF |
| `P2P` | `1<<6` | Enable P2P transfers |
| `REPLICATED` | `1<<7` | Mirror across all GPUs |
| `PERSISTENT` | `1<<8` | Persistent CPU mapping |
| `LAZY_ALLOCATE` | `1<<9` | Defer physical allocation |
| `ZERO_INITIALIZED` | `1<<10` | Zero on allocation |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Character device instead of DRM driver (Phase 1) | Avoids claiming PCI devices from vendor drivers; simpler to maintain across kernel versions |
| DRM driver (Phase 2) | Planned migration for native compositor integration, DRM sync objects, and GEM lifecycle |
| Vulkan layer instead of full ICD (Phase 1) | Allows transparent interception without application changes; full ICD planned for Phase 5 |
| 8-layer architecture | Separates HAL (kernel) from VGDD (vendor dispatch), distinguishes IMFL (framing) from WDE (strategy), elevates Rust safety to its own layer |
| Rust for safety-critical paths | Eliminates memory safety bugs in fence/memory tracking; C FFI boundary provides clean interop |
| C17 for userspace, C++20 for daemon | C17 maximizes compatibility with GPU driver headers; C++20 provides modern abstractions for daemon |
| Unix socket IPC with `SCM_CREDENTIALS` | Zero-dependency authentication; no D-Bus or systemd dependency required for core IPC |
| D-Bus as optional management interface | Standard Linux desktop integration for monitoring tools and session services |
| DMA-BUF for cross-GPU transfers | Kernel-supported zero-copy path; works across all vendor drivers that support it |
| Sysfs polling for GPU metrics | No vendor-specific SDK required; works on all supported vendors |
| `pkexec` for all privileged operations | Policy-compliant privilege escalation; no `sudo` dependency |
| 5-tier memory heap hierarchy | Matches real hardware topology (local VRAM, peer VRAM, NUMA host RAM, remote RAM, SSD) |
| 10 scheduling strategies (7+3) | Covers all known workload patterns; RLD/REP/PPL address gaps from original 7 strategies |
| Language bindings for 7 languages | Maximizes accessibility for developers in different ecosystems with zero additional runtime cost |

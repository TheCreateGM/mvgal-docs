# MVGAL Scheduling & Memory Strategies

> **Version**: 0.5.0  
> **Layer**: 5 — WDE (Workload Distribution Engine)  
> **Status**: Comprehensive  
> **Last Updated**: 2026-06-06

---

## Table of Contents

1. [Overview](#overview)
2. [Existing Scheduler Strategies (7)](#existing-scheduler-strategies)
3. [New Strategies](#new-strategies)
   - [RLD — Render Layer Distribution](#rld-render-layer-distribution)
   - [REP — Replication Mode](#rep-replication-mode)
   - [PPL — Pipeline Parallelism](#ppl-pipeline-parallelism)
4. [Memory Heap Hierarchy](#memory-heap-hierarchy)
5. [Strategy Selection](#strategy-selection)
6. [Workload-Type Matrix](#workload-type-matrix)

---

## Overview

MVGAL's Workload Distribution Engine (WDE, Layer 5) implements 10 scheduling
strategies that map GPU work across 1–N physical devices. The first 7 strategies
cover conventional GPU sharing (time-slicing, spatial partitioning, load
balancing). The 3 new strategies — RLD, REP, PPL — target multi-GPU workloads
where frames, data, or pipeline stages are distributed across devices.

All strategies operate through the common `mvgal_scheduler` interface defined in
`src/userspace/scheduler/` and the kernel-side `mvgal_scheduler.c` for
prioritization.

---

## Existing Scheduler Strategies (7)

### 1. Round-Robin (RR)
Assigns submissions to GPUs in cyclic order. Simplest balancing — no
per-device load tracking. Best for homogeneous pools with uniform workload.

### 2. Least-Load (LL)
Tracks per-GPU queue depth and assigns to the device with fewest pending
submissions. Requires metrics_collector for queue-depth sampling.

### 3. Priority (PRI)
Each submission carries a priority hint (0–7). High-priority work lands on the
fastest device; lower-priority fills remaining capacity.

### 4. Affinity (AFF)
Pins a process or context to a specific GPU. Once assigned, all submissions
from that context target the same device. Useful for latency-sensitive
workloads (VR compositors, real-time rendering).

### 5. Bin-Packing (BP)
Packs submissions into the smallest number of GPUs to maximise idle-device
power saving. Complementary to power_manager — devices with no load enter D3.

### 6. GPU-Aware (GA)
Respects topology: NVLink/XGMI peers get first preference for inter-GPU
transfers; PCIe-attached devices are fallback.

### 7. Hybrid (HYB)
Combines two or more strategies via a weighted decision function. Configured
through the scheduler JSON policy file (see `mvgal-sched` tool).

---

## New Strategies

### RLD — Render Layer Distribution

**Purpose**: Split a single frame's render layers across multiple GPUs,
re-compositing via the daemon's inter-GPU transfer engine.

**How it works**:
1. Application submits a full command buffer to the intercept layer (Layer 7).
2. The intercept layer decomposes the submission into N logical render layers
   (opaque, transparent, post-process, UI overlay).
3. Each layer is dispatched to a different GPU via DMA-BUF export.
4. After completion, layers are composited by `mvgald` on the primary GPU
   using the inter-GPU copy engine (`runtime/daemon/ipc_server.cpp`).

**Best for**:
- Deferred-shading renderers with separable geometry/lighting passes
- Split-frame VR (left eye / right eye on separate GPUs)
- UI-overlay rendering without compositor stalls

**Constraints**:
- Requires `MVGAL_RENDER_LAYER_SPLIT` feature flag in device caps
- Layer decomposition overhead ≤ 5% frame budget
- Inter-GPU copy must saturate at least PCIe 4.0 x16 bandwidth

### REP — Replication Mode

**Purpose**: Replicate identical workloads across N GPUs for fault tolerance,
ML training data parallelism, or benchmarking.

**How it works**:
1. A single submission is cloned N–1 times by the WDE.
2. Each clone targets a distinct GPU with identical command buffers.
3. Completion waits for all replicas to finish.
4. Results are compared via a reduction callback (optional; for fault-tolerant
   mode only).

**Best for**:
- Data-parallel ML training (same model, different micro-batches)
- Mission-critical rendering (triple-redundant display)
- Comparative benchmarking (same workload, different GPU SKUs)

**Constraints**:
- Replicas share the same input buffer (copy-on-write via DMA-BUF)
- Fault-tolerant mode adds ~10% overhead for result comparison
- N ≥ 2 required; no upper limit beyond VRAM capacity

### PPL — Pipeline Parallelism

**Purpose**: Split a GPU workload into pipeline stages and assign each stage
to a different GPU, streaming data through the chain.

**How it works**:
1. The WDE analyses the command DAG (`docs/ARCHITECTURE.md §4.3 — IMFL`).
2. It partitions the DAG into N contiguous stages at natural barrier boundaries.
3. Each stage executes on one GPU; outputs are transferred to the next GPU
   via P2P DMA-BUF.
4. Pipeline depth is N; throughput is limited by the slowest stage.

**Best for**:
- Post-processing chains (tone-map → sharpen → output encode)
- Video transcoding pipelines (decode → process → encode)
- Multi-pass compute workloads

**Constraints**:
- Requires DAG analysis from IMFL (Layer 4)
- Stage imbalance reduces throughput; `mvgal-sched analyze` reports efficiency
- P2P DMA-BUF between non-adjacent stages adds latency

---

## Memory Heap Hierarchy

MVGAL defines 4 memory heaps with distinct performance characteristics.
Applications or the WDE select a heap based on access pattern.

| Heap | Name | Location | Bandwidth | Use Case |
|------|------|----------|-----------|----------|
| 0 | HOST | System RAM | ~50 GB/s (DDR5) | Staging, CPU access |
| 1 | VRAM_CACHE | GPU VRAM (preferred) | ~900 GB/s (HBM2e) | Frequent device-local access |
| 2 | VRAM_STEER | Arbitrated GPU VRAM | Bandwidth-shared | Multi-GPU shared allocations |
| 3 | ZONE_BIN | Partitioned VRAM | Slab-granularity | Fine-grained allocation regions |

**Heap 0 — HOST**: Traditional system memory. Coherent with CPU cache. Used
for submission stagin, readbacks, and fallback when VRAM is exhausted.

**Heap 1 — VRAM_CACHE**: The preferred device-local allocation. Uses first-touch
placement on the GPU that first accesses the buffer. Migrates on access pattern
change (monitored by `mvgald` metrics).

**Heap 2 — VRAM_STEER**: For allocations shared across multiple GPUs. The daemon
arbitrates which device's VRAM hosts the physical allocation; other devices
access via P2P DMA-BUF. Arbitration policy is configurable (RR, LL, locality).

**Heap 3 — ZONE_BIN**: Divides VRAM into fixed-size zones (configured via
`mvgal-config`). Allocations are rounded up to the nearest zone size.
Reduces fragmentation for small, frequently-allocated buffers.

The heap hierarchy is exposed through `include/mvgal/mvgal_unified_heap.h`
and `include/mvgal/mvgal_memory.h`.

---

## Strategy Selection

The WDE selects a strategy based on workload characteristics:

```
Workload Type ──→ Strategy Selection ──→ Heap Assignment ──→ GPU Mapping
```

### Selection Criteria

| Workload Type | Default Strategy | Heap | Rationale |
|---------------|-----------------|------|-----------|
| Single-GPU game | PRI | VRAM_CACHE | Fastest GPU gets the frame |
| Multi-GPU VR | RLD | VRAM_STEER | Split eye renders |
| ML Training (data-parallel) | REP | ZONE_BIN | Identical model on each GPU |
| Video Transcoding | PPL | HOST + VRAM_CACHE | Stream through pipeline |
| Compute Shader | LL + GA | VRAM_CACHE | Load-balance with topology |
| Compositor | AFF | VRAM_CACHE | Pin to display GPU |
| Unknown | HYB (RR+LL) | VRAM_CACHE | Safe default |

### Override Mechanism

Strategy can be overridden per-application via:
- `MVGAL_SCHED_STRATEGY` environment variable
- `/etc/mvgal/app-policies/<app>.json` policy file
- `mvgal-sched set-policy <app> <strategy>` CLI command

---

## Workload-Type Matrix

The following table shows which strategies are applicable per GPU API:

| API | RR | LL | PRI | AFF | BP | GA | HYB | RLD | REP | PPL |
|-----|:--:|:--:|:---:|:---:|:--:|:--:|:---:|:---:|:---:|:---:|
| Vulkan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| OpenGL | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| OpenCL | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| CUDA | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Direct3D (WCL) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| Metal (via WCL) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| WebGPU | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |

**Legend**: ✓ = applicable, — = not applicable

---

*See `docs/ARCHITECTURE.md` §5—WDE for the layer architecture.  
See `src/userspace/scheduler/` for implementation.*

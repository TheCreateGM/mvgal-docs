# mvgal-docs

Documentation for **MVGAL** — Multi-Vendor GPU Aggregation Layer for Linux.

## What is MVGAL?

Most Linux systems with multiple GPUs (e.g. an AMD RX 7900 + NVIDIA RTX 4080) treat each card as a completely separate device. Applications can only use one at a time, leaving the other idle.

MVGAL solves this by aggregating all available GPUs — regardless of vendor — into a single logical device. Any application, game, or compute workload can use it without modification.

```
Your Application / Game / AI Workload
           │              │              │
       Vulkan           OpenCL          CUDA
           ▼              ▼              ▼
┌──────────────────────────────────────────────────┐
│            MVGAL API Interception Layer            │
│  VK_LAYER_MVGAL │ libmvgal_opencl │ libmvgal_cuda │
└──────────────────────┬───────────────────────────┘
                       │ Unix socket
                       ▼
┌──────────────────────────────────────────────────┐
│               mvgald  (daemon)                     │
│  Scheduler │ MemoryMgr │ PowerMgr │ Metrics │ IPC │
└──────┬──────────┬──────────┬──────────┬──────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
  amdgpu.ko  nvidia.ko  i915/xe.ko  mtgpu-drv.ko
  (AMD GPU) (NVIDIA GPU) (Intel GPU) (MTT GPU)
```

## Features

- **Heterogeneous multi-GPU** — AMD, NVIDIA, Intel, and Moore Threads GPUs in any combination
- **Transparent interception** — Vulkan layer, OpenCL ICD, CUDA shim; no application changes needed
- **7 scheduling strategies** — Round-robin, AFR, SFR, Task-based, Compute offload, Hybrid, Single-GPU
- **Unified memory manager** — DMA-BUF zero-copy, PCIe P2P, host-RAM staging fallback
- **GPU health monitoring** — Temperature, utilization, VRAM pressure with configurable thresholds
- **Steam/Proton integration** — Frame pacing, AFR for games, DXVK and VKD3D-Proton compatible
- **Power management** — Idle detection, GPU parking, dynamic frequency scaling
- **Memory-safe subsystems** — Fence manager, memory tracker, capability model written in Rust
- **Qt dashboard + REST API** — Real-time monitoring, scheduler control, log viewer

## Supported Hardware

| Vendor | Architectures | Driver |
|--------|--------------|--------|
| **AMD** | RDNA 1/2/3, GCN, APU (Vega/RDNA) | `amdgpu` |
| **NVIDIA** | Turing (RTX 20xx), Ampere (RTX 30xx), Ada (RTX 40xx), Pascal | `nvidia-open` / proprietary |
| **Intel** | Gen 9–12 (iGPU), Xe / Arc (discrete) | `i915` / `xe` |
| **Moore Threads** | MTT S60, S80, S2000 | `mtgpu-drv` |

## Install from COPR (no build needed)

MVGAL is available as a pre-built package via Fedora COPR. No need to compile from source.

```bash
sudo dnf copr enable axogm/mvgal
sudo dnf install mvgal
```

Supported targets: Fedora 40+ · RHEL/AlmaLinux/Rocky 9 & 10 · CentOS Stream 9 & 10 · openSUSE Tumbleweed · Amazon Linux 2023

## Quick Start

```bash
# Start the daemon
pkexec systemctl start mvgald
pkexec systemctl enable mvgald   # start on boot

# Verify
mvgal-info          # list detected GPUs
mvgal-status        # real-time utilization
mvgal-compat --system   # check readiness
```

## CLI Tools

| Tool | Description |
|------|-------------|
| `mvgal-info` | Print all detected GPUs, VRAM, temperature, utilization |
| `mvgal-status` | Real-time GPU utilization/VRAM bars; `--watch` for continuous refresh |
| `mvgal-bench` | Memory bandwidth, compute FLOPS, scheduling latency |
| `mvgal-compat` | System readiness check + per-app compatibility database |
| `mvgal-config` | Configure scheduler mode, idle thresholds, GPU enable/disable |
| `mvgal` | Main CLI: start/stop daemon, set strategy, show stats |

## Scheduling Strategies

| Strategy | Best For |
|----------|----------|
| Round-robin | Even distribution, general compute |
| Alternate Frame Rendering (AFR) | Gaming — odd/even frames on different GPUs |
| Split Frame Rendering (SFR) | Gaming — horizontal/vertical tile split |
| Task-based | Mixed graphics + compute workloads |
| Compute offload | AI/HPC — route compute to best GPU |
| Hybrid adaptive | Automatic selection based on workload metrics |
| Single GPU | Fallback / compatibility mode |

## Steam / Proton Integration

Add to Steam launch options:
```
ENABLE_MVGAL=1 MVGAL_STRATEGY=afr %command%
```

| Variable | Values | Description |
|----------|--------|-------------|
| `ENABLE_MVGAL` | `0` / `1` | Enable MVGAL for this launch |
| `MVGAL_STRATEGY` | `afr`, `sfr`, `hybrid`, `single` | Scheduling strategy |
| `MVGAL_FRAME_PACING` | `0` / `1` | Enable vsync-aligned frame pacing |
| `MVGAL_GPU_MASK` | hex bitmask | Which GPUs to use (e.g. `0x3` = GPU 0+1) |

## Memory Management

MVGAL uses a three-tier transfer strategy:

1. **DMA-BUF zero-copy** (preferred — kernel-supported, all vendors)
2. **PCIe P2P transfer** (fallback — requires same root complex)
3. **Host-RAM staging** (last resort — always works, highest latency)

## License

- **Kernel module**: GPL-2.0-only
- **Userspace components**: GPL-3.0-only
- **Rust crates**: MIT OR Apache-2.0

## Source Code

The MVGAL source code is available for purchase at:

- **Patreon Shop** — [patreon.com/axogm/shop](https://www.patreon.com/axogm/shop)
- **Ko-fi Shop** — [ko-fi.com/axogm/shop](https://ko-fi.com/axogm/shop)

Your purchase helps fund continued development of MVGAL and other open-source projects.

## Getting Help

- **Issues & bugs** — [github.com/TheCreateGM/mvgal-docs/issues](https://github.com/TheCreateGM/mvgal-docs/issues)
- **Suggestions & improvements** — [github.com/TheCreateGM/mvgal-docs/discussions](https://github.com/TheCreateGM/mvgal-docs/discussions)

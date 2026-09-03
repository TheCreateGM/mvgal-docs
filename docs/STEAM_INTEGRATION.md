# MVGAL Steam/Proton Integration

**Version:** 1.0  
**Date:** 2026-06-02

---

## Table of Contents

1. [Overview](#1-overview)
2. [Integration Methods](#2-integration-methods)
3. [Vulkan Layer Integration](#3-vulkan-layer-integration)
4. [Frame Pacer](#4-frame-pacer)
5. [Alternate Frame Rendering (AFR)](#5-alternate-frame-rendering-afr)
6. [NTSYNC-like Improvements](#6-ntsync-like-improvements)
7. [WoW64 Support](#7-wow64-support)
8. [Configuration](#8-configuration)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Overview

MVGAL integrates with Steam and Proton to enable multi-GPU gaming on Linux. The integration consists of:

1. **Vulkan Implicit Layer** (`VK_LAYER_MVGAL`) - Automatically intercepts Vulkan calls
2. **Frame Pacer** - Ensures consistent frame timing for AFR
3. **Proton Hook** - Environment setup for Steam games
4. **Compatibility Tool** - Native Steam integration

---

## 2. Integration Methods

### 2.1 Steam Launch Options

Add to game properties → Launch Options:

```bash
ENABLE_MVGAL=1 MVGAL_STRATEGY=afr %command%
```

### 2.2 Steam Compatibility Tool

Install MVGAL as a Steam compatibility tool:

1. Download the compatibility tool archive
2. Extract to `steamapps/common/Proton - MVGAL/`
3. Select in game properties → Compatibility → "Proton - MVGAL"

### 2.3 Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `ENABLE_MVGAL` | `0` / `1` | Enable/disable MVGAL |
| `MVGAL_STRATEGY` | `afr`, `sfr`, `hybrid`, `single` | Scheduling strategy |
| `MVGAL_FRAME_PACING` | `0` / `1` | Enable frame pacing |
| `MVGAL_GPU_MASK` | hex bitmask | GPU selection (e.g., `0x3` = GPUs 0+1) |
| `MVGAL_VULKAN_DEBUG` | `0` / `1` | Enable Vulkan layer debug |
| `MVGAL_LOG_PATH` | path | Write logs to file |

---

## 3. Vulkan Layer Integration

### 3.1 Layer Discovery

MVGAL registers as a Vulkan implicit layer:

```json
// /usr/share/vulkan/implicit_layer.d/VK_LAYER_MVGAL.json
{
    "file_format_version": "1.0.0",
    "chain_as_layer_as_is": true,
    "layer": {
        "name": "VK_LAYER_MVGAL_aggregation",
        "description": "MVGAL multi-vendor GPU aggregation",
        "type": "IMPLICIT",
        "library_path": "libVK_LAYER_MVGAL.so",
        "apis": [{"version": "1.3.0", "name": "VK_API_VERSION"}]
    }
}
```

### 3.2 Intercepted Functions

The layer intercepts:

**Instance Level:**
- `vkCreateInstance`
- `vkDestroyInstance`
- `vkEnumeratePhysicalDevices`

**Device Level:**
- `vkCreateDevice`
- `vkDestroyDevice`
- `vkGetDeviceQueue`
- `vkGetDeviceQueue2`

**Queue Level:**
- `vkQueueSubmit`
- `vkQueueSubmit2`
- `vkQueueWaitIdle`

**Physical Device:**
- `vkGetPhysicalDeviceProperties`
- `vkGetPhysicalDeviceMemoryProperties`
- `vkGetPhysicalDeviceQueueFamilyProperties`

### 3.3 Layer Implementation

```c
// Simplified layer dispatch
VKAPI_ATTR VkResult VKAPI_CALL vkQueueSubmit(
    VkQueue queue,
    uint32_t submitCount,
    const VkSubmitInfo* const pSubmits,
    VkFence fence)
{
    // Get MVGAL context
    mvgal_context_t *ctx = mvgal_layer_get_context();
    
    // Determine which GPU to use based on strategy
    uint32_t gpu_index = mvgal_scheduler_select_gpu(ctx, queue);
    
    // Log telemetry
    mvgal_ipc_send_submit(queue, gpu_index, pSubmits, submitCount);
    
    // Forward to next layer
    return ctx->next_vkQueueSubmit(queue, submitCount, pSubmits, fence);
}
```

---

## 4. Frame Pacer

### 4.1 Purpose

Multi-GPU AFR can cause microstutter if frames are delivered at uneven intervals. The frame pacer holds completed frames and releases them at consistent vsync-aligned times.

### 4.2 Architecture

```
Game (via DXVK/VKD3D)
    │
    ▼
vkQueuePresentKHR
    │
    ▼
VK_LAYER_MVGAL (intercepts)
    │
    ▼
mvgal_frame_pacer_submit(frame_id, gpu_index)
    │
    ▼
Frame Pacer Thread (background)
    │
    ├── Wait for next vsync boundary
    │
    └── Signal presentation semaphore
```

### 4.3 Configuration

```bash
# Enable frame pacing (default: on for AFR)
export MVGAL_FRAME_PACING=1

# Set refresh rate (default: 60 Hz)
export MVGAL_REFRESH_HZ=144

# Debug output
export MVGAL_FRAME_PACING_DEBUG=1
```

### 4.4 Frame Pacer API

```c
/* Initialize frame pacer */
mvgal_frame_pacer_t *pacer = mvgal_fp_create(144);  /* 144 Hz */

/* Submit a completed frame */
mvgal_fp_submit_frame(pacer, frame_id, gpu_index);

/* Get statistics */
uint64_t frames_paced, frames_dropped;
double avg_jitter_us;
mvgal_fp_get_stats(pacer, &frames_paced, &frames_dropped, &avg_jitter_us);
```

---

## 5. Alternate Frame Rendering (AFR)

### 5.1 How AFR Works with MVGAL

```
Frame 0: GPU 0 renders
Frame 1: GPU 1 renders
Frame 2: GPU 0 renders
Frame 3: GPU 1 renders
...
```

### 5.2 Frame Synchronization

AFR requires synchronization between GPUs:

```c
struct afr_sync {
    uint64_t frame_counter;
    VkSemaphore present_semaphores[2];  /* GPU 0, GPU 1 */
    VkSemaphore render_semaphores[2];
};

void afr_submit_frame(struct afr_sync *sync, uint32_t frame_index) {
    uint32_t gpu_index = frame_index % 2;
    uint32_t wait_gpu = (gpu_index + 1) % 2;
    
    /* Wait for previous frame on other GPU */
    vkWaitForFences(device, 1, &sync->fences[wait_gpu], VK_TRUE, UINT64_MAX);
    
    /* Submit to GPU */
    vkQueueSubmit(queue[gpu_index], 1, &submit_info, sync->fences[gpu_index]);
}
```

### 5.3 AFR Configuration

```ini
# /etc/mvgal/mvgal.conf
[afr]
enable_sync = true
sync_timeout_ms = 16
max_latency = 3
```

---

## 6. NTSYNC-like Improvements

### 6.1 Windows NT Synchronization

NTSYNC is a Wine synchronization mechanism that maps Windows NT kernel objects to Linux. MVGAL provides similar functionality for better Windows compatibility.

### 6.2 NTSYNC Features in MVGAL

```c
/* Event object (manual/manual reset) */
struct mvgal_event {
    bool manual_reset;
    bool signaled;
    wait_queue_head_t wait_queue;
};

/* Semaphore object */
struct mvgal_semaphore {
    uint32_t count;
    uint32_t max_count;
    wait_queue_head_t wait_queue;
};

/* Mutex object with owner tracking */
struct mvgal_mutex {
    struct task_struct *owner;
    atomic_t count;
    wait_queue_head_t wait_queue;
};
```

### 6.3 Integration Points

1. **Wine**: NTSYNC driver in `dlls/ntsync/`
2. **Proton**: Pre-launch hook sets environment
3. **MVGAL Kernel**: NTSYNC syscall translation layer

---

## 7. WoW64 Support

### 7.1 WoW64 (Windows-on-Windows 64-bit)

WoW64 allows 32-bit Windows applications to run on 64-bit Windows. Under Proton, this requires special handling for GPU API calls.

### 7.2 MVGAL WoW64 Support

```c
/* Detect WoW64 process */
bool is_wow64_process(pid_t pid) {
    struct task_struct *task;
    /* Check if process is 32-bit running on 64-bit kernel */
    return is_32bit_task(task);
}

/* WoW64 layer routing */
void wow64_redirect_api(VkInstance inst, VkPhysicalDevice phys_dev) {
    /* Translate 32-bit pointers */
    /* Map to correct 64-bit structures */
}
```

### 7.3 WoW64 Configuration

```bash
# Enable WoW64 support
export MVGAL_WOW64=1

# WoW64-specific debug
export MVGAL_WOW64_DEBUG=1
```

---

## 8. Configuration

### 8.1 Steam Integration Setup

```bash
# Run the Steam setup tool
mvgal-steam-setup

# This creates:
# ~/.local/share/Steam/steamapps/common/Proton - MVGAL/
# ~/.local/share/Steam/steamapps/compat_tools.d/mvgal.json
```

### 8.2 Compatibility Tool Manifest

```json
{
    "Name": "Proton - MVGAL",
    "Version": "0.7.3",
    "VersionString": "Proton 9.0 with MVGAL 0.7.3",
    "Architectures": "x86_64,i686",
    "Priority": 100,
    "Enabled": true
}
```

---

## 9. Troubleshooting

### 9.1 Common Issues

**Issue: Game shows black screen**
```bash
# Solution: Disable frame pacing
export MVGAL_FRAME_PACING=0

# Or use single-GPU mode
export MVGAL_STRATEGY=single
```

**Issue: Layer not loaded**
```bash
# Check layer discovery
vulkaninfo | grep -i mvgal

# Verify JSON manifest location
ls /usr/share/vulkan/implicit_layer.d/VK_LAYER_MVGAL.json
```

**Issue: Anti-cheat blocked**
```bash
# Some games block Vulkan layers
# Solution: Use compatibility mode
export MVGAL_STRATEGY=single
```

### 9.2 Debug Commands

```bash
# Enable verbose logging
export MVGAL_VULKAN_DEBUG=1
export MVGAL_LOG_PATH=/tmp/mvgal.log

# View current state
mvgal-status --verbose

# Check GPU status
mvgal-info --json
```

### 9.3 Log Analysis

```bash
# Find frame timing issues
grep -i "jitter\|drop" /var/log/mvgal/mvgald.log

# Check GPU assignments
grep "submit.*gpu" /tmp/mvgal.log

# Power management logs
journalctl -u mvgald -f
```

---

## 10. Known Limitations

1. **Anti-cheat**: EasyAntiCheat and BattlEye block Vulkan layers
2. **Ray tracing**: Not split across GPUs in current implementation
3. **DX12**: May have synchronization issues with aggressive fences
4. **VR**: SteamVR requires special handling for multi-GPU

---

## 11. Performance Tips

1. **Use frame pacing for AFR**: Reduces microstutter
2. **Monitor temperatures**: Multi-GPU can thermal-throttle
3. **Check PCIe topology**: P2P transfers need same root complex
4. **Match workloads**: Don't mix high/low intensity on different GPUs

---

## 12. Future Improvements

1. **DXVK integration**: Direct hook into DXVK for lower latency
2. **VK_KHX_multivendor**: Experimental Vulkan extension
3. **Game-specific profiles**: Auto-detect and optimize for known titles
4. **AI-based scheduling**: Learn optimal strategies per game
---
tags: [mvgal, api, reference]
aliases: [API Reference, API]
mvgal_version: "0.7.14"
mvgal_verified: 2026-09-28
mvgal_role: reference
mvgal_order: 8
---

# MVGAL Public API Reference

> **Implementation status:** Source metadata is 0.7.14. The source changelog documents through 0.7.14. Treat design/API descriptions as available only where the relevant code path and runtime capability are verified; unsupported kernel submission and VRAM allocation return `-EOPNOTSUPP`.

**Source version:** 0.7.14 | **Header:** `#include <mvgal/mvgal.h>`

---

## Public C Headers

MVGAL currently contains 29 public C headers under `include/mvgal/`. The main header `mvgal.h` includes all core subsystem headers.

| Header | Description |
|--------|-------------|
| `mvgal.h` | Main API — init, shutdown, device query |
| `mvgal_types.h` | Core type definitions, enums, error codes |
| `mvgal_version.h` | Version macros (generated from `.h.in`) |
| `mvgal_uapi.h` | Kernel/userspace UAPI — IOCTL structs + commands |
| `mvgal_gpu.h` | GPU enumeration, properties, topology |
| `mvgal_memory.h` | Memory allocation, flags, placement |
| `mvgal_unified_heap.h` | Unified heap handle, placement and access-pattern hints |
| `mvgal_scheduler.h` | Scheduler strategy, policy control |
| `mvgal_execution.h` | Frame sessions, migration plans |
| `mvgal_power.h` | Power management, DVFS, thermal |
| `mvgal_config.h` | Configuration file parsing |
| `mvgal_binary.h` | Binary protocol helpers |
| `mvgal_ccl.h` | Collective communication primitives |
| `mvgal_dispatch.h` | Dispatch and interception helpers |
| `mvgal_shader_compiler.h` | Shader compilation utilities |
| `mvgal_log.h` | Logging subsystem |
| `mvgal_ipc.h` | IPC client/server — Unix domain socket protocol |
| `mvgal_intercept.h` | API intercept layer interface |
| `mvgal_p2p_dma.h` | P2P DMA transfer API |
| `mvgal_pool.h` | Memory pool management |
| `mvgal_fork.h` | GPU fork/clone support |
| `mvgal_ai.h` | AI/ML scheduling hint API |
| `mvgal_coherency.h` | Cache coherency management |
| `mvgal_barrier_translate.h` | Barrier translation (Vulkan ↔ CUDA ↔ OpenCL) |
| `mvgal_cmd_dag.h` | Command DAG analysis |
| `mvgal_shader_backend.h` | Shader backend interface (SPIR-V routing) |
| `mvgal_sycl.h` | SYCL backend support |
| `mvgal_network.h` | Network pooling / RDMA |
| `mvgal_wow64.h` | WoW64 filesystem redirection types |

---

## Core API (`mvgal.h`)

### Initialization

```c
// Initialize MVGAL with default configuration
mvgal_error_t mvgal_init(uint32_t flags);

// Initialize with a custom config file path
mvgal_error_t mvgal_init_with_config(const char *config_path, uint32_t flags);

// Shut down and free all resources
void mvgal_shutdown(void);

// Check initialization state
bool mvgal_is_initialized(void);

// Version information
const char *mvgal_get_version(void);
void        mvgal_get_version_numbers(uint32_t *major, uint32_t *minor, uint32_t *patch);
```

### Context Management

```c
mvgal_error_t mvgal_context_create(mvgal_context_t *context);
void          mvgal_context_destroy(mvgal_context_t context);
mvgal_error_t mvgal_context_set_current(mvgal_context_t context);
```

### Execution Control

```c
mvgal_error_t mvgal_flush(mvgal_context_t context);
mvgal_error_t mvgal_finish(mvgal_context_t context);
mvgal_error_t mvgal_wait_idle(mvgal_context_t context);
mvgal_error_t mvgal_set_enabled(mvgal_context_t context, bool enabled);
bool          mvgal_is_enabled(mvgal_context_t context);
```

### Strategy Control

```c
mvgal_error_t                mvgal_set_strategy(mvgal_context_t ctx, mvgal_distribution_strategy_t strategy);
mvgal_distribution_strategy_t mvgal_get_strategy(mvgal_context_t ctx);
```

### Statistics

```c
mvgal_error_t mvgal_get_stats(mvgal_context_t context, mvgal_stats_t *stats);
mvgal_error_t mvgal_reset_stats(mvgal_context_t context);
```

### Custom Splitters

```c
mvgal_error_t mvgal_register_custom_splitter(mvgal_context_t ctx,
                                              const mvgal_workload_splitter_t *splitter);
mvgal_error_t mvgal_unregister_custom_splitter(mvgal_context_t ctx);
```

### Synchronization Primitives

```c
// Fences
mvgal_error_t mvgal_fence_create(mvgal_context_t ctx, mvgal_fence_t *fence);
void          mvgal_fence_destroy(mvgal_fence_t fence);
mvgal_error_t mvgal_fence_wait(mvgal_fence_t fence, uint64_t timeout_ns);
bool          mvgal_fence_check(mvgal_fence_t fence);
mvgal_error_t mvgal_fence_reset(mvgal_fence_t fence);

// Timeline semaphores
mvgal_error_t mvgal_semaphore_create(mvgal_context_t ctx, mvgal_semaphore_t *sem);
void          mvgal_semaphore_destroy(mvgal_semaphore_t sem);
mvgal_error_t mvgal_semaphore_signal(mvgal_semaphore_t sem, uint64_t value);
mvgal_error_t mvgal_semaphore_wait(mvgal_semaphore_t sem, uint64_t value, uint64_t timeout_ns);
uint64_t      mvgal_semaphore_get_value(mvgal_semaphore_t sem);
```

---

## GPU Management API (`mvgal_gpu.h`)

### Enumeration

```c
int32_t       mvgal_gpu_get_count(void);
mvgal_error_t mvgal_gpu_enumerate(mvgal_gpu_descriptor_t *descriptors, uint32_t *count);
mvgal_error_t mvgal_gpu_get_descriptor(int32_t index, mvgal_gpu_descriptor_t *desc);
```

### Discovery

```c
mvgal_gpu_t mvgal_gpu_find_by_pci(uint16_t vendor_id, uint16_t device_id);
mvgal_gpu_t mvgal_gpu_find_by_node(const char *drm_node);
mvgal_gpu_t mvgal_gpu_find_by_vendor(mvgal_vendor_t vendor);
mvgal_gpu_t mvgal_gpu_select_best(const mvgal_gpu_selection_criteria_t *criteria);
mvgal_gpu_t mvgal_gpu_get_primary(void);
```

### Control

```c
mvgal_error_t mvgal_gpu_enable(int32_t index, bool enabled);
bool          mvgal_gpu_is_enabled(int32_t index);
mvgal_error_t mvgal_gpu_enable_all(void);
mvgal_error_t mvgal_gpu_disable_all(void);
```

### Capabilities

```c
bool          mvgal_gpu_has_feature(mvgal_gpu_t gpu, mvgal_feature_flags_t feature);
bool          mvgal_gpu_has_api(mvgal_gpu_t gpu, mvgal_api_type_t api);
mvgal_error_t mvgal_gpu_get_memory_stats(mvgal_gpu_t gpu, uint64_t *total, uint64_t *free);
float         mvgal_gpu_get_utilization(mvgal_gpu_t gpu);
float         mvgal_gpu_get_temperature(mvgal_gpu_t gpu);
```

### Health Monitoring

```c
mvgal_error_t          mvgal_gpu_get_health_status(mvgal_gpu_t gpu, mvgal_gpu_health_status_t *status);
mvgal_gpu_health_level_t mvgal_gpu_get_health_level(mvgal_gpu_t gpu);
bool                   mvgal_gpu_all_healthy(void);
mvgal_error_t          mvgal_gpu_get_health_thresholds(mvgal_gpu_health_thresholds_t *thresholds);
mvgal_error_t          mvgal_gpu_set_health_thresholds(const mvgal_gpu_health_thresholds_t *thresholds);
mvgal_error_t          mvgal_gpu_register_health_callback(mvgal_gpu_health_callback_t cb, void *user_data);
void                   mvgal_gpu_unregister_health_callback(mvgal_gpu_health_callback_t cb);
mvgal_error_t          mvgal_gpu_enable_health_monitoring(bool enable);
```

**Default health thresholds:**

| Metric | Warning | Critical |
|--------|---------|----------|
| Temperature | 80 °C | 95 °C |
| Utilization | 80 % | 95 % |
| Memory usage | 85 % | 95 % |

### Logical Device

```c
mvgal_error_t mvgal_device_create(const mvgal_gpu_t *gpus, uint32_t count,
                                   mvgal_logical_device_t *device);
void          mvgal_device_destroy(mvgal_logical_device_t device);
mvgal_error_t mvgal_device_get_descriptor(mvgal_logical_device_t device,
                                           mvgal_logical_device_descriptor_t *desc);
```

---

## Memory Management API (`mvgal_memory.h`)

### Allocation

```c
mvgal_error_t mvgal_memory_allocate(mvgal_context_t ctx,
                                     const mvgal_memory_alloc_info_t *info,
                                     mvgal_buffer_t *buffer);
mvgal_error_t mvgal_memory_allocate_simple(mvgal_context_t ctx, size_t size,
                                            mvgal_memory_flags_t flags,
                                            mvgal_buffer_t *buffer);
void          mvgal_memory_free(mvgal_buffer_t buffer);
mvgal_error_t mvgal_memory_get_descriptor(mvgal_buffer_t buffer,
                                           mvgal_memory_descriptor_t *desc);
```

### CPU Access

```c
mvgal_error_t mvgal_memory_map(mvgal_buffer_t buffer, void **ptr);
void          mvgal_memory_unmap(mvgal_buffer_t buffer);
bool          mvgal_memory_is_mapped(mvgal_buffer_t buffer);
void         *mvgal_memory_get_pointer(mvgal_buffer_t buffer);
mvgal_error_t mvgal_memory_write(mvgal_buffer_t buffer, uint64_t offset,
                                  const void *data, size_t size);
mvgal_error_t mvgal_memory_read(mvgal_buffer_t buffer, uint64_t offset,
                                 void *data, size_t size);
```

### GPU Transfers

```c
mvgal_error_t mvgal_memory_copy(mvgal_context_t ctx,
                                 const mvgal_memory_copy_region_t *region);
mvgal_error_t mvgal_memory_copy_gpu(mvgal_context_t ctx,
                                     mvgal_buffer_t src, uint32_t src_gpu,
                                     mvgal_buffer_t dst, uint32_t dst_gpu,
                                     size_t size);
```

### DMA-BUF

```c
mvgal_error_t mvgal_memory_export_dmabuf(mvgal_buffer_t buffer, int *fd);
mvgal_error_t mvgal_memory_import_dmabuf(mvgal_context_t ctx, int fd,
                                          size_t size, mvgal_buffer_t *buffer);
```

### Synchronization

```c
mvgal_error_t mvgal_memory_flush(mvgal_buffer_t buffer);
mvgal_error_t mvgal_memory_invalidate(mvgal_buffer_t buffer);
mvgal_error_t mvgal_memory_sync(mvgal_buffer_t buffer, uint32_t gpu_mask);
```

### Advanced

```c
mvgal_error_t mvgal_memory_replicate(mvgal_buffer_t buffer, uint32_t gpu_mask);
uint64_t      mvgal_memory_get_gpu_address(mvgal_buffer_t buffer, uint32_t gpu_index);
bool          mvgal_memory_is_accessible(mvgal_buffer_t buffer, uint32_t gpu_index);
mvgal_error_t mvgal_memory_create_shared(mvgal_context_t ctx, size_t size,
                                          uint32_t gpu_mask, mvgal_buffer_t *buffer);
mvgal_error_t mvgal_memory_get_stats(mvgal_context_t ctx, mvgal_memory_stats_t *stats);
```

---

## Power Management API (`mvgal_power.h`)

```c
mvgal_error_t mvgal_power_get_state(mvgal_gpu_index_t gpu, mvgal_power_state_t *state);
mvgal_error_t mvgal_power_get_temperature(mvgal_gpu_index_t gpu, int32_t *temperature_c);
mvgal_error_t mvgal_power_get_metrics(mvgal_gpu_index_t gpu, mvgal_power_metrics_t *metrics);
```

---

## P2P DMA API (`mvgal_p2p_dma.h`)

```c
mvgal_error_t mvgal_p2p_transfer(mvgal_p2p_context_t ctx, const mvgal_p2p_transfer_info_t *info);
mvgal_error_t mvgal_p2p_get_caps(mvgal_gpu_index_t src, mvgal_gpu_index_t dst, mvgal_p2p_caps_t *caps);
```

---

## Scheduler API (`mvgal_scheduler.h`)

### Workload Submission

```c
mvgal_error_t mvgal_workload_submit(mvgal_context_t ctx,
                                     const mvgal_workload_submit_info_t *info,
                                     mvgal_workload_t *workload);
mvgal_error_t mvgal_workload_submit_with_callback(mvgal_context_t ctx,
                                                   const mvgal_workload_submit_info_t *info,
                                                   mvgal_workload_callback_t callback,
                                                   void *user_data,
                                                   mvgal_workload_t *workload);
```

### Workload Control

```c
mvgal_error_t mvgal_workload_wait(mvgal_workload_t workload, uint64_t timeout_ns);
bool          mvgal_workload_is_completed(mvgal_workload_t workload);
mvgal_error_t mvgal_workload_get_result(mvgal_workload_t workload);
mvgal_error_t mvgal_workload_get_descriptor(mvgal_workload_t workload,
                                             mvgal_workload_descriptor_t *desc);
mvgal_error_t mvgal_workload_cancel(mvgal_workload_t workload);
void          mvgal_workload_destroy(mvgal_workload_t workload);
mvgal_error_t mvgal_workload_set_priority(mvgal_workload_t workload, uint32_t priority);
mvgal_error_t mvgal_workload_assign_gpus(mvgal_workload_t workload, uint32_t gpu_mask);
```

### Scheduler Configuration

```c
mvgal_error_t mvgal_scheduler_configure(const mvgal_scheduler_config_t *config);
mvgal_error_t mvgal_scheduler_get_config(mvgal_scheduler_config_t *config);
mvgal_error_t mvgal_scheduler_get_stats(mvgal_scheduler_stats_t *stats);
mvgal_error_t mvgal_scheduler_reset_stats(void);
mvgal_error_t mvgal_scheduler_set_strategy(mvgal_distribution_strategy_t strategy);
mvgal_distribution_strategy_t mvgal_scheduler_get_strategy(void);
mvgal_error_t mvgal_scheduler_set_gpu_priority(uint32_t gpu_index, int32_t priority);
int32_t       mvgal_scheduler_get_gpu_priority(uint32_t gpu_index);
mvgal_error_t mvgal_scheduler_pause(void);
mvgal_error_t mvgal_scheduler_resume(void);
bool          mvgal_scheduler_is_paused(void);
```

### Distribution Functions

```c
mvgal_error_t mvgal_distribute_afr(mvgal_workload_t workload, uint32_t frame_number,
                                    uint32_t *gpu_index);
mvgal_error_t mvgal_distribute_sfr(mvgal_workload_t workload, float split_ratio,
                                    bool horizontal, uint32_t *gpu_indices);
mvgal_error_t mvgal_distribute_task(mvgal_workload_t workload, uint32_t *gpu_index);
```

---

## Execution Engine API (`mvgal_execution.h`)

```c
// Begin a new frame session
mvgal_error_t mvgal_execution_begin_frame(const mvgal_execution_frame_begin_info_t *info,
                                           uint64_t *frame_id);

// Plan and submit a workload within a frame
mvgal_error_t mvgal_execution_submit(const mvgal_execution_submit_info_t *info,
                                      mvgal_execution_plan_t *plan);

// Present a completed frame
mvgal_error_t mvgal_execution_present(uint64_t frame_id);

// Get frame statistics
mvgal_error_t mvgal_execution_get_frame_stats(uint64_t frame_id,
                                               mvgal_execution_frame_stats_t *stats);

// Plan a cross-GPU memory migration
mvgal_error_t mvgal_execution_migrate_memory(const mvgal_execution_migration_info_t *info,
                                              mvgal_execution_migration_result_t *result);

// Generate a Steam/Proton scheduling profile
mvgal_error_t mvgal_execution_get_steam_profile(const mvgal_steam_profile_request_t *request,
                                                  mvgal_steam_profile_t *profile);
```

---

## IPC API (`mvgal_ipc.h`)

```c
// Server
mvgal_error_t mvgal_ipc_server_init(const char *socket_path);
void          mvgal_ipc_server_cleanup(void);
mvgal_error_t mvgal_ipc_server_start(void);
void          mvgal_ipc_server_stop(void);

// Client
mvgal_error_t mvgal_ipc_client_connect(const char *socket_path, int *fd_out);
void          mvgal_ipc_client_disconnect(int fd);
mvgal_error_t mvgal_ipc_send(int fd, mvgal_ipc_message_type_t type,
                             const void *payload, size_t payload_size,
                             uint64_t request_id);
mvgal_error_t mvgal_ipc_receive(int fd, mvgal_ipc_message_type_t *type_out,
                                void *payload_buf, size_t payload_buf_size,
                                size_t *payload_size_out,
                                uint64_t *request_id_out);
```

Every client call takes the connected file descriptor as its first argument, and `send`/`receive` both carry a `request_id` so a caller can match responses to requests. The wire header (`src/userspace/daemon/ipc.c`) is `MVGAL_IPC_MAGIC 0x4D564741` ("MVGA"), version `1`, then `message_type`, `payload_size`, and `request_id`.

**IPC Message Types:**

| Type | Value | Description |
|------|-------|-------------|
| `MVGAL_IPC_MSG_PING` | 0 | Keepalive ping |
| `MVGAL_IPC_MSG_PONG` | 1 | Keepalive response |
| `MVGAL_IPC_MSG_GPU_ENUMERATE` | 2 | Request GPU list |
| `MVGAL_IPC_MSG_GPU_LIST` | 3 | GPU list response |
| `MVGAL_IPC_MSG_WORKLOAD_SUBMIT` | 4 | Submit workload |
| `MVGAL_IPC_MSG_WORKLOAD_RESULT` | 5 | Workload result |
| `MVGAL_IPC_MSG_MEMORY_ALLOCATE` | 6 | Allocate memory |
| `MVGAL_IPC_MSG_MEMORY_FREE` | 7 | Free memory |
| `MVGAL_IPC_MSG_CONFIG_GET` | 8 | Get configuration |
| `MVGAL_IPC_MSG_CONFIG_SET` | 9 | Set configuration |
| `MVGAL_IPC_MSG_ERROR` | 10 | Error response |

---

## IOCTL Interface (`mvgal_uapi.h`)

MVGAL exposes a character device at `/dev/mvgal0`. Magic number: `'M'` (0x4D).

**13 ioctls are declared; 9 are implemented.** The four DMA-BUF and cross-vendor entries are reserved for future work — they are defined in the header but have no `case` in the `kernel/mvgal_core.c` dispatcher, so they fall through to `default: return -EINVAL`.

| IOCTL | Code | Direction | Implemented | Description |
|-------|:----:|:---------:|:-----------:|-------------|
| `MVGAL_IOC_QUERY_VERSION` | `0x00` | Read | ✅ | Query UAPI version |
| `MVGAL_IOC_GET_GPU_COUNT` | `0x01` | Read | ✅ | Get number of GPUs |
| `MVGAL_IOC_GET_GPU_INFO` | `0x02` | Write-Read | ✅ | Get GPU info by index |
| `MVGAL_IOC_ENABLE` | `0x03` | None | ✅ | Enable MVGAL |
| `MVGAL_IOC_DISABLE` | `0x04` | None | ✅ | Disable MVGAL |
| `MVGAL_IOC_GET_STATS` | `0x05` | Read | ✅ | Get driver statistics |
| `MVGAL_IOC_GET_CAPS` | `0x06` | Read | ✅ | Get capabilities |
| `MVGAL_IOC_RESCAN` | `0x07` | None | ✅ | Trigger GPU rescan |
| `MVGAL_IOC_NTSYNC_QUERY` | `0x20` | Read | ✅ | Query NTSYNC support |
| `MVGAL_IOC_EXPORT_DMABUF` | `0x10` | Write-Read | ❌ | Export DMA-BUF (reserved) |
| `MVGAL_IOC_IMPORT_DMABUF` | `0x11` | Write-Read | ❌ | Import DMA-BUF (reserved) |
| `MVGAL_IOC_ALLOC_CROSS_VENDOR` | `0x12` | Write-Read | ❌ | Cross-vendor allocation (reserved) |
| `MVGAL_IOC_FREE_CROSS_VENDOR` | `0x13` | Write | ❌ | Free cross-vendor alloc (reserved) |

`MVGAL_IOC_QUERY_VERSION` reports its feature set through `feature_flags`, which includes `MVGAL_UAPI_FEATURE_FUTURE_DMABUF` and `MVGAL_UAPI_FEATURE_FUTURE_SUBMISSION` — the flags that mark the unimplemented entries above.

### DRM render ioctls

Separately, `kernel/mvgal_core.c` registers a DRM driver with its own table of **10** render ioctls, all `DRM_RENDER_ALLOW`:

`MVGAL_QUERY_DEVICES` · `MVGAL_QUERY_CAPABILITIES` · `MVGAL_SUBMIT_WORKLOAD` · `MVGAL_ALLOC_MEMORY` · `MVGAL_FREE_MEMORY` · `MVGAL_IMPORT_DMABUF` · `MVGAL_EXPORT_DMABUF` · `MVGAL_WAIT_FENCE` · `MVGAL_SIGNAL_FENCE` · `MVGAL_SET_GPU_AFFINITY`

The device registers with `driver_features = DRIVER_RENDER | DRIVER_HAVE_IRQ | DRIVER_GEM` at major/minor `0.2`. Registration is minimal and logical-only — GPU discovery runs in userspace.

---

## D-Bus API

| Property | Value |
|----------|-------|
| Bus name | `org.mvgal.MVGAL` |
| Object path | `/org/mvgal/daemon` |
| Interface | `org.mvgal.MVGAL` |

**Methods (6):**

| Method | In | Out | Description |
|--------|----|-----|-------------|
| `SetSchedulingMode` | `s` | `` | Set the scheduling strategy |
| `GetSchedulingMode` | `` | `s` | Get the scheduling strategy |
| `SetGPUEnabled` | `ub` | `b` | Enable or disable a GPU by index |
| `GetGPUEnabled` | `u` | `b` | Query whether a GPU is enabled |
| `TriggerRescan` | `` | `` | Re-enumerate GPUs |
| `GetStatistics` | `` | `a{sv}` | Get driver statistics |

**Signals (3):** `GPUHotplug` (gpu_index, added) · `TemperatureWarning` (gpu_index, temperature) · `PowerLimitReached` (gpu_index)

There are **no `SD_BUS_PROPERTY` entries** — the vtable contains only the six methods above, so clients should call the getter methods rather than reading properties. `GetStatistics` returns a dictionary (`a{sv}`), not a fixed struct.

> **Security (introduced in v0.7.8):** the D-Bus policy at `/etc/dbus-1/system.d/org.mvgal.MVGAL.conf` restricts `org.mvgal.MVGAL` to root and the `mvgal` group — all other users are denied. An older `data/mvgal-dbus.conf` declaring `com.mvgal.Daemon` was stale and is explicitly removed by the package scriptlet.

---

## Vulkan

MVGAL ships **no Vulkan extensions.** The interception layer and the ICD implement the standard Vulkan API and are selected by the loader, not by a `VK_MVGAL_*` extension.

The layer is a standard global layer: `VK_LAYER_MVGAL`, `api_version 1.4.0`, installed to `/usr/share/vulkan/implicit_layer.d/VK_LAYER_MVGAL.json`, enabled with `MVGAL_VULKAN_ENABLE=1` and disabled with `MVGAL_VULKAN_DISABLE=1`. It intercepts 38 standard entry points including `vkQueueSubmit`, and notably does **not** intercept `vkQueuePresentKHR`, `vkAcquireNextImageKHR`, or `vkWaitForFences`. See [STEAM_INTEGRATION](STEAM_INTEGRATION.md) for the full list and the frame-pacing implications.

> Earlier revisions of this document listed six `VK_MVGAL_*` extensions. No such symbol exists anywhere in the source tree — it was a documentation error, and the table has been removed rather than corrected.

---

## Logging API (`mvgal_log.h`)

```c
void mvgal_log_init(mvgal_log_level_t level, mvgal_log_callback_t callback, void *user_data);
void mvgal_log_shutdown(void);
void mvgal_log_set_level(mvgal_log_level_t level);
mvgal_log_level_t mvgal_log_get_level(void);
void mvgal_log_register_callback(mvgal_log_callback_t callback, void *user_data);
void mvgal_log_unregister_callback(mvgal_log_callback_t callback);
void mvgal_log_error(const char *fmt, ...);
void mvgal_log_warn(const char *fmt, ...);
void mvgal_log_info(const char *fmt, ...);
void mvgal_log_debug(const char *fmt, ...);
void mvgal_log_trace(const char *fmt, ...);
bool mvgal_log_enabled(mvgal_log_level_t level);
void mvgal_log_enable_file(const char *path);
void mvgal_log_disable_file(void);
void mvgal_log_enable_syslog(const char *ident);
void mvgal_log_disable_syslog(void);
void mvgal_log_enable_colors(bool enable);
void mvgal_log_flush(void);
```

**Log levels:** `MVGAL_LOG_LEVEL_ERROR=0`, `WARN=1`, `INFO=2`, `DEBUG=3`, `TRACE=4`

**Convenience macros:** `MVGAL_LOG_ERROR(fmt, ...)`, `MVGAL_LOG_WARN`, `MVGAL_LOG_INFO`, `MVGAL_LOG_DEBUG`, `MVGAL_LOG_TRACE`

---

## Configuration API (`mvgal_config.h`)

```c
mvgal_error_t mvgal_config_init(void);
void          mvgal_config_shutdown(void);
mvgal_error_t mvgal_config_load(const char *path);
mvgal_error_t mvgal_config_load_string(const char *config_string);
mvgal_error_t mvgal_config_save(const char *path);
mvgal_error_t mvgal_config_get(mvgal_config_t *config);
mvgal_error_t mvgal_config_set(const mvgal_config_t *config);
mvgal_error_t mvgal_config_get_by_name(const char *name, mvgal_config_value_t *value);
mvgal_error_t mvgal_config_set_by_name(const char *name, const mvgal_config_value_t *value);
mvgal_error_t mvgal_config_reset(void);
mvgal_error_t mvgal_config_validate(const mvgal_config_t *config);
const char   *mvgal_config_get_default_path(void);
void          mvgal_config_print(void);
```

---

## Error Codes

| Code | Value | Description |
|------|-------|-------------|
| `MVGAL_SUCCESS` | 0 | Operation succeeded |
| `MVGAL_ERROR_INVALID_ARGUMENT` | 1 | Invalid argument passed |
| `MVGAL_ERROR_OUT_OF_MEMORY` | 2 | Memory allocation failed |
| `MVGAL_ERROR_NOT_FOUND` | 3 | Resource not found |
| `MVGAL_ERROR_TIMEOUT` | 4 | Operation timed out |
| `MVGAL_ERROR_UNSUPPORTED` | 5 | Operation not supported |
| `MVGAL_ERROR_BUSY` | 6 | Resource is busy |
| `MVGAL_ERROR_DEVICE_LOST` | 7 | GPU device lost |
| `MVGAL_ERROR_CONTEXT_LOST` | 8 | Context lost |
| `MVGAL_ERROR_NOT_INITIALIZED` | 9 | MVGAL not initialized |
| `MVGAL_ERROR_ALREADY_INITIALIZED` | 10 | Already initialized |
| `MVGAL_ERROR_INCOMPATIBLE` | 11 | Incompatible GPUs |
| `MVGAL_ERROR_GPU_NOT_FOUND` | 12 | No GPU found |
| `MVGAL_ERROR_NOT_SUPPORTED` | 13 | Feature not supported |
| `MVGAL_ERROR_DRIVER` | 14 | Driver error |
| `MVGAL_ERROR_MEMORY` | 15 | Memory subsystem error |
| `MVGAL_ERROR_INITIALIZATION` | 16 | Initialization failed |
| `MVGAL_ERROR_IPC` | 17 | IPC error |
| `MVGAL_ERROR_NO_GPUS` | 18 | No GPUs available |
| `MVGAL_ERROR_UNKNOWN` | 19 | Unknown error |
| `MVGAL_ERROR_INTERRUPTED` | 20 | Operation interrupted |
| `MVGAL_ERROR_SCHEDULER` | 21 | Scheduler error |
| `MVGAL_ERROR_CANCELLED` | 22 | Operation cancelled |
| `MVGAL_ERROR_QUEUE_FULL` | 23 | Queue or buffer at capacity |

> **Note on 5 vs 13.** `MVGAL_ERROR_UNSUPPORTED` (5) and `MVGAL_ERROR_NOT_SUPPORTED` (13) are distinct codes with near-identical meanings, and both are defined at `include/mvgal/mvgal_types.h:94-117`. This is a genuine quirk of the source, not a transcription error in this table — code that compares against one will not match the other. It is left as-is rather than silently renumbered, because renumbering would break ABI compatibility.

---

## Type Reference

### `mvgal_vendor_t`

```c
MVGAL_VENDOR_UNKNOWN       = 0
MVGAL_VENDOR_AMD           = 0x1002
MVGAL_VENDOR_NVIDIA        = 0x10DE
MVGAL_VENDOR_INTEL         = 0x8086
MVGAL_VENDOR_MOORE_THREADS = 0x1ED5
MVGAL_VENDOR_QUALCOMM      = 0x5143
MVGAL_VENDOR_ARM           = 0x13B5
MVGAL_VENDOR_BROADCOM      = 0x14E4
```

### `mvgal_distribution_strategy_t`

```c
MVGAL_STRATEGY_ROUND_ROBIN     = 0
MVGAL_STRATEGY_AFR             = 1
MVGAL_STRATEGY_SFR             = 2
MVGAL_STRATEGY_AUTO            = 3
MVGAL_STRATEGY_COMPUTE_OFFLOAD = 4
MVGAL_STRATEGY_HYBRID          = 5
MVGAL_STRATEGY_SINGLE_GPU      = 6
MVGAL_STRATEGY_TASK            = 7
MVGAL_STRATEGY_AI_DRIVEN       = 8
MVGAL_STRATEGY_RLD             = 9
MVGAL_STRATEGY_REP             = 10
MVGAL_STRATEGY_PPL             = 11
MVGAL_STRATEGY_CUSTOM          = 100
```

### `mvgal_api_type_t` (API flags)

```c
MVGAL_API_VULKAN   MVGAL_API_OPENGL   MVGAL_API_OPENCL
MVGAL_API_CUDA     MVGAL_API_D3D11    MVGAL_API_D3D12
MVGAL_API_METAL    MVGAL_API_WEBGPU   MVGAL_API_VA_API
```

### `mvgal_feature_flags_t`

```c
MVGAL_FEATURE_DMA_BUF         MVGAL_FEATURE_CROSS_VENDOR
MVGAL_FEATURE_UNIFIED_MEMORY  MVGAL_FEATURE_P2P_TRANSFER
MVGAL_FEATURE_GRAPHICS        MVGAL_FEATURE_COMPUTE
MVGAL_FEATURE_VIDEO_DECODE    MVGAL_FEATURE_VIDEO_ENCODE
MVGAL_FEATURE_AI_ACCEL        MVGAL_FEATURE_RAY_TRACING
```

---

## Rust FFI Reference

Three Rust crates export C-ABI functions for the C++ daemon. **The directory names and the Cargo package names differ:** `safe/fence_manager/` is the `mvgal_fence` package, `safe/memory_safety/` is `mvgal_memory_safety`, and `safe/capability_model/` is `mvgal_capability`. `runtime/safe/lib.rs` re-exports them under their directory names as modules, which is why the two naming schemes appear to collide.

Every entry point is `#[no_mangle] extern "C"` and catches panics at the boundary, so no unwind can cross into C.

### `mvgal_fence` — `safe/fence_manager/`

Handle is `MvgalFenceHandle` = `u64`.

```rust
pub type MvgalFenceHandle = u64;

pub extern "C" fn mvgal_fence_create(gpu_index: u32) -> MvgalFenceHandle;
pub extern "C" fn mvgal_fence_submit(handle: MvgalFenceHandle) -> i32;
pub extern "C" fn mvgal_fence_signal(handle: MvgalFenceHandle) -> i32;
pub extern "C" fn mvgal_fence_state(handle: MvgalFenceHandle) -> i32;
pub extern "C" fn mvgal_fence_reset(handle: MvgalFenceHandle) -> i32;
pub extern "C" fn mvgal_fence_destroy(handle: MvgalFenceHandle) -> i32;
pub extern "C" fn mvgal_fence_get_last_error() -> i32;
```

`mvgal_fence_create` is the only function that returns a handle; everything else takes one and returns an `i32` status. The handle must be freed with `mvgal_fence_destroy`.

### `mvgal_memory_safety` — `safe/memory_safety/`

Handle is `MvgalAllocHandle` = `u64`.

```rust
pub type MvgalAllocHandle = u64;

pub extern "C" fn mvgal_mem_track(size_bytes: u64, placement: u32, gpu_index: u32) -> MvgalAllocHandle;
pub extern "C" fn mvgal_mem_retain(handle: MvgalAllocHandle) -> i32;
pub extern "C" fn mvgal_mem_release(handle: MvgalAllocHandle) -> i32;
pub extern "C" fn mvgal_mem_set_dmabuf(handle: MvgalAllocHandle, fd: i32) -> i32;
pub extern "C" fn mvgal_mem_size(handle: MvgalAllocHandle) -> u64;
pub extern "C" fn mvgal_mem_placement(handle: MvgalAllocHandle) -> i32;
pub extern "C" fn mvgal_mem_total_system_bytes() -> u64;
pub extern "C" fn mvgal_mem_total_gpu_bytes() -> u64;
pub extern "C" fn mvgal_mem_get_last_error() -> i32;
```

`mvgal_mem_track` takes both a `placement` and a `gpu_index`.

### `mvgal_capability` — `safe/capability_model/`

Handle is `MvgalCapHandle` = `*mut AggregateCapability` — a **pointer**, not an integer. `pub struct GpuCapability` is defined at `safe/capability_model/src/lib.rs:37`.

```rust
pub type MvgalCapHandle = *mut AggregateCapability;

pub unsafe extern "C" fn mvgal_cap_compute(gpus: *const GpuCapability, count: u32) -> MvgalCapHandle;
pub unsafe extern "C" fn mvgal_cap_free(handle: MvgalCapHandle);
pub unsafe extern "C" fn mvgal_cap_total_vram(handle: MvgalCapHandle) -> u64;
pub unsafe extern "C" fn mvgal_cap_tier(handle: MvgalCapHandle) -> i32;
pub unsafe extern "C" fn mvgal_cap_to_json(handle: MvgalCapHandle, buf: *mut c_char, buf_len: usize) -> i32;
pub extern "C" fn mvgal_cap_get_last_error() -> i32;
```

Notes on the contract: `mvgal_cap_compute` returns a valid **empty** aggregate when `gpus` is null or `count` is 0 — it must still be freed. `mvgal_cap_to_json` writes into a caller-supplied buffer and truncates rather than allocating, returning `-1` for a null handle, null buffer, or zero length. The `capability_model` functions are `unsafe extern` because the caller guarantees the pointer validity; the other two crates are safe.

### `mvgal_ffi_tests` — `safe/ffi_tests/`

A fourth crate exercising the FFI boundary. It imports the packages under their directory-name aliases:

```rust
use mvgal_capability as capability_model;
use mvgal_fence as fence_manager;
use mvgal_memory_safety as memory_safety;
```

---

## Documentation Corrections in This Revision

The following claims appeared in earlier revisions of this document and have no counterpart in the source. They are recorded here so the removal is traceable rather than silent:

| Removed claim | Reality |
|---------------|---------|
| Nine-method D-Bus table (`GetGPUCount`, `GetPowerState`, `Ping`, …) | Six methods, listed above; the signals were correct |
| `VK_MVGAL_*` Vulkan extensions | No such symbol exists; the layer implements standard Vulkan |
| IPC client calls without `fd` or `request_id` | Both are required parameters |
| "12 ioctls" | 13 declared, 9 implemented, plus 10 separate DRM ioctls |
| "26 headers" (in [MOC](MOC.md)) | 29 headers; this table listed 25 |
| Rust functions returning `void` from mutating calls | They return `i32` status; `mvgal_mem_track` also takes a `gpu_index` |
| `GpuCapability`-based `mvgal_cap_to_json` returning `const char *` | Takes a caller-supplied buffer and returns `i32` |

---

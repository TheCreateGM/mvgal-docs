---
tags: [mvgal, strategies, reference]
aliases: [Scheduling Strategies, Strategies]
mvgal_version: "0.7.16"
mvgal_verified: 2026-09-30
mvgal_role: reference
mvgal_order: 10
---

# MVGAL Scheduling Strategy Identifiers

> Source metadata is **0.7.16**; the source changelog documents releases through **0.7.16**. These are API/configuration identifiers. A declared strategy does not establish that a supported backend can submit work across GPUs.

## Public C identifiers

The enum in `include/mvgal/mvgal_types.h` declares:

| Identifier | Enum value | Header description |
|------------|:----------:|--------------------|
| `MVGAL_STRATEGY_ROUND_ROBIN` | 0 | Round-robin distribution |
| `MVGAL_STRATEGY_AFR` | 1 | Alternate Frame Rendering |
| `MVGAL_STRATEGY_SFR` | 2 | Split Frame Rendering |
| `MVGAL_STRATEGY_AUTO` | 3 | Auto-detect best strategy |
| `MVGAL_STRATEGY_COMPUTE_OFFLOAD` | 4 | Compute offloading |
| `MVGAL_STRATEGY_HYBRID` | 5 | Hybrid adaptive strategy |
| `MVGAL_STRATEGY_SINGLE_GPU` | 6 | Use single fastest GPU |
| `MVGAL_STRATEGY_TASK` | 7 | Task-based distribution |
| `MVGAL_STRATEGY_AI_DRIVEN` | 8 | AI/ML-driven scheduling strategy |
| `MVGAL_STRATEGY_RLD` | 9 | Radeon LD wrapper strategy |
| `MVGAL_STRATEGY_REP` | 10 | Reproducible build strategy |
| `MVGAL_STRATEGY_PPL` | 11 | AMD Performance Primitives strategy |
| `MVGAL_STRATEGY_CUSTOM` | 100 | Custom strategy (user-defined) |

The enum labels RLD, REP, and PPL do not mean “render layer distribution,” “replication mode,” or “pipeline parallelism” in the current public header. Older versions of this guide expanded those abbreviations incorrectly.

## CLI configuration

The main CLI documents these strategy arguments in `tools/mvgal.c`: `round_robin`, `afr`, `sfr`, `single`/`single_gpu`, `hybrid`, `task`, `compute_offload`, `auto`, and `custom`. Check `mvgal --help` and `mvgal-config --help` on the installed version for accepted forms.

## Custom splitters

`MVGAL_STRATEGY_CUSTOM` is a public identifier with a registration API behind it,
but the two halves are not yet connected. A splitter descriptor
(`mvgal_workload_splitter_t`) carries three callbacks — `analyze`, `split` and
`merge` — plus an opaque `user_data`:

```c
bool (*analyze)(mvgal_workload_t workload, const mvgal_workload_submit_info_t *info,
                uint32_t gpu_count, const uint32_t *gpu_indices,
                void *split_info, void *user_data);
bool (*split)(mvgal_workload_t workload, void *split_info, uint32_t part_count,
              mvgal_workload_t *parts, void *user_data);
bool (*merge)(mvgal_workload_t workload, uint32_t part_count,
              mvgal_workload_t *parts, void *user_data);
```

`mvgal_register_custom_splitter()` and `mvgal_unregister_custom_splitter()` both
work as of v0.7.16. The scheduler validates the descriptor, rejects any of the
three callbacks being `NULL`, and retains a copy. Removal matches on all four
fields together, so splitters that share callbacks but differ in `user_data` can
be released independently.

> [!note] Registration does not deduplicate
> Registering the same descriptor twice stores it twice and reports
> `MVGAL_SUCCESS` both times; there is no lookup on the register path. Release
> removes one entry per call, so `N` registrations of one descriptor need `N`
> releases, and a mismatch on a later call surfaces as
> `MVGAL_ERROR_NOT_FOUND`. If you register in a reinitialisation path, release
> on the way out rather than relying on the registry to reconcile it. The
> descriptor is a POD, so compare the four fields yourself if you need
> idempotence.

> [!warning] The `custom` strategy still cannot be selected
> `mvgal_scheduler_apply_strategy()` returns `MVGAL_ERROR_NOT_SUPPORTED` for
> `MVGAL_STRATEGY_CUSTOM`, and no code path reads the registry to apply a
> registered splitter to a dequeued workload. `merge()` is never invoked. Until
> the task tree contract below is settled, registering a splitter has no effect
> on scheduling.

The missing contract is not a bug with a known shape. A splitter's `split()`
callback returns an array of `mvgal_workload_t` sub-workload handles, and there
is currently no public API for a callback to mint one without re-entering
`mvgal_workload_submit()`; there is no defined owner of the returned parts, no
trigger for `merge()`, and no defined propagation of a failed child to the
parent. These are design decisions, so none were invented. One structural fact
does reduce the risk: `mvgal_scheduler_apply_strategy()` runs on the scheduler
thread *after* the workload has been dequeued, so a splitter calling
`mvgal_workload_submit()` enqueues children rather than recursing synchronously.

See [[docs/API|API Reference]] § Custom Splitters for the registration calls.

## Operational limits

The v0.7.12 source changelog records that vendor `submit_cs` functions previously returned success without dispatching work. Those functions now return `-EOPNOTSUPP`, and the scheduler no longer marks such work complete. Kernel submission is not advertised as a supported runtime capability. Treat strategies as configuration/API surface until a real workload and device capability test confirms the selected path.

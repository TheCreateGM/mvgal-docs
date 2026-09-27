---
tags: [mvgal, strategies, reference]
aliases: [Scheduling Strategies, Strategies]
---

# MVGAL Scheduling Strategy Identifiers

> Source metadata is **0.7.13**; the source changelog documents releases through **0.7.12**. These are API/configuration identifiers. A declared strategy does not establish that a supported backend can submit work across GPUs.

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

## Operational limits

The v0.7.12 source changelog records that vendor `submit_cs` functions previously returned success without dispatching work. Those functions now return `-EOPNOTSUPP`, and the scheduler no longer marks such work complete. Kernel submission is not advertised as a supported runtime capability. Treat strategies as configuration/API surface until a real workload and device capability test confirms the selected path.

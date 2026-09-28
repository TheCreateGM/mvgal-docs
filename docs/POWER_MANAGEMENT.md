---
tags: [mvgal, power, reference]
aliases: [Power Management, Power]
mvgal_version: "0.7.14"
mvgal_verified: 2026-09-28
mvgal_role: reference
mvgal_order: 11
---

# MVGAL Power Management

> Source metadata is **0.7.14**; the source changelog documents releases through **0.7.14**. Power operations are vendor- and capability-dependent. Do not assume that a compiled adapter can control clocks, power limits, or idle states.

## What the source provides

The repository contains power APIs and managers in `include/mvgal/mvgal_power.h`, `kernel/mvgal_power.c`, `runtime/daemon/power_manager.cpp`, and vendor adapter files under `kernel/vendors/`. Runtime capability probing determines which controls are reported. In 0.7.12 the changelog notes that DPM capability is no longer inferred from vendor family and requires the relevant sysfs node to exist. Operations without a verified backend report unsupported or record state without claiming that hardware changed.

## Inspect power and device status

Use the tools present in your installed package:

```bash
mvgal-info --help
mvgal-status --help
mvgal-config --help
mvgal-info
mvgal-status --once
```

`mvgal-config --help` lists configured power commands in builds that include them. Current source exposes selected commands such as `set-power-profile`, `set-power-curve`, and PSU configuration; valid options and hardware applicability are shown by that tool. There is no separate `mvgal-powercurve` target in the current tools CMake file.

System telemetry can also be inspected through the native driver's interfaces and tools. For NVIDIA, use the installed `nvidia-smi`; for AMD and Intel, consult the relevant DRM, hwmon, and sysfs nodes. Availability differs by driver and GPU.

## Idle gating

Source version 0.7.12 gates idle control on a measurable busy signal (`MVGAL_CAP_BUSY_PERCENT`). A GPU without that capability reports idle gating as unavailable and refuses to arm it. This avoids changing device state based on guessed utilization.

## Limitations

MVGAL does not claim universal dynamic voltage/frequency scaling, GPU parking, fan control, thermal policy, or power-curve support. Native drivers retain ownership of the hardware. Check the probed capability mask and the native driver's documentation before changing power settings.

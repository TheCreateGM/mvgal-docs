---
tags: [mvgal, power, reference]
aliases: [Power Management, Power]
mvgal_version: "0.7.46"
mvgal_verified: 2026-11-14
mvgal_role: reference
mvgal_order: 11
---

# MVGAL Power Management

> Source metadata is **0.7.46**; the source changelog documents releases through **0.7.46**. Power operations are vendor- and capability-dependent. Do not assume that a compiled adapter can control clocks, power limits, or idle states.

## What the source provides

Power management exists at three layers, but the control loops are **not fully wired to runtime triggers**:

1. **Kernel module** (`kernel/mvgal_power.c`, `kernel/mvgal_power.h`): per-GPU DVFS policy structures and a frequency-limit control function, thermal state tracking with a continuous throttle calculation, a power budget registry with PSU headroom configuration, and the idle gate. Initialized per GPU from `mvgal_device.c` (dvfs init, thermal init, budget register) and at module load from `mvgal_core.c`.
2. **Runtime daemon** (`runtime/daemon/power_manager.cpp`): a four-state idle machine (ACTIVE → SUSTAINED → IDLE → PARK), five-tier thermal classification, fan-curve interpolation and manual fan control, power-curve → clock-ceiling computation and PSU headroom tracking. Runs in the daemon main loop (`daemon.cpp` calls `processEvents()` each iteration).
3. **Userspace power library** (`src/userspace/power/`): `power_curve.c` (curve math, PSU efficiency table, per-vendor power-profile helpers) and `power_manager.c` (park/unpark, suspend/resume, thermal check, power monitor thread).

### Wiring status (read this first)

Honest state of each control path as of 0.7.46:

| Path | Status |
|------|--------|
| Daemon idle/thermal state machines | **Running** — driven by `processEvents()` in the daemon loop |
| Daemon fan curve / power curve / PSU APIs | **Implemented** — power curve, per-GPU power limit, and PSU keys are settable via the `mvgal` CLI (`set-power-curve`, `set-power-limit`, `psu-config`, `psu-headroom`), which persists them to `[power]` through the pkexec helper and reloads the daemon; fan curves remain in-process only (no CLI or D-Bus method) |
| Kernel DVFS/thermal periodic work handlers | **Armed but never queued** — `mvgal_dvfs_start()` / `mvgal_thermal_start()` have no callers outside tests, so the tick handlers never run |
| Kernel power control entry points (`mvgal_dvfs_set_mode`, `mvgal_set_freq_limit`, `mvgal_thermal_set_thresholds`, `mvgal_set_power_state`, `mvgal_power_budget_distribute`) | **No runtime caller** — no ioctl or sysfs write path reaches them; only KUnit tests call them |
| `[power]` section of `mvgal.conf` | **Wired** — `daemon.cpp` `applyPowerConfig()` parses the section into `PowerManager::setConfig()` / `setPsuConfig()` / `setPowerCurve()` at startup and on SIGHUP |
| D-Bus power interface | **Signal only** — `PowerLimitReached` is emitted; there are no power/fan/thermal methods |

### Telemetry and control return values

Since v0.7.46 the daemon reports what it actually has. When a GPU exposes neither an NVML handle nor a readable hwmon node, `readTemperature()`, `readPowerDraw()`, and `readFanSpeed()` report failure instead of a substitute value (they previously returned fabricated 50 °C, 100 W, and 0 RPM), and the caller keeps its last known reading. `writePowerLimit()`, `writeFanSpeed()`, and `writeFrequency()` return false when no vendor interface accepted the request, so callers no longer record a value the GPU never received. No fixed wattage is written on a power state change: NVML exposes no per-state power mode and no per-GPU TDP is probed, so the idle state machine records the transition without applying an invented power limit.

In 0.7.12 the changelog notes that DPM capability is no longer inferred from vendor family and requires the relevant sysfs node to exist. Operations without a verified backend report unsupported or record state without claiming that hardware changed.

### Power curves

- Kernel default curve: exactly three points (0% util → 30% limit / 40 °C, 50% → 70% / 70 °C, 100% → 100% / 85 °C), linear interpolation, no voltage column.
- Shipped `config/mvgal.conf` `[power] power_curve=`: five points, `0:30, 25:50, 50:70, 75:90, 100:100`.
- Named profiles: `[power] power_curve_profile = silent | balanced | performance | custom` (commented out in the shipped file). `daemon.cpp` `profileToPowerCurve()` maps a name to a preset point list — `silent`: 0:15, 25:25, 50:40, 75:55, 100:70; `balanced`: 0:30, 25:50, 50:70, 75:90, 100:100; `performance`: 0:50, 25:75, 50:90, 75:100, 100:100; `custom`: no preset, the explicit `power_curve` list applies. An explicit `power_curve` list wins over a profile; an unknown name warns and changes nothing. The curve only has an effect when power capping is enabled (`enable_power_capping = true` with `power_limit_watts > 0`) or PSU headroom tracking is active — see `PowerManager::applyPowerCurves()`.
- The public header defines an eight-value profile enum (`PERFORMANCE`, `BALANCED`, `POWERSAVER`, `AUTO`, `CUSTOM`, `ADAPTIVE`, `RENDERING`, `GAMING`). There is no `turbo` profile and no fixed "%TDP per profile" table — profile behavior is curve-driven.
- PSU capacity is a **user-provided** value (`psu_capacity_watts`, default 0 = unknown). MVGAL does not discover PSU capacity from hardware.

## Inspect power and device status

Use the tools present in your installed package:

```bash
mvgal-info --help
mvgal-status --help
mvgal-config --help
mvgal-info
mvgal-status --once
```

`mvgal-config --help` lists configured power commands in builds that include them. Since v0.7.46 the `mvgal` CLI itself exposes the power/PSU surface; valid options and hardware applicability are shown by `mvgal --help`. There is no separate `mvgal-powercurve` target in the current tools CMake file.

### Power and PSU CLI commands (v0.7.46)

| Command | Effect |
|---------|--------|
| `mvgal set-power-curve <profile>` | Persists `power.power_curve_profile` (`silent\|balanced\|performance\|custom`); reloads the daemon |
| `mvgal set-power-limit <watts>` | Persists `power.power_limit_watts` and sets `enable_power_capping` (0 disables capping); reloads the daemon |
| `mvgal psu-config <watts> <margin%>` | Persists `psu_capacity_watts` and `psu_safety_margin_percent` |
| `mvgal psu-headroom <on\|off>` | Persists `enable_psu_headroom` |

All four go through `pkexec /usr/lib/mvgal/mvgal-pkexec-helper.sh` — the helper's generic `set-config` action is restricted to keys `applyPowerConfig()` actually parses, and `set_config_value` rejects shell metacharacters — then signal the daemon to reload. Writes the hardware refuses are reported honestly by the daemon (see "Telemetry and control return values" above). The ctest `power_profile` covers profile parsing, explicit-curve precedence, `custom`, and bogus-name handling.

`mvgal-config set-power-curve balanced` remains available and takes **no GPU index** (v0.7.22). It used to accept one, print it, and then discard it: the value is persisted once as `power.power_curve_profile`, so every index wrote the same key. The old two-argument form is still accepted, but warns that the index is ignored.

### Multi-GPU strategies need two GPUs

`afr`, `sfr`, `round_robin`, `hybrid`, `task` and `compute_offload`
distribute work across GPUs, so they need at least two. Since v0.7.25 that
is checked, in three places:

- `mvgal-config set-strategy afr` on a one-GPU machine **refuses**, and
  says so. `--force` overrides it.
- The daemon falls back to `single` at startup and says why, leaving your
  configuration file untouched so it takes effect if you add a GPU.
- `mvgal-compat` names the active strategy when it cannot be used.

The shipped configuration says "Use afr/sfr/hybrid only after mvgal-compat
reports COMPAT_SUPPORTED", but that guidance was enforced nowhere before
v0.7.25 — the daemon would announce
`Scheduler mode from config default_strategy='afr'` on a single-GPU host.

**The profile is acted on, but only as a curve — not as a hardware guarantee.**
Since v0.7.46 `applyPowerConfig()` parses `power_curve_profile` at startup and
on SIGHUP, so the command changes the curve the daemon applies. Whether that
curve moves any hardware depends on the probed capability mask and on power
capping or PSU headroom tracking being enabled; on a GPU with no writable power
interface the write is now reported as refused rather than recorded as applied.
`set-power-profile`, which drives AMD hardware through sysfs, is the command
that takes effect at the driver level.

System telemetry can also be inspected through the native driver's interfaces and tools. For NVIDIA, use the installed `nvidia-smi`; for AMD and Intel, consult the relevant DRM, hwmon, and sysfs nodes. Availability differs by driver and GPU.

## Idle gating

The kernel gates idle control on a measurable busy signal
(`MVGAL_CAP_BUSY_PERCENT`). `mvgal_idle_gate_init()` arms the gate only when
the GPU reports that capability; a GPU without it logs "reports no busy
signal; idle gating is unavailable and will stay disabled", and
`mvgal_idle_gate_set_enabled()` then refuses with `-EOPNOTSUPP`. This
avoids changing device state based on guessed utilization. The gate is
exposed per GPU in sysfs as `idle_gate` (write-only enable),
`idle_gate_status` (distinguishes `unavailable` from `disabled`), and
`idle_gate_timeout`. Armed-but-off is the default — the user must enable it.

## What does not exist

Documented explicitly so readers do not go looking for these:

| Claim | Reality |
|-------|---------|
| `mvgal-powercurve` CLI tool | Does not exist as a separate binary; power curve/profile/PSU control is exposed through `mvgal set-power-curve`, `mvgal set-power-limit`, `mvgal psu-config`, and `mvgal psu-headroom` (v0.7.46). Fan curves still have no CLI or D-Bus method |
| `mvgal-info --dvfs / --power / --temperature / --history` | Flags do not exist (`mvgal-info` accepts only `--json`, `--count`, `--vulkan-groups`, `--version`, `--help`) |
| Gamemode integration (`/etc/mvgal/gamemode.conf`) | No gamemode reference anywhere in `src/`, `runtime/`, or `tools/` |
| Custom curve file `/etc/mvgal/powercurve.json` | No code reads it |
| Moore Threads MTGX power API | No MTGX reference in the tree |
| PCI D-state mapping (D0/D3hot/D3cold) | Not implemented; the daemon does not drive PCI power states |
| Fixed per-state TDP tables and wake-latency numbers | Not implemented |
| 3-level throttle ladder with hysteresis | The kernel uses one continuous formula: `level = (temp − 75) × 100 / (95 − 75)`, clamped to 100, power-off at 95 °C |

## Limitations

MVGAL does not claim universal dynamic voltage/frequency scaling, GPU parking, fan control, thermal policy, or power-curve support. Native drivers retain ownership of the hardware. Check the probed capability mask and the native driver's documentation before changing power settings.

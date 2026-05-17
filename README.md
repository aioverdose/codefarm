# CodeFarm

A local simulated autonomous infrastructure ecosystem rooted at `G:\codefarm`.

Run a Genesis/Sustain cycle:

```powershell
$env:CODEFARM_ROOT = 'G:\codefarm'
python G:\codefarm\overmind.py cycle
```

The first cycle spawns `org-001`, generates code for the pending JSON parser task, digests it into nutrients, updates `state.json`, and writes observatory metrics.

All runtime files, logs, tasks, outputs, state, and placeholders are under `G:\codefarm`.

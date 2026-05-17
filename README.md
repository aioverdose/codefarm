# CodeFarm

CodeFarm is a local self-building infrastructure ecosystem rooted at `G:\codefarm`.

Organisms are agent-like workers with specializations such as Terraform, Ansible, and digestive-engine analysis. They survive by proposing improvements to CodeFarm itself. The orchestrator verifies each proposal, promotes verified changes with snapshots, quarantines failed proposals, awards nutrients, and breeds successful organisms.

## Run

```bat
G:\codefarm\tools\env.bat
G:\codefarm\orchestrator.bat agent-genesis
G:\codefarm\observatory.bat
```

The observatory UI is generated at:

```text
G:\codefarm\observatory\ui\index.html
```

## Safety Model

Organisms do not write directly into live subsystems. They write proposals under:

```text
G:\codefarm\proposals\pending
```

Verified proposals move to `proposals\promoted`, failed proposals move to `proposals\quarantine`, and live targets are snapshotted under `snapshots` before promotion.

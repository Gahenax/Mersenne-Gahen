---
description: Protocol for transforming experiments into modular skills and contracts.
---

# 🚀 Workflow: Modular Skill Injection

This workflow ensures that the Antigravity agent never reverts to a monolithic state. For every new experiment or research track, the following steps MUST be followed:

## 1. Skill Definition (Discovery Phase)
Before writing any research code, create a new directory in `.agent/skills/<skill-name>/`.
Create a `SKILL.md` file defining:
- **Capabilities**: What this experiment can do.
- **Laws**: The rules it must follow.
- **Interpretation**: How to read its results (e.g., Semaforo colors).

## 2. Contract Enforcement (Verification Phase)
Define a formal contract in `SKILL.md` or a localized `CONTRACTS.json` that includes:
- **Input Schema**: Required parameters.
- **Output Schema**: Expected results fields ($H, \Delta S, UA$).
- **Success Criteria**: Thresholds for "ACCEPTED" status.

## 3. Modular Implementation (Execution Phase)
Write the experiment code in `research/<domain>/`.
Ensure the code:
- Imports no logic from other domains.
- Uses `Gahenax_Core` only for ledgering and governance.
- Is stateless, using `results/<domain>/` for any persistence.

## 4. Kernel Integration (Registration Phase)
Register the new skill in the global `CONTRACTS.md` or the `gahenax_ops.py` registry to enable multimodal orchestration.

---
*// turbo-all*
*Workflow strictly enforced by Antigravity Oracle.*

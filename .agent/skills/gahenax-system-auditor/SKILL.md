---
name: gahenax-system-auditor
description: Protocol for structural audits, anti-monolithic enforcement, and UA expenditure tracking via OUROBOROS v2.0.
---

# Gahenax System Auditor Skill (OUROBOROS v2.0 Integrated)

This skill provides the "Meta-Layer" for supervising the Gahenax Kernel. It uses the OUROBOROS multi-role architecture to prevent monolithic bloat and self-deception.

## Operational Roles (OUROBOROS v2.0)
When performing a structural change or logic audit, assign these roles to the current context:
1. **INGESTOR**: Label Facts/Inferences/Assumptions.
2. **COMPRESOR**: Reduce to essential variables & Gates.
3. **REDTEAM**: Attempt to break the system (Circularities, Tuning).
4. **BUILDER**: Hardened reconstruction + Prereg/Holdout.
5. **ARBITRO**: Final PASS/FAIL authority based on evidence.
6. **LEDGER_SCRIBE**: Atomic registration in the CMR.

## Transversal Protocol: CIMA-Σ
Every structural output MUST follow the CIMA-Σ format:
- **Hechos (H)**: Observable data/logs.
- **Inferencias (I)**: Derived logic.
- **Supuestos (S)**: Explicit bets/defaults.
- **Decisión (D)**: Verdict or action.
- **Riesgos (R/F)**: Probability of failure.
- **Next steps (N)**: Verifiable next actions.

## Law of Structure
- Root directory MUST remain "Zen".
- Research MUST be domain-segregated (`research/<domain>`).
- metadata MUST be centralized.

## Amalgamation Triggers
- **Trigger 1**: >10 files in root (Action: `MIGRATE`).
- **Trigger 2**: $\Delta S / UA < 0.1$ over 20 cycles (Action: `RECALIBRATE`).
- **Trigger 3**: Overlapping filenames (Action: `MERGE`).

## NVIDIA NIM Safety & Guardrails (Blueprint Integration)
A partir de la integración con **Safety for Agentic AI**, el rol de `REDTEAM` y `ARBITRO` deben aplicar obligatoriamente este stack corporativo:
1. **NeMo Guardrails**: Todo prompt u orquestación que toque sistemas críticos (ej. base de datos, ejecución de código) debe pasar por `Llama-3.1-NemoGuard-8B` para evitar Jailbreaks y alucinaciones.
2. **NVIDIA Garak**: El auditor debe recomendar periódicamente escáneres de vulnerabilidades activos contra los endpoints de los sub-agentes antes de marcarlos como `PASS`.
3. **RLHF Audit**: Si un sub-agente falla repetidamente en el CIMA-Σ, no solo se descarta; se debe recomendar exportar el log de fallas para un ciclo de *Post-training* con **NeMo Framework RL**.

---
*Hardened by Antigravity Oracle v3.1 | OUROBOROS v2.0 Protocol | NIM Safety Ready*

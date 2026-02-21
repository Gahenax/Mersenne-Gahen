---
name: gahenax-governance
description: Protocols for the Gahenax Core, Falsifiability Ledger (FCD), and CMR audits.
---

# Gahenax Governance Skill

This skill manages the "Motor Lógico" (Logical Engine) and its strict adherence to the Hodge-PCP (Probabilistically Checkable Proofs) standard.

## 🛠️ Core Capabilities
1. **CMR (Canonical Measurement Recorder)**: Atomic logging of every inference or computation cycle with hardware-linked fingerprints.
2. **Semaforo Protocol**: Real-time auditing of spectral rigidity ($H$) and contract validity.
3. **Snapshot & Seal**: Generating signed JSONL snapshots for blockchain anchoring or peer-review.

## 📜 Operational Contracts
- **Contract Versioning**: Every modification to the logical engine must increment the `CONTRACT_VERSION` in `gahenax_ops.py`.
- **UA Budgeting**: All operations must declare a "Universal Action" (UA) budget hint to prevent infinite loops or resource exhaustion.
- **Fail-Fast**: If the `Semaforo` returns **RED**, the orchestrator MUST halt and request manual recalibration.

## 🚀 Key Scripts
- `Gahenax_Core/gahenax_ops.py`: The central hub for ledger operations.
- `Gahenax_Core/orchestrator/orchestrator.py`: The single-orchestrator managing the multi-worker swarm.

## ⚖️ Ethical Boundary
This engine operates under the `ETHICS.md` of the Gahenax repository, focusing on transparent, falsifiable AI-driven research.

---
*Skill injected via Antigravity Oracle protocol.*

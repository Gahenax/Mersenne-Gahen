# 📜 Gahenax / Hodge Repository Contracts

**Version**: 2.0.0  
**Status**: ACTIVE  
**Goal**: Prevent logical overlap and ensure modularity between research tracks.

---

## 1. Global Module Hierarchy

All code in this repository must belong to one of the following architectural layers:

1.  **L0: Governance (The Core)**
    - Location: `Gahenax_Core/`
    - Responsibility: Ledgering, Falsifiability gates, and Security.
    - *Contract*: No research script may write to its own log; it MUST use the `Gahenax_Core/gahenax_ops.py` interface.

2.  **L1: Specialized Skills**
    - Location: `.agent/skills/`
    - Responsibility: Abstracting "knowledge" into executable instructions for the AI agent.
    - *Contract*: All "How-to" logic must be documented here, not in the agent's system prompt.

3.  **L2: Research Engines**
    - Location: `research/` (e.g., `research/riemann/`, `research/mersenne/`)
    - Responsibility: Heavy lifting, math, and data mining.
    - *Contract*: Engines must be "stateless" or use localized `checkpoints/` folders.

4.  **L3: Artifacts & Evidence**
    - Location: `artifacts/`, `results/`
    - Responsibility: Persistent storage of proof.
    - *Contract*: No evidence file is valid unless registered in the `ua_ledger.sqlite`.

---

## 2. Intersystem Protocol (The "Wire")

When a **Research Engine** (L2) completes a task, it must pass a result to the **Governance** (L0) layer using the following schema:

```json
{
  "protocol": "Hodge-PCP-v1",
  "meta": {
    "engine": "MERSENNE_WARP_V2",
    "timestamp": "ISO-8601",
    "fingerprint": "SHA-256"
  },
  "payload": {
    "target": "2^1279-1",
    "verdict": "COMPOSITE",
    "h_rigidity": 1.42e-15,
    "delta_s": 0.042
  }
}
```

---

## 3. The "Anti-Monolith" Rule

- **No Flat Growth**: New scripts must be placed in `research/<sub-domain>/`.
- **Naming Conventions**: Scripts must follow the `<DOMAIN>_<TOOL>_<VERSION>.py` format.
- **Dependency Cleanliness**: No circular imports between `riemann` and `mersenne` modules.

## 4. External Lab Delegation (Jules)

- **Role**: Jules is the canonical remote compute provider.
- **Protocol**: All data sent to Jules must be cryptographically hashed.
- **Validation**: No result from Jules is "Canonical" until the local Kernel validates its `h_rigidity` and registers it in `ua_ledger.sqlite`.
- **Latency Tolerance**: The Orquestador must handle Jules as an asynchronous worker with potential high-latency loopback.

## 5. Skill-First Mandate (Anti-Monolith Protocol)

- **Mandate**: Every new experiment MUST be preceded by the creation of a Skill in `.agent/skills/`.
- **Modularity**: Code that does not belong to a defined Skill or violates its domain-specific contract will be flagged as "UNSTRUCTURED" and blocked from the Ledger.
- **Auto-Documentation**: The Agent must update the `SKILL.md` of a domain as new findings or tools are integrated.

---

*This contract is legally binding for all Antigravity instances operating in this workspace.*

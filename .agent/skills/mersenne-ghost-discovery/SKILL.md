---
name: mersenne-ghost-discovery
description: Specialized probe for detecting "Invariance Loci" (GL) and Telemetry Phenotypes (TP) in the neighborhoods of certified primes.
---

# Mersenne Invariance Audit (Ghost-Discovery Calibrated)

This skill governs the detection of **Invariance Loci (GL)**: exponents that, while arithmetically composite (LL != 0), exhibit a high degree of phenotypic stability under algorithmic attacks.

## 🛠️ Mission: The GL/TP Hunt
We shifted from "Ghost Primes" to "Invariance Loci". We no longer seek hidden primes, but rather **Structural Phenotypes** in the exponent pipeline.

## 📜 Audit Protocols
1. **GL-Classification**: Classifying candidates into GL-A (absolute invariance), GL-B, GL-C, or GL-D (artifact).
2. **Attack Vectoring**: Using the `InvarianceEngine` to apply rotations, permutations, and precision sweeps to examine the $I(p)$ index.
3. **Telemetry Packaging (TP)**: Tagging runs with `TP-FFT`, `TP-SYS`, or `TP-IO` to identify hardware/software dependencies.
4. **Arithmetic Boundary**: Maintaining a strict separation between GL-Invariance and LL-Primality. $M_p$ with $LL \neq 0$ is always COMPOSITE.

## 🚀 Execution
- `Gahenax_Core/physics/INVARIANCE_ENGINE.py`: The core audit instrument.
- `research/mersenne/NEIGHBORHOOD_SCANNER.py`: Identifying GL-candidates.
- `tools/ghost_hunter_lab.py`: Calibrating records for the Unified Ledger.

---
*Skill recalibrated by Antigravity Oracle v4.5 - Epistemological Guardrail.*

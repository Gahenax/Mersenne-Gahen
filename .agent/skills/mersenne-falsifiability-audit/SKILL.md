---
name: mersenne-falsifiability-audit
description: Rigorous blindage and falsifiability testing for Mersenne Ghost Loci using representation stress-tests.
---

# Mersenne Falsifiability Audit (Ghost Hunter Lab)

This skill provides a high-rigor framework for validating numerical "ghosts" using the **GHOST-HUNTER LAB PLUG**.

## 🛠️ Core Capabilities
1. **Preregistration**: Freezing hypotheses and success criteria before execution to prevent p-hacking.
2. **Representation Stress-Tests**: Applying rotations, swaps, and permutations to residues to ensure $H$ isn't an artifact of the data format.
3. **Negative Controls**: Automatic sampling of non-Mersenne candidates to establish a baseline.
4. **Statistical Summarization**: Automatic grouping and flagging of degenerate metrics.

## 📜 Laws & Contracts
- **Prereg Law**: No experiment is valid without a `prereg.json` file.
- **Falsifiability Law**: Every "Ghost Locus" must survive at least 3 representation tests (rotation, swap, permutation) without its rigidity $H$ collapsing.
- **Reporting**: Outputs must be saved in `results/mersenne/falsifiability/`.

## 🚀 Key Scripts
- `tools/ghost_hunter_lab.py`: The core experiment engine.
- `tools/mersenne_ghost_adapter.py`: The adapter for the Antigravity Mersenne Engine.

---
*Skill injected via Antigravity Oracle protocol.*

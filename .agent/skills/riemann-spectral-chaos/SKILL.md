---
name: riemann-spectral-chaos
description: Logic for Riemann zeta zero mining and spectral rigidity analysis (H-rigidity).
---

# Riemann Spectral Chaos Skill

This skill provides the theoretical and practical framework for investigating the distribution of Riemann zeros and their adherence to the Gaussian Unitary Ensemble (GUE) statistics.

## 🛠️ Core Capabilities
1. **Tripwire Mining**: Efficient zero detection using sign-change bracketing in the Hardy Z-function.
2. **Spectral Rigidity (H-rigidity)**: Calculation of the $\bar{r}$ statistic to measure "structural" vs "noisy" behavior.
3. **Band Analysis**: Partitioning the critical line into $T \in [T_{start}, T_{end}]$ bands for longitudinal drift analysis.

## 📜 Laws & Contracts
- **Schema**: Every result must report $\{t_{root}, \text{iters}, |f(t)|, \text{h\_rigidity}\}$.
- **Precision**: Minimum DPS (decimal places) of 50 for $T < 10^4$, scaling logarithmically with $T$.
- **Deduplication**: SHA-256 fingerprinting of zero sets to prevent "ghost" overlaps.

## 🚀 Key Scripts
- `RIEMANN_TRIPWIRE_MINER_V2.py`: The reference implementation for mining.
- `ab_calibrator.py`: Used for baseline drift calibration between Band A and Band B.

## 📊 Interpretation (Semaforo)
- **GREEN (Structural)**: $H \le 10^{-14}$. Consistent with high-precision GUE.
- **YELLOW (Island-T)**: $10^{-14} < H \le 10^{-11}$. Localized perturbation or precision fatigue.
- **ORANGE (Drift-Warn)**: $10^{-11} < H \le 10^{-8}$. Significant deviation, requires recalibration.
- **RED (Ghost)**: $H > 10^{-8}$ or failed convergence. Potential hallucination or numerical instability.

---
*Skill injected via Antigravity Oracle protocol.*

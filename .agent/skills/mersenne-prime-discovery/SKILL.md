---
name: mersenne-prime-discovery
description: Logic for Mersenne prime search, GIMPS synchronization, and Hodge-PCP proof verification.
---

# Mersenne Prime Discovery Skill

This skill governs the high-performance search for Mersenne primes ($2^p - 1$) and the verification of existing claims using the LUCAS-LEHMER test and spectral analysis.

## 🛠️ Core Capabilities
1. **Lucas-Lehmer Warp**: Optimized LL test with periodic checkpointing and GPU/Distributed delegation hints.
2. **GIMPS Sync**: Pulling recent results from the GIMPS network to calibrate the local "Seismograph".
3. **Probabilistic Seismography**: Detecting "anomalies" in the exponent space before full LL-test execution to prioritize computational resources.

## 📜 Laws & Contracts
- **Verification Law**: A prime is not "found" until it has two independent LL-test residues matching perfectly.
- **Evidence Schema**: Every candidate must generate an `evidence_p<exp>.json` file containing the residue, duration, and hardware fingerprint.
- **Checkpointing**: In-progress tests must save state every $10^5$ iterations.

## 🚀 Key Scripts
- `MERSENNE_SEISMOGRAPH_V2.py`: Analyzes exponent density for potential "hot zones".
- `mersenne_production_w3.py`: The production-grade worker for the Lucas-Lehmer sweep.

## 📊 Verdicts
- **PRIME**: Confirmed Mersenne prime.
- **COMPOSITE**: Confirmed composite via LL-test.
- **STALLED**: Process halted (check hardware thermal/power).
- **DRIFT**: Unexpected residue variance (possible cosmic ray or bit-flip).

---
*Skill injected via Antigravity Oracle protocol.*

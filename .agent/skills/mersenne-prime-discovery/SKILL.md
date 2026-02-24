---
name: mersenne-prime-discovery
description: Logic for Mersenne prime search, GIMPS synchronization, and Hodge-PCP proof verification.
---

# 🚀 Mission: Path to 100,000,000

This skill governs the systematic mapping of the Mersenne exponent space from the current certified frontier towards the 100M mark ($p=10^8$).

## 🛠️ Mission Objectives
1. **Block-Wise Scanning**: Dividing the range $[23209, 100,000,000]$ into manageable blocks (1M exponents each).
2. **Deterministic Certification**: Applying the Lucas-Lehmer test with Dual-Path Verification to every candidate.
3. **Spectral Profiling**: Recording the $H$ (Hodge Rigidity) for every exponent to detect "Ghost Loci" and structural trends.
4. **Jules Delegation**: Offloading high-energy blocks ($p > 5M$) to the distributed lab.

## 📜 Governing Laws
- **Continuity Law**: No block can be certified unless the previous block has been fully audited and ledgered.
- **Evidence Law**: Every discovery must be accompanied by its LL-residue hash and wall-time metrology.
- **Fail-Closed**: If a hardware bit-flip is detected (Mismatch in Path A/B), the block is invalidated and re-scheduled.

## 🚀 Execution Tools
- `research/mersenne/MERSENNE_PROBE_V1.py`: Core engine.
- `jules_orders/JULES_MAP_100M_BLOCK_XXX.json`: Work orders for the path to 100M.

---
*Mission blueprint by Antigravity Oracle v4.0*

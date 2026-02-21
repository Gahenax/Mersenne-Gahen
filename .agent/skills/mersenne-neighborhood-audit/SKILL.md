---
name: mersenne-neighborhood-audit
description: Auditing the numerical "neighborhood" of certified Mersenne primes to detect spectral echoes or missed loci.
---

# Mersenne Neighborhood Audit Skill

This skill focuses on the high-resolution investigation of the exponent space immediately surrounding known Mersenne primes ($p_{prime} \pm \Delta p$).

## 🛠️ Core Capabilities
1. **Neighborhood Mapping**: Systematic scanning of exponents in a radius around certified primes.
2. **Spectral Echo Detection**: Identifying composite exponents that exhibit "prime-like" spectral rigidity ($H \to 0$) during the first $10^5$ iterations of the LL-test.
3. **Ghost Locus Identification**: Filtering candidates that GIMPS might have skipped due to thresholding artifacts.

## 📜 Laws & Contracts
- **Baseline Law**: Every scan MUST be anchored to a certified prime from the `ua_ledger.sqlite`.
- **Detection Contract**: A "Ghost Locus" is defined as any exponent $p$ where the PRP test is negative but the LL-test residue exhibits local stability $> P95$ of the baseline.
- **Reporting**: Results are saved in `results/mersenne/neighborhoods/`.

## 🚀 Key Scripts
- `research/mersenne/NEIGHBORHOOD_SCANNER.py`: The worker for local radius scans.
- `jules_orders/JULES_ORDER_GHOST_HUNT.json`: Delegation template for large $p$ neighborhoods.

---
*Skill injected via Antigravity Oracle protocol.*

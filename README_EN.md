# GAHENAX — Hodge Rigidity Research Laboratory

> **Language note:** All code and scripts are in English. The Spanish version of this README is [`README.md`](README.md). The full scientific report is available in both languages: [`reports/riemann_phase1_spectral_report.tex`](reports/riemann_phase1_spectral_report.tex) (ES) and [`reports/riemann_phase1_spectral_report_EN.tex`](reports/riemann_phase1_spectral_report_EN.tex) (EN).

---

## What this repository is

This repository contains the experimental infrastructure and results for two parallel research lines:

1. **Riemann Zero Spectral Analysis** — detecting structural signatures in the zero spectrum of $\zeta(s)$ and comparing them against the GUE (Gaussian Unitary Ensemble) random matrix model.
2. **Mersenne Prime Certification** — deterministic certification of Mersenne primes ($M_p = 2^p - 1$) via Lucas-Lehmer, and a spectral proof-of-concept linking Mersenne primes to the Riemann zero spectrum.

Both lines operate under the **Gahenax Core v1.1.1 / OUROBOROS v2.0** governance protocol, which enforces auditable, falsifiable, and reproducible computation.

---

## Key Results (Phase 1)

| Metric | Observed | GUE Expected | Deviation |
|:-------|:--------:|:------------:|:---------:|
| $\langle r \rangle$ (local order) | **0.6152** | 0.5996 | +2.6% |
| ACF lag-1 | **−0.376** | −0.25 | −50% |
| $\Sigma^2(L=10)$ / GUE | **52.2%** | 100% | −48% |
| FFT peak frequency | **0.0994** cycles/zero | — | matches $p=2$ |
| Pearson $r(\log p, A_p)$ | **−0.9668** | — | $p < 0.0001$ |

**Three simultaneous spectral anomalies** were detected in $T \in [6340, 6640]$:
- Local hyperuniformity ($\mathrm{ACF}_1 = -0.376$, 50% above GUE)
- Dominant spectral echo at $f = 0.099$ cycles/zero (power $P = 35.07$)
- Number variance compression: 41.6% more rigid than GUE at $L=10$

All peaks are identified as **prime spectral fingerprints** via the Riemann explicit formula, with prediction error $< 1\%$ across 11 primes ($p = 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31$).

---

## Research Architecture

### Phase 1 (complete)
- **Dataset:** 332 certified zeros, $T \in [6340.36, 6639.84]$
- **System:** Domino-WAVE, 6 parallel probes (ALPHA–FOXTROT)
- **Report:** [`reports/riemann_phase1_spectral_report_EN.tex`](reports/riemann_phase1_spectral_report_EN.tex)

### Phase 2 (complete — persistence tests)
- Three disjoint ranges: $T \in \{[1000,1300],\, [6340,6640],\, [10000,10300]\}$
- Robust $\Sigma^2(L)$ estimator (random origins, bias-corrected)
- Sub-GUE rigidity confirmed across all three ranges

### Phase 3 (pending — Jules execution)
- **Target:** $N \geq 10{,}000$ zeros, $T \in [7000, 15000]$
- **Goal:** Mersenne spectral POC with sufficient statistical power (AUC $\geq 0.60$)
- **Work order:** [`jules_orders/JULES_ORDER_RIEMANN_P3.json`](jules_orders/JULES_ORDER_RIEMANN_P3.json)

---

## Mersenne Prime Certification

### Architecture
| Phase | Description |
|:------|:------------|
| **P1 (Search)** | High-speed probabilistic search (PRP) |
| **P2 (Verify)** | Deterministic Lucas-Lehmer certification |
| **Audit** | Integrity governance via roundoff semaphore |

### Spectral POC
Using the explicit-formula statistic $S(u) = \sum_\gamma w(\gamma) e^{i\gamma u}$, evaluated at $u = \log(M_k)$, we test whether certified Mersenne primes leave a detectable signature in the Riemann zero spectrum.

**Phase-1 result (N=332):** AUC($k \leq 127$) = 0.603. Signal above chance, below confirmation threshold. Phase-3 (N=10,000) will deliver a statistically powered test.

---

## Repository Structure

```
Tesis/
├── scripts/                  ← Analysis and pipeline scripts (EN)
│   ├── mersenne_spectral_poc.py    Explicit-formula S(u) instrument
│   ├── poc_25_mersenne.py          25 certified Mersenne exponents test
│   ├── phase3_aggregator.py        Gate 0 + aggregation for Phase-3
│   ├── layer_c_adversarial.py      Adversarial audit (3 nulls × 3 windows)
│   ├── prime_resonance_analysis.py FFT peak ↔ prime correlation
│   └── audit_dataset.py            Full dataset quality audit
├── reports/
│   ├── riemann_phase1_spectral_report.tex     Full report (ES)
│   └── riemann_phase1_spectral_report_EN.tex  Full report (EN)
├── jules_orders/             ← Work orders for Jules distributed lab
├── results/riemann/          ← Certified zero data and analysis outputs
├── ledger_riemann_phase1/    ← Append-only data ledger (shards)
└── docs/ES/
    └── guia_scripts.md       ← Script documentation in Spanish
```

---

## Falsifiability

All hypotheses are pre-registered with explicit failure conditions:

| Hypothesis | Failure condition |
|:-----------|:-----------------|
| **H1 (Layer B):** AUC $> 0.60$ | AUC $< 0.55$ with $N \geq 10{,}000$ → archived |
| **H2 (Layer C):** $k=10,11,29$ peaks are real | Do not survive adversarial audit → artefact |
| **H3 (Persistence):** Sub-GUE is persistent | $\Sigma^2$ ratio $> 90\%$ across all ranges |

---

## Governance

This repository operates under **OUROBOROS v2.0** — a protocol for deterministic, auditable scientific computation:
- All parameters pre-registered before data collection
- Estimator corrections documented explicitly (see Appendix A of report)
- No post-hoc threshold adjustments
- Negative results reported identically to positive ones

---

## Operational Log

See [`MERSENNE_OPERATIONAL_LOG.md`](MERSENNE_OPERATIONAL_LOG.md) for the register of certified exponents and fragility missions.

---

*Deterministic Truth Laboratory — Jules & Antigravity (2026)*

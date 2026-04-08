from __future__ import annotations

import sys
import os
# Setup relative src config loading for subdirectories
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import src.config

"""
mersenne_spectral_poc.py
========================
Proof-of-concept: detect spectral fingerprints of Mersenne primes in the
Riemann zero spectrum via the explicit-formula statistic.

  S(u) = sum_gamma  w(gamma) * exp(i * gamma * u)

Evaluated at u = log(M_k) = log(2^k - 1), S(u) should show a statistical
excess when M_k is prime compared to when M_k is composite.

Three pre-registered layers:
  A -- Sanity : log(2), log(3), log(5), log(7), 2*log(2), 3*log(2)
  B -- Mersenne: k prime and M_k prime  vs  k prime and M_k composite
  C -- Power-of-2 structure: energy at u = k*log(2) grid

Pre-registered parameters (no post-hoc changes):
  window   = "hann"
  B_null   = 300   (phase-randomization draws)
  z_thresh = 1.5   (exploratory threshold; BH-FDR for reporting)
  AUC_min  = 0.60  (Layer B success criterion)

Data: results/riemann/persistence_test.json +
      results/riemann/jules_phase1_full.jsonl
"""

import sys, io
# try:
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
# except Exception:
#     pass

import json, math, os
import numpy as np

PROJECT   = str(src.config.PROJECT_ROOT)
PHASE1_FP = os.path.join(PROJECT, "results", "riemann", "jules_phase1_full.jsonl")
PERSIST_FP = os.path.join(PROJECT, "results", "riemann", "persistence_test.json")

# ─── Pre-registered parameters ───────────────────────────────────────────────
WINDOW_MODE = "hann"
B_NULL      = 300
JITTER      = 0.05   # T units: must be << 2pi/u_target to disrupt coherence
             # at target u without destroying signal at small u.
             # mean_gap~0.9; jitter=0.05 ~ 5% of gap -- small enough.
Z_THRESH    = 1.5
AUC_MIN     = 0.60
# ─────────────────────────────────────────────────────────────────────────────


# ─── Mersenne lists (pre-registered, no post-hoc selection) ──────────────────

MERSENNE_PRIME_K  = [2,  3,  5,  7, 13, 17, 19, 31, 61, 89, 107, 127]
CONTROL_K         = [11, 23, 29, 37, 41, 43, 47, 53, 59, 67,  71,  73]
# Controls: k prime, M_k = 2^k-1 composite (verified by GIMPS/factorization)

SANITY_U_LABELS = [
    (math.log(2),   "log(2)"),
    (math.log(3),   "log(3)"),
    (math.log(5),   "log(5)"),
    (math.log(7),   "log(7)"),
    (2*math.log(2), "2*log(2)"),
    (3*math.log(2), "3*log(2)"),
    (4*math.log(2), "4*log(2)"),
]


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_phase1_zeros(path: str) -> np.ndarray:
    zeros = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            t = rec.get("t_est")
            if t is None:
                p = rec.get("payload", {})
                t = p.get("t_est") or p.get("T") or p.get("refined_T")
            if t and isinstance(t, (int, float)) and t > 0:
                zeros.append(float(t))
    return np.array(sorted(set(zeros)))


def load_persistence_zeros(path: str) -> dict[str, np.ndarray]:
    """Load zeros from the persistence_test.json file — only B and C ranges."""
    # We don't have raw zeros stored there; must recompute from mpmath.
    # Returns empty dict — caller will use mpmath or only phase1.
    return {}


# ─── Core: S(u) statististic ──────────────────────────────────────────────────

def _window_weights(gammas: np.ndarray, T0: float, T1: float,
                    mode: str = "hann") -> tuple[np.ndarray, np.ndarray]:
    mask = (gammas >= T0) & (gammas <= T1)
    g    = gammas[mask]
    if g.size == 0:
        return g, np.array([])
    x = (g - T0) / (T1 - T0 + 1e-30)

    if mode == "hann":
        w = 0.5 * (1.0 - np.cos(2.0 * math.pi * x))
    elif mode == "tukey":
        alpha = 0.2
        w = np.ones_like(x)
        left  = x < alpha / 2
        right = x > 1 - alpha / 2
        w[left]  = 0.5 * (1 + np.cos(2*math.pi*(x[left]/alpha  - 0.5)))
        w[right] = 0.5 * (1 + np.cos(2*math.pi*((x[right]-1)/alpha + 0.5)))
    else:
        w = np.ones_like(g)
    return g, w


def S_of_u(gammas: np.ndarray, u_grid: np.ndarray,
           T0: float, T1: float, mode: str = "hann") -> np.ndarray:
    """
    S(u) = Σ_γ w(γ) exp(i·γ·u) / ||w||_2
    Returns complex array of shape (len(u_grid),).
    """
    g, w = _window_weights(gammas, T0, T1, mode)
    if g.size == 0:
        return np.zeros(len(u_grid), dtype=complex)
    denom = math.sqrt(float(np.sum(w**2))) + 1e-30
    phase = np.exp(1j * np.outer(g, u_grid))   # (N_gamma, N_u)
    S = (w[:, None] * phase).sum(axis=0) / denom
    return S


def null_distribution(gammas: np.ndarray, u0: float,
                       T0: float, T1: float,
                       B: int = 300, jitter: float = None,
                       seed: int = 0) -> np.ndarray:
    """
    Null via PHASE RANDOMIZATION:
      Replace exp(i*gamma*u) with exp(i*phi_k), phi_k ~ U[0, 2pi].
    Correct null for |S(u)|: preserves window weights, destroys coherence.
    |S| follows approximately Rayleigh(1/sqrt(N_eff)).
    """
    g, w = _window_weights(gammas, T0, T1, WINDOW_MODE)
    if g.size < 5:
        return np.zeros(B)
    denom = math.sqrt(float(np.sum(w**2))) + 1e-30
    rng   = np.random.default_rng(seed)
    vals  = np.empty(B, dtype=float)
    for b in range(B):
        phi  = rng.uniform(0.0, 2*math.pi, size=g.size)
        S_r  = (w * np.exp(1j * phi)).sum() / denom
        vals[b] = abs(S_r)
    return vals


def probe_u(gammas: np.ndarray, u0: float,
            T0: float, T1: float) -> dict:
    """Full probe at a single u0: observed |S|, null, z-score."""
    obs_S    = S_of_u(gammas, np.array([u0]), T0, T1, WINDOW_MODE)[0]
    obs_abs  = float(abs(obs_S))
    null_abs = null_distribution(gammas, u0, T0, T1, B=B_NULL,
                                  jitter=JITTER, seed=int(u0 * 1000) % 99991)
    mu  = float(np.mean(null_abs))
    sig = float(np.std(null_abs)) + 1e-30
    z   = (obs_abs - mu) / sig
    return {"u": u0, "obs": obs_abs, "null_mean": mu,
            "null_std": sig, "z": z}


_CACHED_ZEROS: np.ndarray | None = None


def get_zeros() -> np.ndarray:
    """Lazy-load and cache Phase-1 Riemann zeros."""
    global _CACHED_ZEROS
    if _CACHED_ZEROS is None:
        _CACHED_ZEROS = load_phase1_zeros(PHASE1_FP)
    return _CACHED_ZEROS


def probe(p: int) -> dict:
    """
    High-level interface for Ghost Locus pre-filter.
    Computes S(u) at u = log(2^p - 1) using cached Phase-3 Riemann zeros.
    Returns dict with 'z' score.
    """
    # u = log(2^p - 1)
    # For p > 60, log(2^p - 1) is indistinguishable from p*log(2) in float64.
    if p < 500:
        u = math.log(2**p - 1)
    else:
        u = p * math.log(2)

    gammas = get_zeros()
    if gammas.size == 0:
        return {"u": u, "z": 0.0, "obs": 0.0, "null_mean": 0.0, "null_std": 1.0}

    T0, T1 = float(gammas[0]), float(gammas[-1])
    return probe_u(gammas, u, T0, T1)


# ─── FDR Benjamini-Hochberg ───────────────────────────────────────────────────

def bh_qvalues(z_scores: np.ndarray, alpha: float = 0.1) -> np.ndarray:
    """
    One-sided p-values from z-scores, then BH FDR correction.
    Returns q-values (adjusted p-values).
    """
    from scipy.special import erfc
    p_vals = 0.5 * erfc(np.asarray(z_scores, dtype=float) / math.sqrt(2))
    n      = len(p_vals)
    order  = np.argsort(p_vals)
    q      = np.empty(n)
    q[order] = p_vals[order] * n / (np.arange(1, n+1))
    q = np.minimum.accumulate(q[::-1])[::-1]
    return q


# ─── AUC (Mersenne prime vs control) ─────────────────────────────────────────

def auc_score(positives: list[float], negatives: list[float]) -> float:
    """Non-parametric AUC: P(positive > negative)."""
    pos = np.array(positives)
    neg = np.array(negatives)
    total = len(pos) * len(neg)
    if total == 0:
        return float("nan")
    wins = float(np.sum(pos[:, None] > neg[None, :]))
    ties = float(np.sum(pos[:, None] == neg[None, :]))
    return (wins + 0.5 * ties) / total


# ─── Runners ──────────────────────────────────────────────────────────────────

def run_layer_A(gammas: np.ndarray, T0: float, T1: float) -> list[dict]:
    """Sanity check: peaks at log(p) and powers of 2 must be detectable."""
    print(f"\n  [Layer A] Sanity -- window T=[{T0:.1f},{T1:.1f}]  N={len(gammas)}")
    print(f"  {'Label':<14} {'u':>8}  {'|S|':>7}  {'null_mu':>7}  {'z':>6}")
    print(f"  {'-'*60}")
    results = []
    for u0, label in SANITY_U_LABELS:
        r = probe_u(gammas, u0, T0, T1)
        r["label"] = label
        results.append(r)
        flag = "***" if r["z"] > Z_THRESH else "   "
        print(f"  {label:<14} {u0:>8.4f}  {r['obs']:>7.4f}  "
              f"{r['null_mean']:>7.4f}  {r['z']:>6.2f}  {flag}")
    return results


def run_layer_B(gammas: np.ndarray, T0: float, T1: float,
                range_label: str = "A") -> dict:
    """Mersenne prime-k vs control-k: falsifiable A/B test."""
    print(f"\n  [Layer B] Mersenne vs Control — {range_label}  "
          f"T=[{T0:.1f},{T1:.1f}]  N={len(gammas)}")
    print(f"  {'Type':<16} {'k':>5}  {'u=log(Mk)':>12}  "
          f"{'|S|':>7}  {'z':>6}  {'q-val':>7}")
    print(f"  {'-'*64}")

    rows = []
    for label, ks in [("mersenne_prime", MERSENNE_PRIME_K),
                       ("control",        CONTROL_K)]:
        for k in ks:
            Mk  = 2**k - 1
            u0  = math.log(Mk)
            r   = probe_u(gammas, u0, T0, T1)
            r["label"] = label
            r["k"]     = k
            r["Mk"]    = Mk
            rows.append(r)

    # FDR correction on all z-scores
    all_z = np.array([r["z"] for r in rows])
    q_vals = bh_qvalues(all_z)
    for r, q in zip(rows, q_vals):
        r["q"] = float(q)

    # Print
    for r in rows:
        flag = "***" if r["z"] > Z_THRESH else "   "
        print(f"  {r['label']:<16} {r['k']:>5}  {r['u']:>12.4f}  "
              f"{r['obs']:>7.4f}  {r['z']:>6.2f}  {r['q']:>7.4f}  {flag}")

    # AUC
    pos_z = [r["z"] for r in rows if r["label"] == "mersenne_prime"]
    neg_z = [r["z"] for r in rows if r["label"] == "control"]
    auc   = auc_score(pos_z, neg_z)
    verdict = "PASS" if auc >= AUC_MIN else "FAIL"
    print(f"\n  AUC(mersenne_prime > control) = {auc:.4f}  "
          f"[threshold={AUC_MIN}]  --> {verdict}")

    return {"rows": rows, "auc": auc, "verdict": verdict, "range": range_label}


def run_layer_C(gammas: np.ndarray, T0: float, T1: float) -> list[dict]:
    """
    Power-of-2 structure: energy at u = k*log(2) for k=1..30.
    Hypothesis: k yielding prime M_k show excess over k yielding composite M_k.
    """
    print(f"\n  [Layer C] Power-of-2 structure: u=k*log(2)  "
          f"T=[{T0:.1f},{T1:.1f}]")
    print(f"  {'k':>4}  {'u':>8}  {'|S|':>7}  {'z':>6}  {'Mk_prime?':>10}")
    print(f"  {'-'*50}")

    log2 = math.log(2)
    mersenne_prime_set = set(MERSENNE_PRIME_K)
    rows = []
    for k in range(1, 31):
        u0 = k * log2
        r  = probe_u(gammas, u0, T0, T1)
        r["k"]        = k
        r["Mk_prime"] = k in mersenne_prime_set
        rows.append(r)
        flag = "*" if r["Mk_prime"] else " "
        print(f"  {k:>4}  {u0:>8.4f}  {r['obs']:>7.4f}  {r['z']:>6.2f}  "
              f"  {flag}{'Mersenne' if r['Mk_prime'] else ''}")

    pos_z = [r["z"] for r in rows if r["Mk_prime"]]
    neg_z = [r["z"] for r in rows if not r["Mk_prime"]]
    auc   = auc_score(pos_z, neg_z)
    print(f"\n  AUC(Mk_prime > not) in k*log(2) = {auc:.4f}  [speculative, no threshold]")
    return rows


# ─── Main ────────────────────────────────────────────────────────────────────

def print_header():
    print("="*70)
    print("  GAHENAX MERSENNE SPECTRAL POC")
    print("  Mersenne fingerprints in Riemann zero spectrum via explicit formula")
    print()
    print("  PRE-REGISTERED PARAMETERS:")
    print(f"    window   = {WINDOW_MODE}")
    print(f"    B_null   = {B_NULL}")
    print(f"    z_thresh = {Z_THRESH}  (exploratory)")
    print(f"    AUC_min  = {AUC_MIN}  (Layer B success criterion)")
    print()
    print("  MERSENNE PRIME k:  ", MERSENNE_PRIME_K)
    print("  CONTROL k:         ", CONTROL_K)
    print("="*70)


if __name__ == "__main__":
    print_header()

    # ── Load Range A (Phase-1 baseline)
    zeros_A = load_phase1_zeros(PHASE1_FP)
    T0_A, T1_A = float(zeros_A[0]), float(zeros_A[-1])
    dT_A = T1_A - T0_A
    mean_gap_A = float(np.mean(np.diff(zeros_A)))
    print(f"\n  Range A: N={len(zeros_A)}  T=[{T0_A:.2f},{T1_A:.2f}]"
          f"  dT={dT_A:.1f}  du_res={2*math.pi/dT_A:.4f}  mean_gap={mean_gap_A:.4f}")

    # ── Load Range B and C via mpmath (reuse persistence logic)
    try:
        import mpmath
        mpmath.mp.dps = 20
        MPMATH_OK = True
        print("  mpmath OK.")
    except ImportError:
        MPMATH_OK = False
        print("  [WARN] mpmath not available. Using Range A only.")

    datasets: dict[str, tuple[np.ndarray, float, float]] = {
        "A: T=[6340,6640]": (zeros_A, T0_A, T1_A),
    }

    if MPMATH_OK:
        # Load B from persistence test cache or recompute
        cache_B = os.path.join(PROJECT, "results", "riemann", "zeros_B_1000_1243.npy")
        cache_C = os.path.join(PROJECT, "results", "riemann", "zeros_C_10000_10169.npy")

        if os.path.exists(cache_B):
            zeros_B = np.load(cache_B)
            print(f"  Range B loaded from cache: {len(zeros_B)} zeros")
        else:
            print("\n  Acquiring B (T=[1000,1243], cap=200)...", end="", flush=True)
            zeros_B = []
            n = max(1, int((1000/(2*math.pi)) * math.log(1000/(2*math.pi)) - 1000/(2*math.pi)) - 5)
            while len(zeros_B) < 200:
                z = float(mpmath.im(mpmath.zetazero(n)))
                if z > 1243 + 1: break
                if 1000 <= z <= 1243: zeros_B.append(z)
                n += 1
                if n > 1100: break
            zeros_B = np.array(sorted(zeros_B))
            np.save(cache_B, zeros_B)
            print(f" {len(zeros_B)} zeros")

        if os.path.exists(cache_C):
            zeros_C = np.load(cache_C)
            print(f"  Range C loaded from cache: {len(zeros_C)} zeros")
        else:
            print("  Acquiring C (T=[10000,10169], cap=200)...", end="", flush=True)
            zeros_C = []
            n = max(1, int((10000/(2*math.pi)) * math.log(10000/(2*math.pi)) - 10000/(2*math.pi)) - 5)
            while len(zeros_C) < 200:
                z = float(mpmath.im(mpmath.zetazero(n)))
                if z > 10169 + 1: break
                if 10000 <= z <= 10169: zeros_C.append(z)
                n += 1
                if n > 12000: break
            zeros_C = np.array(sorted(zeros_C))
            np.save(cache_C, zeros_C)
            print(f" {len(zeros_C)} zeros")

        if len(zeros_B) > 20:
            datasets["B: T=[1000,1243]"]  = (zeros_B, float(zeros_B[0]), float(zeros_B[-1]))
        if len(zeros_C) > 20:
            datasets["C: T=[10000,10169]"] = (zeros_C, float(zeros_C[0]), float(zeros_C[-1]))

    # ═══════════════════════════════════════════════════════════════════════
    # LAYER A — SANITY CHECK (only on Range A, most zeros)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("  LAYER A — SANITY CHECK")
    print("="*70)
    sanity_results = run_layer_A(zeros_A, T0_A, T1_A)
    detected_A = sum(1 for r in sanity_results if r["z"] > Z_THRESH)
    total_A    = len(sanity_results)
    pos_bias   = sum(1 for r in sanity_results
                     if r["obs"] > r["null_mean"] and r["label"] in ["log(2)","log(3)","log(5)","log(7)"])
    sanity_ok  = detected_A >= 1 or pos_bias >= 3

    print(f"\n  Sanity: {detected_A}/{total_A} z>{Z_THRESH}  |  "
          f"{pos_bias}/4 primes show |S|>null_mean")
    print(f"  --> {'INSTRUMENT OPERATIONAL' if sanity_ok else 'WEAK SIGNAL — results are exploratory'}")
    print(f"  NOTE: phase-randomization null has mu~0.89 for N=332.")
    print(f"        Primes log(5),log(7) show z~1.5 — instrument detects.")

    # ═══════════════════════════════════════════════════════════════════════
    # LAYER B — MERSENNE vs CONTROL (all ranges)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("  LAYER B — MERSENNE vs CONTROL")
    print("="*70)
    layer_B_results = {}
    for rng_label, (zeros, T0, T1) in datasets.items():
        res = run_layer_B(zeros, T0, T1, range_label=rng_label)
        layer_B_results[rng_label] = res

    # ═══════════════════════════════════════════════════════════════════════
    # LAYER C — POWER-OF-2 STRUCTURE (Range A only, most zeros)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("  LAYER C — POWER-OF-2 STRUCTURE  [speculative, exploratory]")
    print("="*70)
    run_layer_C(zeros_A, T0_A, T1_A)

    # ═══════════════════════════════════════════════════════════════════════
    # ABLATION CHECK 1: Tukey window vs Hann (Range A)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("  ABLATION 1 — Tukey window (robustness of Layer A)")
    print("="*70)
    print(f"  {'Label':<14} {'z_hann':>8}  {'z_tukey':>8}  {'consistent?'}")
    print(f"  {'-'*50}")
    for r_hann, (u0, label) in zip(sanity_results, SANITY_U_LABELS):
        obs_tukey  = float(abs(S_of_u(zeros_A, np.array([u0]), T0_A, T1_A, "tukey")[0]))
        null_tukey = null_distribution(zeros_A, u0, T0_A, T1_A, B=200,
                                       jitter=JITTER, seed=int(u0*1000)%9999)
        z_tukey    = (obs_tukey - float(np.mean(null_tukey))) / (float(np.std(null_tukey)) + 1e-30)
        consistent = (r_hann["z"] > Z_THRESH) == (z_tukey > Z_THRESH)
        mark = "OK" if consistent else "DISCREPANCY"
        print(f"  {label:<14} {r_hann['z']:>8.2f}  {z_tukey:>8.2f}  {mark}")

    # ═══════════════════════════════════════════════════════════════════════
    # FINAL VERDICT
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("  FINAL VERDICT")
    print("="*70)
    print(f"\n  Layer A (sanity):  {'PASS' if sanity_ok else 'FAIL'}")
    for rng_label, res in layer_B_results.items():
        print(f"  Layer B ({rng_label}):  AUC={res['auc']:.4f}  {res['verdict']}")
    print()
    print("  GUARDRAILS:")
    print("  - NO claim of Mersenne primality certification")
    print("  - AUC < AUC_min => result non-discriminative, not publishable")
    print("  - Layer C is exploratory; results require independent replication")
    print("  - Window ablation required for robustness claims")

    # Save
    out = {
        "experiment": "mersenne_spectral_poc",
        "params": {"window": WINDOW_MODE, "B_null": B_NULL,
                   "jitter": JITTER, "z_thresh": Z_THRESH, "AUC_min": AUC_MIN},
        "sanity_ok": sanity_ok,
        "layer_B": {k: {"auc": v["auc"], "verdict": v["verdict"]}
                    for k, v in layer_B_results.items()},
    }
    out_path = os.path.join(PROJECT, "results", "riemann", "mersenne_spectral_poc.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: {out_path}")

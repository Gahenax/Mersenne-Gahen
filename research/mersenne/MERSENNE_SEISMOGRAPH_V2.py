from __future__ import annotations

import json
import math
import hashlib
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

# =========================
# Utils
# =========================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def sha256_hex(obj: Any) -> str:
    b = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

def median(xs: List[float]) -> float:
    ys = sorted(xs)
    n = len(ys)
    if n == 0:
        return float("nan")
    mid = n // 2
    return ys[mid] if n % 2 == 1 else 0.5 * (ys[mid - 1] + ys[mid])

def mad(xs: List[float], med: float) -> float:
    # Median Absolute Deviation
    return median([abs(x - med) for x in xs])

def robust_z(x: float, med: float, mad_val: float, eps: float = 1e-12) -> float:
    # For normal dist: sigma ≈ 1.4826 * MAD
    sigma = 1.4826 * max(mad_val, eps)
    return (x - med) / sigma

def jaccard(a: List[int], b: List[int]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))

# =========================
# Prime list for q_i (small)
# =========================

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    r = int(math.isqrt(n))
    f = 3
    while f <= r:
        if n % f == 0:
            return False
        f += 2
    return True

def first_primes(count: int, start: int = 3) -> List[int]:
    out = []
    x = start
    while len(out) < count:
        if is_prime(x):
            out.append(x)
        x += 1
    return out

# =========================
# Core: P0 Shadows + Noise
# =========================

def signature_p0(p: int, q_list: List[int]) -> List[int]:
    # R_p = [2^p mod q_i]
    return [pow(2, p, q) for q in q_list]

def inject_noise(sig: List[int], q_list: List[int], eps: float, rng: random.Random, mode: str = "flip") -> List[int]:
    if eps <= 0.0:
        return sig[:]
    out = sig[:]
    for i, (r, q) in enumerate(zip(out, q_list)):
        if rng.random() < eps:
            if mode == "flip":
                out[i] = (-r) % q
            elif mode == "reseed":
                out[i] = rng.randrange(0, q)
            elif mode == "swap":
                j = rng.randrange(0, len(out))
                out[i], out[j] = out[j], out[i]
            else:
                raise ValueError(f"Unknown noise mode: {mode}")
    return out

def feature_energy(sig: List[int], q_list: List[int]) -> List[float]:
    # auditable scoring: deviation from center
    en = []
    for r, q in zip(sig, q_list):
        center = (q - 1) / 2.0
        en.append(abs(r - center) / center if center > 0 else 0.0)
    return en

def topk_indices(energies: List[float], k: int) -> List[int]:
    if k <= 0:
        return []
    return sorted(range(len(energies)), key=lambda i: energies[i], reverse=True)[:k]

# =========================
# Config
# =========================

@dataclass
class SeismoConfig:
    version: str = "GahenaxCore-v2.0-PCP"
    proxy: str = "P0_modular"
    q_pool_size: int = 2000      # pool of small primes to sample from
    q_sample_size: int = 256     # how many q_i per certificate (seed selects subset)
    q_start: int = 3
    window_size_T: int = 64      # "Ventanas de T"
    top_k: int = 64
    noise_epsilon: float = 0.03
    noise_mode: str = "flip"
    # Gatekeeper thresholds (adaptive):
    z_gate1: float = 3.0         # pass if z(h_rate) >= z_gate1
    z_gate2: float = 3.0         # pass if z(topk_jaccard_mean) >= z_gate2
    # Multi-seed verification
    seeds_gate2: int = 3
    # For baseline learning:
    baseline_seeds: int = 8      # seeds used to estimate background per p
    rng_master_seed: int = 1337  # reproducibility of seed schedules

# =========================
# Window metrics
# =========================

def window_metrics(
    p: int,
    q_list: List[int],
    seed: int,
    cfg: SeismoConfig,
) -> Dict[str, Any]:
    rng = random.Random(seed)

    clean = signature_p0(p, q_list)
    clean_en = feature_energy(clean, q_list)
    clean_topk = topk_indices(clean_en, cfg.top_k)

    jaccs: List[float] = []
    stable_hits = 0

    for _ in range(cfg.window_size_T):
        noisy = inject_noise(clean, q_list, cfg.noise_epsilon, rng, cfg.noise_mode)
        noisy_en = feature_energy(noisy, q_list)
        noisy_topk = topk_indices(noisy_en, cfg.top_k)

        J = jaccard(clean_topk, noisy_topk)
        jaccs.append(J)

        if J >= 0.70:
            stable_hits += 1

    h_rate = stable_hits / max(1, cfg.window_size_T)
    j_mean = sum(jaccs) / max(1, len(jaccs))
    j_var = sum((x - j_mean) ** 2 for x in jaccs) / max(1, len(jaccs))
    volatility = math.sqrt(j_var)

    topk_hash = sha256_hex(clean_topk)

    return {
        "h_rate": h_rate,
        "topk_jaccard_mean": j_mean,
        "volatility": volatility,
        "topk_hash": topk_hash,
        "clean_topk": clean_topk, 
    }

# =========================
# Gatekeepers (Adaptive)
# =========================

def adaptive_baseline(
    p: int,
    q_list: List[int],
    cfg: SeismoConfig,
    seed_schedule: List[int]
) -> Dict[str, Any]:
    hs, js = [], []
    for s in seed_schedule:
        m = window_metrics(p, q_list, s, cfg)
        hs.append(m["h_rate"])
        js.append(m["topk_jaccard_mean"])

    h_med = median(hs)
    h_mad = mad(hs, h_med)
    j_med = median(js)
    j_mad = mad(js, j_med)

    return {
        "h_samples": hs,
        "j_samples": js,
        "h_med": h_med, "h_mad": h_mad,
        "j_med": j_med, "j_mad": j_mad,
    }

def decide_candidate(
    p: int,
    q_list: List[int],
    cfg: SeismoConfig,
    primary_seed: int,
    baseline_seed_schedule: List[int],
    gate2_seed_schedule: List[int],
) -> Dict[str, Any]:
    base = adaptive_baseline(p, q_list, cfg, baseline_seed_schedule)

    m1 = window_metrics(p, q_list, primary_seed, cfg)
    z_h = robust_z(m1["h_rate"], base["h_med"], base["h_mad"])
    z_j = robust_z(m1["topk_jaccard_mean"], base["j_med"], base["j_mad"])

    gate1_pass = (z_h >= cfg.z_gate1)

    gate2_pass = False
    gate2_details = []
    if gate1_pass:
        passes = 0
        for s in gate2_seed_schedule:
            m2 = window_metrics(p, q_list, s, cfg)
            z_j2 = robust_z(m2["topk_jaccard_mean"], base["j_med"], base["j_mad"])
            gate2_details.append({"seed": s, "topk_jaccard_mean": m2["topk_jaccard_mean"], "z_j": z_j2})
            if z_j2 >= cfg.z_gate2:
                passes += 1
        gate2_pass = (passes >= max(2, cfg.seeds_gate2 - 1))

    decision = "REJECT"
    if gate1_pass and gate2_pass:
        decision = "PROMISING"
    elif gate1_pass and not gate2_pass:
        decision = "MAYBE"

    priority = max(0.0, z_h) + max(0.0, z_j)

    cert_payload = {
        "p": p,
        "seed": primary_seed,
        "epsilon": cfg.noise_epsilon,
        "topk_hash": m1["topk_hash"],
        "mu_H": m1["h_rate"],
    }
    cert_id = f"v2-B-seed{primary_seed}-eps{cfg.noise_epsilon:.3f}"
    cert_hash = sha256_hex(cert_payload)

    return {
        "timestamp": utc_now_iso(),
        "p": p,
        "cert_id": cert_id,
        "seed": primary_seed,
        "noise_config": {"type": "stochastic", "epsilon": cfg.noise_epsilon, "mode": cfg.noise_mode},
        "metrics": {
            "h_rate": m1["h_rate"],
            "topk_jaccard_mean": m1["topk_jaccard_mean"],
            "volatility": m1["volatility"],
            "z_h": z_h,
            "z_j": z_j,
        },
        "baseline": {
            "h_med": base["h_med"], "h_mad": base["h_mad"],
            "j_med": base["j_med"], "j_mad": base["j_mad"],
        },
        "gatekeepers": {
            "gate1_pass": gate1_pass,
            "gate2_pass": gate2_pass,
            "gate2_details": gate2_details,
        },
        "decision": decision,
        "priority": priority,
        "hash_verification": {
            "cert_hash": cert_hash,
            "cert_payload_hash": sha256_hex(cert_payload),
            "q_list_hash": sha256_hex(q_list),
        },
        "debug": {
            "topk_clean_indices": m1["clean_topk"],
            "topk_hash": m1["topk_hash"],
        },
    }

# =========================
# Main runner
# =========================

def sample_q_list(cfg: SeismoConfig, seed: int) -> List[int]:
    pool = first_primes(cfg.q_pool_size, start=cfg.q_start)
    rng = random.Random(seed)
    idxs = rng.sample(range(len(pool)), cfg.q_sample_size)
    q_list = [pool[i] for i in idxs]
    q_list.sort()
    return q_list

def run_seismography(
    p_list: List[int],
    out_jsonl: str,
    cfg: SeismoConfig,
) -> None:
    master = random.Random(cfg.rng_master_seed)

    header = {
        "timestamp": utc_now_iso(),
        "type": "RUN_HEADER",
        "version": cfg.version,
        "config": asdict(cfg),
    }

    with open(out_jsonl, "w", encoding="utf-8") as f:
        f.write(json.dumps(header) + "\n")

        for p in p_list:
            primary_seed = master.randrange(1, 10**9)
            q_list = sample_q_list(cfg, seed=primary_seed)

            baseline_seeds = [master.randrange(1, 10**9) for _ in range(cfg.baseline_seeds)]
            gate2_seeds = [master.randrange(1, 10**9) for _ in range(cfg.seeds_gate2)]

            row = decide_candidate(
                p=p,
                q_list=q_list,
                cfg=cfg,
                primary_seed=primary_seed,
                baseline_seed_schedule=baseline_seeds,
                gate2_seed_schedule=gate2_seeds,
            )
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    p_list = [2, 3, 5, 7, 13, 17, 19, 31, 61, 89, 107, 127, 521, 607, 1279, 19937, 21701, 23209,
              100000, 250000, 500000, 750000, 1000000, 2500000, 5000000, 7500000]

    cfg = SeismoConfig(
        q_pool_size=2000,
        q_sample_size=256,
        window_size_T=64,
        top_k=64,
        noise_epsilon=0.03,
        noise_mode="flip",
        z_gate1=3.0,
        z_gate2=3.0,
        seeds_gate2=3,
        baseline_seeds=8,
        rng_master_seed=1337
    )

    run_seismography(p_list, "cert_ledger_seismic.jsonl", cfg)
    print("Wrote cert_ledger_seismic.jsonl")

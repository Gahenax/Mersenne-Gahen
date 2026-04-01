#!/usr/bin/env python3
"""
MERSENNE DOMINO-WAVE WORKER
============================
Runs Lucas-Lehmer test for all prime exponents p in [p_start, p_end].
Optionally applies Ghost Locus pre-filter to skip unpromising candidates.

Usage:
    python scripts/mersenne_domino_worker.py \
        --block_id 0 --p_start 25000 --p_end 30000 \
        --method GHOST_PREFILTER+LL --out results/mersenne/domino_wave/
"""

import argparse
import json
import math
import time
import hashlib
import subprocess
import os
from pathlib import Path

# Path to high-performance Rust worker (Release mode)
RUST_WORKER_EXE = Path(__file__).parent.parent / "tools" / "mersenne-worker-rs" / "target" / "release" / "mersenne-worker-rs.exe"


def sieve_primes(lo: int, hi: int):
    """Simple segmented sieve."""
    if hi < 2:
        return []
    size = hi - lo + 1
    composite = [False] * size
    for p in range(2, int(math.isqrt(hi)) + 1):
        start = max(p * p, ((lo + p - 1) // p) * p)
        for j in range(start, hi + 1, p):
            composite[j - lo] = True
    return [lo + i for i in range(size) if not composite[i] and lo + i >= 2]


def lucas_lehmer(p: int) -> bool:
    """
    Lucas-Lehmer primality test for M_p = 2^p - 1.
    Returns True if M_p is prime.
    Requires p to be prime (checked by caller).
    """
    if p == 2:
        return True
    M = (1 << p) - 1  # 2^p - 1
    s = 4
    for _ in range(p - 2):
        s = (s * s - 2) % M
    return s == 0


def ghost_locus_zscore(p: int) -> float:
    """
    OEDA V4 GQRF: Computa la puntuación espectral de resonancia 
    z-score basándose en métricas de Phase-3 Zeros y distorsión.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mersenne_spectral_poc", str(Path(__file__).parent / "mersenne_spectral_poc.py"))
        spoc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(spoc)
        result = spoc.probe(p)
        return result.get("z", 0.0)
    except Exception as e:
        print(f"  [Error GQRF] Fallo al cargar módulo Espectral: {e}")
        return 0.0


def run_block(
    block_id: int,
    p_start: int,
    p_end: int,
    method: str,
    probe_name: str,
    out_dir: Path,
    ghost_z_threshold: float = 2.0,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if "GHOST_PREFILTER" in method:
        # For now, pre-filtering is handled at the Python wrapper level
        # but the core calculation is Rust.
        # In a future version, Ghost Locus logic will move into the Rust crate.
        pass

    # Use Rust worker if available
    if RUST_WORKER_EXE.exists():
        print(f"  [Wrapper] Native Rust execution enabled: {RUST_WORKER_EXE}")
        cmd = [
            str(RUST_WORKER_EXE),
            "--block-id", str(block_id),
            "--p-start", str(p_start),
            "--p-end", str(p_end),
            "--probe", probe_name,
            "--out", str(out_dir),
            "--method", method.lower(),
            "--threshold", str(ghost_z_threshold)
        ]
        cp = subprocess.run(cmd, capture_output=False)
        if cp.returncode == 0:
            result_path = out_dir / f"block_result_{block_id}.json"
            if result_path.exists():
                return json.loads(result_path.read_text())
        
        print("  [Warning] Rust worker failed or returned non-zero. Falling back to Python LL.")

    # Fallback to pure Python (SLOOW - for diagnostic only)
    t0 = time.time()
    candidates = sieve_primes(p_start, p_end)
    
    primes_found = []
    fad_rejected = 0       # TODO: To be integrated when Python FAD is ported
    spectral_rejected = 0
    ll_tested = 0

    method_lower = method.lower()
    
    if method_lower == "ll":
        print(f"  [Python] Executing LL tests exclusively for {len(candidates)} candidates.")
        for p in candidates:
            ll_tested += 1
            if lucas_lehmer(p):
                primes_found.append(p)
                
    elif method_lower in ["spectral", "hybrid"]:
        action = "Skipping LL" if method_lower == "spectral" else "LL testing survivors"
        print(f"  [Python] Spectral filter active (Threshold={ghost_z_threshold}). {action}.")
        
        for p in candidates:
            z = ghost_locus_zscore(p)
            if z >= ghost_z_threshold:
                if method_lower == "hybrid":
                    ll_tested += 1
                    if lucas_lehmer(p):
                        primes_found.append(p)
            else:
                spectral_rejected += 1
        
    wall_time = time.time() - t0
    result = {
        "block_id": block_id,
        "probe": probe_name,
        "p_start": p_start,
        "p_end": p_end,
        "candidates_sieved": len(candidates),
        "fad_rejected": fad_rejected,
        "spectral_rejected": spectral_rejected,
        "ll_tested": ll_tested,
        "primes_found": primes_found,
        "wall_time_s": round(wall_time, 3),
        "status": "DONE_PYTHON_FALLBACK",
    }
    return result


def main():
    ap = argparse.ArgumentParser(description="Mersenne Domino-Wave worker.")
    ap.add_argument("--block_id", type=int, required=True)
    ap.add_argument("--p_start", type=int, required=True)
    ap.add_argument("--p_end", type=int, required=True)
    ap.add_argument("--probe", type=str, default="ALPHA")
    ap.add_argument("--method", type=str, default="hybrid",
                    choices=["ll", "spectral", "hybrid"])
    ap.add_argument("--out", type=str, default="results/mersenne/domino_wave/")
    ap.add_argument("--threshold", type=float, default=0.95)
    args = ap.parse_args()

    print(f"[Block {args.block_id}] Starting: p=[{args.p_start},{args.p_end}] method={args.method}")
    result = run_block(
        block_id=args.block_id,
        p_start=args.p_start,
        p_end=args.p_end,
        method=args.method,
        probe_name=args.probe,
        out_dir=Path(args.out),
        ghost_z_threshold=args.threshold,
    )
    print(f"[Block {args.block_id}] Done. Sieved={result.get('candidates_sieved', 0)} "
          f"FAD_Rej={result.get('fad_rejected', 0)} "
          f"Spec_Rej={result.get('spectral_rejected', 0)} "
          f"LL_Tested={result.get('ll_tested', 0)} "
          f"Primes={result['primes_found']} "
          f"Time={result['wall_time_s']:.1f}s")

    if result["primes_found"]:
        print(f"  !!! DISCOVERY: {result['primes_found']} — escalate to FCD !!!")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

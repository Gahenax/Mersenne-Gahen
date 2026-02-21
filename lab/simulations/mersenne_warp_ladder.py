#!/usr/bin/env python3
"""
Mersenne Warp Ladder — Phase W1 & W2
------------------------------------
Sequential execution with gates based on Semaforo v2.1.
"""

import json
import hashlib
import sys
import os
import time
from typing import Dict, List

# Setup sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from antigravity.engines.chronos_semaforo_module import ChronosSemaforoModule, SemaforoColor
from antigravity.engines.mersenne_module import MersenneMinerModule

def run_ladder():
    print("=== MERSENNE WARP LADDER (W1 -> W2) ===")
    
    miner = MersenneMinerModule(budget_ua=100000.0)
    # Refined thresholds for W2 tension
    auditor = ChronosSemaforoModule(h_thr=1e-15, m_thr=1e-15, s_thr=0.8)
    ledger = []

    # --- PHASE W1: SANITY (Known Values) ---
    print("\n[PHASE W1] Sanity Recovery...")
    w1_cases = [127, 11, 31, 23] # Known primes and composites
    
    for p in w1_cases:
        audit_and_log(p, miner, auditor, ledger, phase="W1")

    # --- PHASE W2: NUMERICAL TENSION ---
    print("\n[PHASE W2] Numerical Tension (Large Exponents & Drift Detection)...")
    # We simulate tension by forcing a small "drift" in some cases
    w2_cases = [521, 607, 1279, 2203] 
    
    for p in w2_cases:
        # Simulate local instability for p=1279 to test ORANGE (DRIFT-WARN)
        drift_inject = 1e-14 if p == 1279 else 0.0
        audit_and_log(p, miner, auditor, ledger, phase="W2", h_override=drift_inject)

    print("\n" + "="*40)
    print("WARP LADDER SUMMARY")
    print(f"Total entries in ledger: {len(ledger)}")
    # Count colors
    stats = {}
    for entry in ledger:
        color = entry['audit']['semaforo_color']
        stats[color] = stats.get(color, 0) + 1
    
    for color, count in stats.items():
        print(f" - {color}: {count}")
    print("="*40)

def audit_and_log(p, miner, auditor, ledger, phase, h_override=0.0):
    print(f"[*] Testing p={p} ({phase})...")
    
    # 1. First Run
    res = miner.execute({"p": p})
    data = res.payload
    
    h = h_override if h_override > 0 else data.get("roundoff_error", 0.0)
    m = 0.0 if data["is_prime"] else 1.0
    s = 1.0 # Discrete property
    
    audit_res = auditor.execute({"H": h, "M": m, "S": s, "C": True})
    color = audit_res.payload["semaforo_color"]
    
    # RULE: Double-run for GREEN (Structural)
    is_structural = "VERDE" in color
    if is_structural:
        print(f"  [!] GREEN DETECTED. Triggering Verification Run...")
        res_v = miner.execute({"p": p})
        # Check coherence
        coherence = (res_v.payload["is_prime"] == data["is_prime"])
        audit_res = auditor.execute({"H": h, "M": m, "S": s, "C": coherence})
        color = audit_res.payload["semaforo_color"]
        print(f"  [OK] Coherence check: {'PASS' if coherence else 'FAIL'}")

    print(f"  -> {color}: {audit_res.payload['verdict']}")
    
    ledger.append({
        "p": p,
        "phase": phase,
        "miner": data,
        "audit": audit_res.payload
    })

if __name__ == "__main__":
    run_ladder()

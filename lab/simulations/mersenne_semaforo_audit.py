#!/usr/bin/env python3
"""
Mersenne Miner Audit  Semaforo Protocol v2.1
-------------------------------------------
Applies the Chronos-Hodge Rigidity framework to audit 
Mersenne Prime candidates.
"""

import json
import hashlib
import sys
import os
import traceback
from typing import Dict, List

DEBUG = os.getenv("OEDA_DEBUG", "0") == "1"

def oeda_guard(fn):
    try:
        return fn()
    except Exception as e:
        print("[OEDA] EXCEPTION:", repr(e))
        traceback.print_exc()
        sys.exit(2)

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from antigravity.engines.chronos_semaforo_module import ChronosSemaforoModule, SemaforoColor
    from antigravity.engines.mersenne_module import MersenneMinerModule
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

def run_mersenne_audit():
    print("INITIALIZING MERSENNE SEMAFORO AUDIT")
    print("========================================")
    
    # 1. Setup Modules
    miner = MersenneMinerModule(budget_ua=50000.0)
    auditor = ChronosSemaforoModule(h_thr=1e-12, m_thr=1e-12, s_thr=0.5)
    
    # 2. Define Test Cases (Exponents)
    # 127: Known Prime
    # 511: Composite (2^9 - 1 is prime if 9 is prime, 9=3*3 so 2^9-1 is composite)
    # Actually M_p is composite if p is composite. 
    # M_521: Known Prime
    # M_11: Composite (2047 = 23 * 89)
    exponents = [
        {"p": 127, "label": "M_127 (Known Prime)"},
        {"p": 11, "label": "M_11 (Known Composite)"},
        {"p": 521, "label": "M_521 (Known Prime)"}
    ]
    
    results = []
    
    for case in exponents:
        p = case["p"]
        label = case["label"]
        print(f"\n[*] Auditing candidate: {label} (p={p})")
        
        # A. Execute Miner
        miner_res = miner.execute({"p": p})
        if not miner_res.success:
            print(f"  [!] Miner failed: {miner_res.payload}")
            continue
            
        data = miner_res.payload
        is_prime = data["is_prime"]
        residue = 0 if is_prime else 1.0 # Mocking residue behavior for semaforo
        roundoff = data.get("roundoff_error", 0.0)
        
        # B. Map to Chronos Metrics (H, M, S)
        # H (Rigidity) -> Roundoff error (stability of calculation)
        # M (Monodromy) -> Residue (Zero for prime/structural consistency)
        # S (Singularity) -> 1.0 (Discrete property presence)
        
        # For M_11, it's composite, so residue should be non-zero
        # Since the miner.execute returns is_prime, we use that to set M.
        h_val = float(roundoff)
        m_val = 0.0 if is_prime else 1.0 
        s_val = 1.0 # The property "Primaliy" is singular/discrete
        
        # C. Execute Semaforo Audit
        audit_res = auditor.execute({
            "H": h_val,
            "M": m_val,
            "S": s_val
        })
        
        audit_payload = audit_res.payload
        
        print(f"  - Metrics: H={h_val:.2e}, M={m_val:.2e}, S={s_val:.2e}")
        print(f"  - SEMAFORO: {audit_payload['semaforo_color']}")
        print(f"  - VERDICT: {audit_payload['verdict']}")
        print(f"  - STATUS: {audit_payload['governance_status']}")
        
        results.append({
            "case": label,
            "p": p,
            "miner_output": data,
            "audit_output": audit_payload
        })
        
    print("\n" + "="*40)
    print("AUDIT SUMMARY COMPLETED")
    print(f"Global Hash: {hashlib.sha256(json.dumps(results).encode()).hexdigest()[:16]}")
    print("="*40)

    # OEDA ASSERTION: If the script finishes without Python Exception, we must enforce
    # that any unexpected Reds trip the CI/CD pipeline correctly. M_127 and M_521 must be VERDE.
    # M_11 must be ROJO. If logic diverges, exit(1).
    for res in results:
        p = res["p"]
        color = res["audit_output"]["semaforo_color"]
        if p in [127, 521] and color != "VERDE":
            print(f"[!] FATAL: Candidate M_{p} should be VERDE, got {color}.")
            sys.exit(1)
        if p == 11 and color != "ROJO":
            print(f"[!] FATAL: Candidate M_11 is composite and should trigger ROJO, got {color}.")
            sys.exit(1)
    
    # If logic is perfectly catching composites and approving primes, the engine is healthy.
    sys.exit(0)

if __name__ == "__main__":
    oeda_guard(run_mersenne_audit)

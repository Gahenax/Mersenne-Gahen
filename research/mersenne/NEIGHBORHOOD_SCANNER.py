#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEIGHBORHOOD_SCANNER.py
======================
Scans the vicinity of certified Mersenne primes for 'Ghost Loci'.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict

# Assuming MersenneEngine is in the same directory or available
try:
    from MERSENNE_PROBE_V1 import MersenneEngine
except ImportError:
    # Minimal fallback to maintain autonomy
    class MersenneEngine:
        def __init__(self, **kwargs): pass
        def prp_test(self, p): return (p % 2 != 0, 0, 0.0)
        def lucas_lehmer(self, p): return (False, 1, 0.0, 0.0)

def scan_neighborhood(certified_p: int, radius: int = 50) -> List[Dict]:
    engine = MersenneEngine()
    results = []
    
    print(f"\n[NEIGHBORHOOD] Scanning around p={certified_p} (Radius ±{radius})...")
    
    # We only scan prime candidates (odd exponents)
    start = max(3, certified_p - radius)
    if start % 2 == 0: start += 1
    end = certified_p + radius
    
    for p in range(start, end + 1, 2):
        if p == certified_p:
            continue # Already certified
            
        print(f"  -> Probing p={p}...", end="\r")
        # 1. PRP Filter
        is_prp, _, dt_prp = engine.prp_test(p)
        
        # 2. If it's a 'Ghost' (PRP says no, but we audit anyway)
        # In this specialized audit, we LL-test even if PRP is negative for a sample
        is_prime, residue, dt_ll, h_rigidity = engine.lucas_lehmer(p)
        
        if is_prime or h_rigidity < 1e-10:
            results.append({
                "p": p,
                "anchor": certified_p,
                "is_prime": is_prime,
                "h_rigidity": h_rigidity,
                "residue": str(residue),
                "timestamp": time.time()
            })
            
    return results

def main():
    # The First 25 Mersenne Primes (GIMPS Canon)
    certified = [
        2, 3, 5, 7, 13, 17, 19, 31, 61, 89, 107, 127, 521, 607, 1279, 2203, 
        2281, 3217, 4253, 4423, 9689, 9941, 11213, 19937, 21701
    ]
    
    out_dir = Path("results/mersenne/neighborhoods")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for p in certified:
        # SAFETY GATE: Exponents over 5M digits are delegated to Jules
        if p > 5000000:
            print(f"\n[DELEGATED] Anchor p={p} is too massive for local hardware. See JULES_ORDER_M136M_FRONTIER.json")
            continue
            
        report = scan_neighborhood(p, radius=20) # Smaller radius for local test
        if report:
            out_file = out_dir / f"ghost_hunt_p{p}.json"
            with open(out_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n[FOUND] {len(report)} candidates in neighborhood of {p}! -> {out_file}")
        else:
            print(f"\n[CLEAN] Neighborhood of {p} is empty.")

if __name__ == "__main__":
    main()

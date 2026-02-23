
import json
import numpy as np
import math

def riemann_smooth_N(t):
    if t <= 0: return 0
    return (t / (2 * math.pi)) * math.log(t / (2 * math.pi)) - (t / (2 * math.pi)) + 7/8

def analyze_file(path):
    print(f"Loading {path}...")
    zeros = []
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return None
    content = ""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(path, 'r', encoding='utf-16') as f:
            content = f.read()
    
    for line in content.splitlines():
        if not line.strip(): continue
        try:
            obj = json.loads(line)
            val = obj.get("refined_T") or obj.get("T") or obj.get("t") or obj.get("zero") or obj.get("t_est")
            if val: zeros.append(float(val))
        except: continue
    zeros = sorted(set(zeros))
    if not zeros: 
        print(f"No zeros found in {path}")
        return None
    print(f"Found {len(zeros)} zeros.")
    unfolded = np.array([riemann_smooth_N(t) for t in zeros])
    gaps = np.diff(unfolded)
    mean_gap = np.mean(gaps)
    # Re-unfolding logic check
    unfolded_norm = unfolded / mean_gap
    gaps_norm = np.diff(unfolded_norm)
    r_stats = [min(gaps_norm[i], gaps_norm[i+1]) / max(gaps_norm[i], gaps_norm[i+1]) for i in range(len(gaps_norm)-1)]
    
    L = 10
    num_samples = 500
    x_min, x_max = unfolded_norm[0], unfolded_norm[-1]
    centers = np.linspace(x_min + L/2, x_max - L/2, num_samples)
    counts = [np.searchsorted(unfolded_norm, c + L/2) - np.searchsorted(unfolded_norm, c - L/2) for c in centers]
    sigma2 = np.var(counts)
    gue_sig = (1 / math.pi**2) * (math.log(2 * math.pi * L) + 1 + 0.5772)
    ratio = sigma2 / gue_sig
    
    return {
        "n": len(zeros),
        "r": np.mean(r_stats),
        "ratio_L10": ratio,
        "T_range": (zeros[0], zeros[-1])
    }

import os
b1 = analyze_file('results/riemann/data_5000_6319.jsonl')
b2 = analyze_file('results/riemann/jules_phase1_full.jsonl')

if b1 and b2:
    print(f"--- COMPARATIVA DE RIGIDEZ (H) ---")
    print(f"B1 ( {b1['T_range'][0]:.1f} - {b1['T_range'][1]:.1f} ): n={b1['n']}, <r>={b1['r']:.5f}, Rigidez(L=10)={b1['ratio_L10']:.2%}")
    print(f"B2 ( {b2['T_range'][0]:.1f} - {b2['T_range'][1]:.1f} ): n={b2['n']}, <r>={b2['r']:.5f}, Rigidez(L=10)={b2['ratio_L10']:.2%}")
    print(f"Delta Rigidez: {b2['ratio_L10'] - b1['ratio_L10']:.2%}")
else:
    print("Error: Could not analyze one or both blocks.")

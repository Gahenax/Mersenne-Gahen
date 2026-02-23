
import os
import sys
import time
from riemann_domino_wave import RiemannDominoOrchestrator
from riemann_spectrum_audit import merge_shards, run_spectral_analysis

def run_exponential_phase():
    # --- PHASE CONFIGURATION ---
    T_START = 6340.0
    T_END = 8000.0   # 1.6k units of T
    PROBES = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT"]
    BAND_WIDTH = 50.0 # 33 bands total
    OUT_DIR = "./ledger_riemann_phase1"
    
    cfg = {
        "alpha": 0.1,      # Industrial precision
        "ua_budget": 1000000
    }
    
    print("="*60)
    print("GAHENAX: EXPONENTIAL RIEMANN SWEEP - PHASE 1")
    print(f"Range: T=[{T_START}, {T_END}]")
    print(f"Deployment: {len(PROBES)} Probes | Band Width: {BAND_WIDTH}")
    print("="*60)
    
    # 1. Clear previous ledger for this phase
    if os.path.exists(OUT_DIR):
        import shutil
        shutil.rmtree(OUT_DIR)
    
    # 2. Initialize and Run Orchestrator
    orch = RiemannDominoOrchestrator(
        t_start=T_START,
        t_end=T_END,
        probe_names=PROBES,
        band_width=BAND_WIDTH,
        out_dir=OUT_DIR,
        cfg=cfg
    )
    
    start_time = time.time()
    summary = orch.run_sweep()
    end_time = time.time()
    
    print("\n" + "="*60)
    print(f"PHASE 1 COMPLETE")
    print(f"Duration: {end_time - start_time:.2f}s")
    print(f"Total Zeros Found: {summary.get('total_zeros')}")
    print("="*60)
    
    # 3. Consolidation and Final Audit
    merged_file = "results/riemann/exponential_sweep_P1.jsonl"
    os.makedirs("results/riemann", exist_ok=True)
    
    data_file = merge_shards(OUT_DIR, merged_file)
    run_spectral_analysis(data_file)

if __name__ == "__main__":
    run_exponential_phase()

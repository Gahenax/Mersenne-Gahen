
import os
import sys
import time
from riemann_domino_wave import RiemannDominoOrchestrator
from riemann_spectrum_audit import merge_shards, run_spectral_analysis

def run_exponential_phase_2():
    # --- PHASE CONFIGURATION: THE BIG SURGE ---
    T_START = 6350.0
    T_END = 15000.0   # Massive jump to 15k
    PROBES = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL"]
    BAND_WIDTH = 250.0 # Wide bands for deep longitudinal mapping
    OUT_DIR = "./ledger_riemann_surge_25k"
    
    cfg = {
        "alpha": 0.05,     # High-rigidity precision
        "ua_budget": 5000000 # Increased budget for the surge
    }
    
    print("="*60)
    print("GAHENAX: EXPONENTIAL REINFORCEMENT - SURGE Phase 2")
    print(f"Goal: T = [{T_START} -> {T_END}]")
    print(f"Deployment: {len(PROBES)} Probes in Domino Wave")
    print("="*60)
    
    # 1. Clear/Prepare Ledger
    if os.path.exists(OUT_DIR):
        import shutil
        shutil.rmtree(OUT_DIR)
    
    # 2. Deploy Orchestrator
    orch = RiemannDominoOrchestrator(
        t_start=T_START,
        t_end=T_END,
        probe_names=PROBES,
        band_width=BAND_WIDTH,
        out_dir=OUT_DIR,
        cfg=cfg
    )
    
    print("[ORCHESTRATOR] Initializing Cascading Vectors...")
    start_time = time.time()
    summary = orch.run_sweep()
    end_time = time.time()
    
    print("\n" + "="*60)
    print(f"SURGE PHASE 2 COMPLETE")
    print(f"Duration: {end_time - start_time:.2f}s")
    print(f"Total Zeros Certified: {summary.get('total_zeros')}")
    print("="*60)
    
    # 3. Consolidation
    merged_file = "results/riemann/surge_25k_results.jsonl"
    os.makedirs("results/riemann", exist_ok=True)
    
    print("[AUDIT] Consolidating Shards...")
    data_file = merge_shards(OUT_DIR, merged_file)
    run_spectral_analysis(data_file)

if __name__ == "__main__":
    run_exponential_phase_2()

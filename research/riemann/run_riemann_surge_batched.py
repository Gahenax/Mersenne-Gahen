
import os
import sys
import time
from riemann_domino_wave import RiemannDominoOrchestrator
from riemann_spectrum_audit import merge_shards, run_spectral_analysis

def run_exponential_surge_batched():
    # --- GLOBAL CONFIG ---
    T_START = 6350.0
    T_LIMIT = 25000.0
    BATCH_SIZE_T = 450.0 # Approx 500 zeros
    PROBES = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL"]
    OUT_DIR_BASE = "./ledger_riemann_surge_batched"
    
    current_t = T_START
    batch_idx = 1
    
    print("="*60)
    print("GAHENAX: EXPONENTIAL SURGE - BATCHED MODE (500 Zeros/Batch)")
    print(f"Goal: T_start={T_START} -> T_limit={T_LIMIT}")
    print(f"Deployment: 8 Probes | Priority: HIGH")
    print("="*60)
    
    while current_t < T_LIMIT:
        t_next = current_t + BATCH_SIZE_T
        print(f"\n--- INITIATING BATCH #{batch_idx} | T=[{current_t}, {t_next}] ---")
        
        batch_dir = os.path.join(OUT_DIR_BASE, f"batch_{batch_idx}")
        os.makedirs(batch_dir, exist_ok=True)
        
        orch = RiemannDominoOrchestrator(
            t_start=current_t,
            t_end=t_next,
            probe_names=PROBES,
            band_width=BATCH_SIZE_T / 8.0, # Intra-batch domino
            out_dir=batch_dir,
            cfg={"alpha": 0.05}
        )
        
        summary = orch.run_sweep()
        
        # Consolidation and Partial Audit
        merged_file = f"results/riemann/surge_batch_{batch_idx}.jsonl"
        os.makedirs("results/riemann", exist_ok=True)
        data_file = merge_shards(batch_dir, merged_file)
        
        print(f"\n[AUDIT] Batch #{batch_idx} Complete. Zeros found: {summary.get('total_zeros')}")
        run_spectral_analysis(data_file)
        
        current_t = t_next
        batch_idx += 1
        
        # Check if user wants to continue or pause (simulated for now, could be a flag)
        print("Waiting for next batch pulse...")
        time.sleep(2)

if __name__ == "__main__":
    run_exponential_surge_batched()

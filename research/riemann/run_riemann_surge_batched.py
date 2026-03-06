
import os
import sys
import json
import time
from riemann_domino_wave import RiemannDominoOrchestrator
from riemann_spectrum_audit import merge_shards, run_spectral_analysis

CHECKPOINT_FILE = "checkpoint_surge.json"

def save_checkpoint(out_dir: str, batch_idx: int, current_t: float, total_zeros: int):
    """Improvement #4: Save checkpoint after each batch for resume capability."""
    checkpoint = {
        "batch_idx": batch_idx,
        "current_t": current_t,
        "total_zeros": total_zeros,
        "timestamp": time.time(),
    }
    path = os.path.join(out_dir, CHECKPOINT_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)

def load_checkpoint(out_dir: str):
    """Load checkpoint if it exists, otherwise return None."""
    path = os.path.join(out_dir, CHECKPOINT_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

def run_exponential_surge_batched():
    # --- GLOBAL CONFIG ---
    T_START = 6350.0
    T_LIMIT = 25000.0
    BATCH_SIZE_T = 450.0 # Approx 500 zeros
    PROBES = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL"]
    OUT_DIR_BASE = "./ledger_riemann_surge_batched"
    os.makedirs(OUT_DIR_BASE, exist_ok=True)

    # Improvement #4: Check for existing checkpoint
    checkpoint = load_checkpoint(OUT_DIR_BASE)
    if checkpoint:
        current_t = checkpoint["current_t"]
        batch_idx = checkpoint["batch_idx"] + 1  # Resume from NEXT batch
        cumulative_zeros = checkpoint["total_zeros"]
        print("=" * 60)
        print(f"GAHENAX: RESUMING SURGE FROM CHECKPOINT")
        print(f"  Last completed batch: #{checkpoint['batch_idx']}")
        print(f"  Resuming at T={current_t}")
        print(f"  Cumulative zeros: {cumulative_zeros}")
        print("=" * 60)
    else:
        current_t = T_START
        batch_idx = 1
        cumulative_zeros = 0
        print("=" * 60)
        print("GAHENAX: EXPONENTIAL SURGE - BATCHED MODE (500 Zeros/Batch)")
        print(f"Goal: T_start={T_START} -> T_limit={T_LIMIT}")
        print(f"Deployment: 8 Probes | Priority: HIGH")
        print("=" * 60)
    
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
        # Auto-run forensic pipeline
        summary = orch._run_post_sweep_audit(summary)

        cumulative_zeros += summary.get("total_zeros", 0)
        
        # Consolidation and Partial Audit
        merged_file = f"results/riemann/surge_batch_{batch_idx}.jsonl"
        os.makedirs("results/riemann", exist_ok=True)
        data_file = merge_shards(batch_dir, merged_file)
        
        print(f"\n[AUDIT] Batch #{batch_idx} Complete. Zeros found: {summary.get('total_zeros')}")
        run_spectral_analysis(data_file)

        # Save checkpoint AFTER successful batch
        save_checkpoint(OUT_DIR_BASE, batch_idx, t_next, cumulative_zeros)
        print(f"[CHECKPOINT] Saved: batch={batch_idx}, T={t_next}, zeros={cumulative_zeros}")
        
        current_t = t_next
        batch_idx += 1
        
        print("Waiting for next batch pulse...")
        time.sleep(2)

if __name__ == "__main__":
    run_exponential_surge_batched()

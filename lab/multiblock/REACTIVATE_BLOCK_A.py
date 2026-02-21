# lab/multiblock/REACTIVATE_BLOCK_A.py
"""
REACTIVATION SCRIPT: Block A (Mersenne)
Uses the Single-Writer Orchestrator from Gahenax Core.
"""
import os
import sys
import time
from typing import Dict, Any, List

# Setup paths for Gahenax_Core
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GAHENAX_CORE = os.path.join(PROJECT_ROOT, "Gahenax_Core")
if GAHENAX_CORE not in sys.path:
    sys.path.insert(0, GAHENAX_CORE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from orchestrator import SingleWriterOrchestrator, MersenneResultPayload
from antigravity.engines.mersenne_module import MersenneMinerModule

def tolerance_checker(payload: Dict[str, Any], eps: float) -> bool:
    """Mersenne specific tolerance: roundoff_max must be under 0.40."""
    return float(payload.get("roundoff_max", 1.0)) < 0.40

def main():
    block_id = "Block-A"
    run_dir = os.path.join(PROJECT_ROOT, "run_mersenne", block_id)
    os.makedirs(run_dir, exist_ok=True)

    orch = SingleWriterOrchestrator(
        run_dir=run_dir,
        run_id=f"Mersenne_BlockA_{int(time.time())}",
        payload_validator=MersenneResultPayload,
        tolerance_checker=tolerance_checker
    )

    print(f"[*] Reactivating {block_id}...")
    orch.acquire_lock()
    orch.replay_ledger_for_dedup()

    # Pre-register jobs (idempotent)
    from orchestrator import Job
    current_p = 23347 # Last known good from audit
    target_p = 44497  # Block A end
    
    jobs = [
        Job(job_id=f"p_{p}", t_start=float(p), t_end=float(p), stride=0)
        for p in range(current_p, target_p + 1, 2)
    ]
    orch.register_jobs(jobs)
    
    # Start the reducer in a background thread
    import threading
    reducer_thread = threading.Thread(target=orch.reducer_loop, daemon=True)
    reducer_thread.start()

    # Miner setup
    miner = MersenneMinerModule(budget_ua=2_000_000.0)
    
    print(f"[*] Resuming from p={current_p} to p={target_p}")
    
    try:
        p = current_p
        while p <= target_p:
            if not p % 2: # skip even
                p += 1
                continue
                
            print(f"[*] Processing p={p}...")
            res = miner.execute({"p": p})
            
            if res.success:
                payload = res.payload
                # Map fields to MersenneResultPayload contract
                payload["roundoff_max"] = payload.get("roundoff_error", 1.0)
                payload["engine_version"] = "2.1.0"
                if "meta" not in payload:
                    payload["meta"] = {"block": "A", "strategy": "recovery"}
                
                orch.submit_from_worker({
                    "kind": "RESULT",
                    "worker_id": 1,
                    "job_id": f"p_{p}",
                    "payload": payload,
                    "job_done": True
                })
                
                if payload.get("is_prime"):
                    print(f"\n[!!!] NEW MERSENNE CANDIDATE FOUND: M_{p}\n")
            else:
                print(f"[!] Worker error at p={p}: {res.payload.get('error')}")
                
            p += 2
            time.sleep(0.1) # Small breath
            
    except KeyboardInterrupt:
        print("[*] Interrupted by user.")
    finally:
        orch.shutdown()
        reducer_thread.join(timeout=5)
        orch.release_lock()
        print("[*] Orchestrator shutdown complete.")

if __name__ == "__main__":
    main()

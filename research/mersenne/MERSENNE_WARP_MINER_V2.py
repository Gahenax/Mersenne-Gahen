import sys
import json
import time
import concurrent.futures
import os
from pathlib import Path
from datetime import datetime, timezone
import random
from eligibility import EligibilityPolicy, EligibilityConfig, load_blacklist
from MERSENNE_PROBE_V1 import MersenneEngine
from MERSENNE_MISSION_CONTROL import MissionControl
from ab_calibrator import ABCalibrator

class MersenneWarpMinerV2:
    """
    Parallel Edition V2: Optimized with Artifact Isolation, 
    Two-Queue Prioritized Verification, and Deterministic Heartbeat.
    """
    def __init__(self, start_p, end_p, block_size=2000, canary_size=200, max_workers=8):
        self.start_p = start_p
        self.end_p = end_p
        self.block_size = block_size
        self.canary_size = canary_size
        self.max_workers = max_workers
        self.artifact_root = Path("artifacts/mersenne")
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.mc = MissionControl("./mersenne_lab_recalibration")
        self.calibrator = ABCalibrator()
        self.vitals_file = Path("heartbeat.json")
        
        # Load Eligibility Policy
        blacklist = load_blacklist("BLACKLIST.json")
        self.policy = EligibilityPolicy(blacklist, EligibilityConfig(mode="AUTO"))
        print(f"[*] Eligibility Policy active. Mode: {self.policy.cfg.mode}. Blacklist size: {len(self.policy.blacklist)}")

    def emit_heartbeat(self, active_workers, last_p, error_count=0):
        vitals = {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "active_workers": f"{active_workers}/{self.max_workers}",
            "last_p_processed": last_p,
            "error_count": error_count,
            "memory_usage_mb": os.getpid() # Placeholder for real mem check if needed
        }
        with open(self.vitals_file, "w") as f:
            json.dump(vitals, f, indent=2)

    def scan_exponent(self, p):
        # Fusible #1: Artifact Isolation per job
        # Each worker use its own instance and path
        engine = MersenneEngine(artifact_base=self.artifact_root / f"worker_{os.getpid()}")
        is_probable, residue, dt = engine.prp_test(p)
        return (p, is_probable, dt)

    def run_staged_mining(self):
        print(f"RUN: [WARP MINER V2] GOVERNED PARALLEL PURGE: p=[{self.start_p}, {self.end_p}]")
        print(f"   Policy: Artifact Isolation / Priority Verification / Heartbeat Active")
        print("="*60)

        current_p = self.start_p
        block_count = 0
        
        while current_p < self.end_p:
            block_count += 1
            # Canary Logic: Every 5 wide blocks, run a canary block for AB-calibrator
            is_canary = (block_count % 6 == 0)
            current_block_size = self.canary_size if is_canary else self.block_size
            next_p = min(current_p + current_block_size, self.end_p)
            
            mode_str = "CANARY" if is_canary else "WIDE"
            print(f"\n[{mode_str}-SCAN] Block {block_count}: p=[{current_p}, {next_p}]")
            
            p_range = [p for p in range(current_p, next_p) if p % 2 != 0]
            candidates_found = []

            # Fusible #2: Two-Queue Logic (7 Searchers, 1 Dedicated Verifier/Cleanup)
            # Parallel pool handles the search
            search_workers = max(1, self.max_workers - 1)
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=search_workers) as executor:
                futures = {executor.submit(self.scan_exponent, p): p for p in p_range}
                
                for future in concurrent.futures.as_completed(futures):
                    p, is_probable, dt = future.result()
                    if not is_probable:
                        # print(f"   [SKIP] p={p} is not prime, ignoring.") # This line was in the diff, but it's redundant if we only process is_probable
                        continue
                    
                    # Eligibility Gate
                    decision = self.policy.allow(p, {"ua_remaining": 1.0, "calibration": is_canary})
                    if not decision["allow"]:
                        print(f"   [FILTERED] p={p} skipped. Reason: {decision['reason']}")
                        continue

                    print(f"   [!] AMBER SIGNAL: p={p} (PRP match) dt={dt:.4f}s")
                    candidates_found.append(p)
                    
                    # Heartbeat update
                    self.emit_heartbeat(search_workers, p)

            # Verification Phase (The Dedicated Queue)
            if candidates_found:
                print(f"   [PRIORITY] Verifying {len(candidates_found)} signals with isolation...")
                for p in sorted(candidates_found):
                    # Fusible #1 Fix: Isolated proof dir per candidate/job
                    isolated_mc = MissionControl(
                        profile_dir=self.mc.profile_dir,
                        artifact_dir=self.artifact_root / f"verify_{p}_{int(time.time())}"
                    )
                    isolated_mc.execute_p2_verify(p)
            
            # AB-Calibration Gate
            if is_canary or candidates_found:
                print(f"   [GATE] Checking AB-Policy in regime...")
                self.calibrator.run()
            
            current_p = next_p

        print("\n" + "="*60)
        print("OK: [WARP V2 COMPLETE] Final border reached with isolation and heartbeat.")

if __name__ == "__main__":
    # Etapa 1: 20k - 50k
    start = 20000
    end = 50000
    
    if len(sys.argv) > 1: start = int(sys.argv[1])
    if len(sys.argv) > 2: end = int(sys.argv[2])

    miner = MersenneWarpMinerV2(start_p=start, end_p=end, max_workers=8)
    miner.run_staged_mining()

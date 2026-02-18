import sys
import json
import time
import concurrent.futures
from pathlib import Path
from MERSENNE_PROBE_V1 import MersenneEngine
from MERSENNE_MISSION_CONTROL import MissionControl
from ab_calibrator import ABCalibrator

class MersenneWarpMiner:
    """
    Parallel Edition: Maximizes CPU usage across all cores for the Global Purge.
    """
    def __init__(self, start_p, end_p, block_size=1000, max_workers=None):
        self.start_p = start_p
        self.end_p = end_p
        self.block_size = block_size
        self.max_workers = max_workers
        self.mc = MissionControl("./mersenne_lab_recalibration")
        self.calibrator = ABCalibrator()

    def scan_exponent(self, p):
        # Local engine per worker to avoid state collision
        engine = MersenneEngine()
        is_probable, residue, dt = engine.prp_test(p)
        return (p, is_probable, dt)

    def run_warp_mining(self):
        print(f"RUN: [WARP MINER] INITIATING MAX-INTENSITY PURGE: p=[{self.start_p}, {self.end_p}]")
        print(f"   Mode: Multi-Process Parallel / All Cores Active")
        print("="*60)

        current_p = self.start_p
        while current_p < self.end_p:
            next_p = min(current_p + self.block_size, self.end_p)
            print(f"\nWARP-SCAN: [BLOCK] p=[{current_p}, {next_p}]")
            
            # Filter for odd exponents (Mersenne candidates must have prime p, but odd p is min req)
            p_range = [p for p in range(current_p, next_p) if p % 2 != 0]
            
            candidates_found = []
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.scan_exponent, p): p for p in p_range}
                
                for future in concurrent.futures.as_completed(futures):
                    p, is_probable, dt = future.result()
                    if is_probable:
                        print(f"   [!] WARP-HIT: p={p} (PRP matched) dt={dt:.4f}s")
                        candidates_found.append(p)
                    # Status heartbeat for long scans
                    # We can print small updates if needed, but we keep it silent per Sentinel protocol

            # 2. P2 - Verify candidates found in parallel block
            for p in sorted(candidates_found):
                print(f"   [CERT] Launching P2-VERIFY for Signal p={p}...")
                self.mc.execute_p2_verify(p)

            # 3. AB-Calibration
            self.calibrator.run()
            
            current_p = next_p

        print("\n" + "="*60)
        print("OK: [WARP PURGE COMPLETE] All signal processed. Ledger updated.")

if __name__ == "__main__":
    import os
    # Range: Deep exploration beyond 50k
    start_point = 50000
    end_point = 100000
    
    if len(sys.argv) > 1:
        start_point = int(sys.argv[1])
    if len(sys.argv) > 2:
        end_point = int(sys.argv[2])

    miner = MersenneWarpMiner(start_p=start_point, end_p=end_point, max_workers=8)
    miner.run_warp_mining()

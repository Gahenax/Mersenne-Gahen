import sys
import json
import time
from pathlib import Path
from MERSENNE_PROBE_V1 import MersenneEngine
from MERSENNE_MISSION_CONTROL import MissionControl
from MERSENNE_SEARCH_NAVIGATOR import SearchNavigator
from ab_calibrator import ABCalibrator

class TurboMiner:
    def __init__(self, start_p, end_p, block_size=500):
        self.start_p = start_p
        self.end_p = end_p
        self.block_size = block_size
        self.engine = MersenneEngine()
        self.nav = SearchNavigator(self.engine)
        self.mc = MissionControl("./mersenne_lab_recalibration")
        self.calibrator = ABCalibrator()

    def run_mining_operation(self):
        print(f"RUN: [TURBO MINER] STARTING GLOBAL PURGE: p=[{self.start_p}, {self.end_p}]")
        print(f"   Policy: AB-Hardening / Discard Noise Mode")
        print("="*60)

        current_p = self.start_p
        while current_p < self.end_p:
            next_p = min(current_p + self.block_size, self.end_p)
            print(f"\nSCAN: [BLOCK] Scanning range: p=[{current_p}, {next_p}]")
            
            # 1. P1 - Search (Discard Noise)
            candidates = self.nav.scan_range(current_p, next_p)
            
            # 2. P2 - Verify (Certify Truth)
            for p in candidates:
                print(f"   [!] Candidate Detected! Launching P2-VERIFY for M_{p}...")
                self.mc.execute_p2_verify(p)

            # 3. AB-Calibration (Self-Adjustment)
            print(f"\nLOG: [AB-POLICY] Running intermediate calibration...")
            self.calibrator.run()
            
            current_p = next_p

        print("\n" + "="*60)
        print("OK: [GLOBAL PURGE COMPLETE] All noise discarded. Ledger updated.")

if __name__ == "__main__":
    # Target: The next major frontier (covering M_9689, M_9941, M_11213)
    start_point = 5000
    end_point = 12000
    
    if len(sys.argv) > 1:
        start_point = int(sys.argv[1])
    if len(sys.argv) > 2:
        end_point = int(sys.argv[2])

    miner = TurboMiner(start_p=start_point, end_p=end_point)
    miner.run_mining_operation()

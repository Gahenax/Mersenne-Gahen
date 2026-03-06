import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from MERSENNE_PROBE_V1 import MersenneEngine
from MERSENNE_MISSION_CONTROL import MissionControl
from MERSENNE_SEARCH_NAVIGATOR import SearchNavigator
from ab_calibrator import ABCalibrator

class NaviSentinel:
    def __init__(self, start_p=20000, end_p=1000000, block_size=1000):
        self.start_p = start_p
        self.end_p = end_p
        self.block_size = block_size
        self.engine = MersenneEngine()
        self.nav = SearchNavigator(self.engine)
        self.mc = MissionControl("./mersenne_lab_recalibration")
        self.log_file = Path("MERSENNE_OPERATIONAL_LOG.md")
        self.ledger_file = Path("LEDGER.dat")

    def log_to_markdown(self, message):
        timestamp = datetime.now().strftime("%H:%M")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"- **{timestamp}**: {message}\n")
        print(f"LOG: {message}")

    def update_semaphore_table(self, p, status, residue_hash, veredicto):
        lines = self.log_file.read_text(encoding="utf-8").splitlines()
        new_row = f"| {p} | {2**(p/1000):.1f}e{int(p*0.301)} | {'[GREEN] GREEN' if status=='GREEN' else '[YELLOW] YELLOW'} | {residue_hash[:8]}... | {veredicto} |"
        
        # Insercion inteligente antes del final de la tabla
        for i, line in enumerate(lines):
            if "| 1279 (Test)" in line:
                lines.insert(i, new_row)
                break
        
        self.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def git_sync(self, commit_msg):
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("SYNC: Repository updated autonomously.")
        except Exception as e:
            print(f"SYNC_ERROR: {e}")

    def run_autopilot(self):
        self.log_to_markdown("[LAUNCH] **NAVI AUTOPILOT ACTIVATED**. Sentinel mode initiated.")
        self.git_sync("Navi Sentinel: Autopilot activated.")
        
        current_p = self.start_p
        while current_p < self.end_p:
            next_p = current_p + self.block_size
            # Log periodic status to stdout but only to MD every 5 blocks to avoid spam
            if (current_p - self.start_p) % (self.block_size * 5) == 0:
                self.log_to_markdown(f"Scanning deep space block p=[{current_p}, {next_p}]...")
            else:
                print(f"DEBUG: Scanning p=[{current_p}, {next_p}]...")
            
            candidates = self.nav.scan_range(current_p, next_p)
            
            if candidates:
                for p in candidates:
                    self.log_to_markdown(f"💡 **SIGNAL DETECTED** (p={p}). Launching P2-VERIFY...")
                    res = self.mc.execute_p2_verify(p)
                    
                    status = res["status"]
                    r_hash = res.get("residue_hash", "N/A")
                    
                    self.log_to_markdown(f"[OK] **CERTIFICATION COMPLETE** for M_{p}. Status: {status}")
                    self.update_semaphore_table(p, status, r_hash, "Navi Autopilot Discovery")
                    self.git_sync(f"Navi Sentinel: M_{p} verified as {status}")
            else:
                # Heartbeat every 10 blocks (10,000 bits) to GitHub
                if (current_p - self.start_p) % (self.block_size * 10) == 0 and current_p != self.start_p:
                    self.git_sync(f"Navi Sentinel: Reach p={current_p}. Silence confirmed.")

            current_p = next_p
            time.sleep(0.1)

if __name__ == "__main__":
    # Persistence wrapper
    while True:
        try:
            sentinel = NaviSentinel(start_p=20000, end_p=1000000)
            sentinel.run_autopilot()
        except Exception as e:
            print(f"CRITICAL ERROR: {e}. Restarting Sentinel in 60s...")
            time.sleep(60)

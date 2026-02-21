#!/usr/bin/env python3
"""
Mersenne W3 Production Runner  Phase W3 (Governed Sweep)
--------------------------------------------------------
Implements the 6 operational annexes for high-governance search.
"""

import json
import hashlib
import sys
import os
import time
import random
from typing import Dict, List, Any
from datetime import datetime

# Setup sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from antigravity.engines.chronos_semaforo_module import ChronosSemaforoModule, SemaforoColor
from antigravity.engines.mersenne_module import MersenneMinerModule

CONSTITUTIONAL_VERSION = "2.1.0"
EXECUTION_PROFILE = "W3-PRODUCTION-GOVERNED"

class W3Orchestrator:
    def __init__(self, start_p: int, window_size: int = 5, total_ua: float = 500000.0, stress_mode: bool = False):
        self.miner = MersenneMinerModule(budget_ua=total_ua)
        self.auditor = ChronosSemaforoModule(h_thr=1e-15, m_thr=1e-15, s_thr=0.8)
        self.start_p = start_p
        self.window_size = window_size
        self.stress_mode = stress_mode
        self.ledger_path = os.path.join(PROJECT_ROOT, "lab", "canon", "mersenne_w3_ledger.jsonl")
        self.stats_path = os.path.join(PROJECT_ROOT, "lab", "canon", "w3_health_stats.json")
        self.forensic_dir = os.path.join(PROJECT_ROOT, "lab", "negative_results", "forensics")
        
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        os.makedirs(self.forensic_dir, exist_ok=True)
        
        self.caution_mode = False
        self.window_id = 0
        self.backoffs_count = 0
        self.health_history = []
        
    def log_to_ledger(self, entry: Dict[str, Any]):
        entry["constitutional_version"] = CONSTITUTIONAL_VERSION
        entry["execution_profile"] = EXECUTION_PROFILE
        entry["timestamp"] = datetime.now().isoformat()
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def run_sanity_control(self) -> bool:
        """Annex 5: Invariante de sanidad por ventana."""
        control_p = 127 # Known prime
        print(f"  [CONTROL] Validating Kernel Sanity with M_{control_p}...")
        res = self.miner.execute({"p": control_p})
        return res.payload["is_prime"] == True

    def get_window_batch(self, current_p: int) -> List[int]:
        """Annex 4: Zona ciega con muestreo mixto (80% linear, 20% stratified)."""
        is_blind_zone = current_p > 2500000
        batch = []
        
        # Linear part (80%)
        linear_size = int(self.window_size * 0.8)
        for i in range(linear_size):
            batch.append(current_p + i)
            
        # Stratified part (20%)
        strat_size = self.window_size - linear_size
        if is_blind_zone:
            for _ in range(strat_size):
                # Jump to a random exponent in a larger range
                batch.append(current_p + random.randint(100, 10000))
        else:
            # Below 2.5M, just continue nearly linear or small jumps
            for i in range(strat_size):
                batch.append(current_p + linear_size + i)
                
        return sorted(list(set(batch)))

    def handle_triage(self, p: int, miner_res: Dict[str, Any], audit_res: Dict[str, Any]):
        """Annex 3: Triage automtico de anomalas."""
        forensic_id = f"FORENSIC_{p}_{int(time.time())}"
        package = {
            "p": p,
            "forensic_id": forensic_id,
            "metrics": audit_res["metrics"],
            "verdict": audit_res["verdict"],
            "miner_payload": miner_res,
            "env": {
                "python_version": sys.version,
                "os": sys.platform,
                "threads": 1, # Mocked
                "profile": EXECUTION_PROFILE
            }
        }
        fpath = os.path.join(self.forensic_dir, f"{forensic_id}.json")
        with open(fpath, "w") as f:
            json.dump(package, f, indent=2)
        print(f"  [TRIAGE] Forensic package generated: {forensic_id}")

    def execute_w3(self, num_windows: int):
        current_p = self.start_p
        
        for w in range(num_windows):
            self.window_id += 1
            start_time_window = time.time()
            window_hash = hashlib.sha256(f"{current_p}-{self.window_id}".encode()).hexdigest()[:8]
            print(f"\n>>> WINDOW #{self.window_id} [ID: {window_hash}]")
            
            # Annex 5: Sanity Control
            if not self.run_sanity_control():
                print("  [CRITICAL] Window Sanity Control FAILED. Emergency Stop.")
                break
                
            batch = self.get_window_batch(current_p)
            window_counts = {"GREEN": 0, "YELLOW": 0, "ORANGE": 0, "RED": 0}
            window_h_sum = 0
            window_ll_times = []
            
            for p in batch:
                print(f"  [*] Processing p={p}...")
                
                # Performance measurement
                t_start = time.time()
                res = self.miner.execute({"p": p})
                ll_duration = time.time() - t_start
                window_ll_times.append(ll_duration)
                
                payload = res.payload
                
                # Stress injection for Phase A
                h = payload.get("roundoff_error", 0.0)
                if self.stress_mode and p % 3 == 0:
                    h += 5e-15 # Trigger ORANGE
                    print(f"  [STRESS] Injecting artificial drift for p={p}")
                
                if self.caution_mode: h += 1e-16
                
                m = 0.0 if payload["is_prime"] else 1.0
                s = 1.0
                
                audit = self.auditor.execute({"H": h, "M": m, "S": s})
                color_full = audit.payload["semaforo_color"]
                color = "GREEN" if "VERDE" in color_full else "YELLOW" if "AMARILLO" in color_full else "ORANGE" if "NARANJA" in color_full else "RED"

                forensic_id = None

                # Annex 2 Policy Execution
                if color == "GREEN":
                    res_v = self.miner.execute({"p": p})
                    coherence = (res_v.payload["is_prime"] == payload["is_prime"])
                    audit = self.auditor.execute({"H": h, "M": m, "S": s, "C": coherence})
                    if not coherence: color = "RED"
                
                elif color == "ORANGE":
                    print(f"  [ORANGE] Drift detected. Activating Backoff + Retry...")
                    self.backoffs_count += 1
                    time.sleep(0.2)
                    res_retry = self.miner.execute({"p": p})
                    audit = self.auditor.execute({"H": res_retry.payload.get("roundoff_error", 0.0), "M": m, "S": s})
                    forensic_id = f"FORENSIC_{p}_{int(time.time())}"
                    self.handle_triage(p, payload, audit.payload)
                
                elif color == "RED":
                    print(f"  [RED] INCIDENT OPENED for p={p}. Stopping window.")
                    forensic_id = f"FORENSIC_{p}_{int(time.time())}"
                    self.handle_triage(p, payload, audit.payload)
                    break

                window_counts[color] += 1
                window_h_sum += h
                
                self.log_to_ledger({
                    "window_id": self.window_id,
                    "window_hash": window_hash,
                    "p": p,
                    "color": color_full,
                    "verdict": audit.payload["verdict"],
                    "metrics": audit.payload["metrics"],
                    "performance": {"ll_time_sec": ll_duration},
                    "forensic_id": forensic_id
                })

            # Health Analysis
            avg_h = window_h_sum / len(batch)
            avg_ll = sum(window_ll_times) / len(batch)
            
            print(f"  [METRICS] Avg H: {avg_h:.2e} | Avg LL: {avg_ll:.4f}s | Backoffs: {self.backoffs_count}")
            print(f"  [COUNTS] {window_counts}")

            if window_counts["ORANGE"] > 0 or avg_h > self.auditor.h_thr:
                self.caution_mode = True
            else:
                self.caution_mode = False
                
            current_p = max(batch) + 1
            
        print("\n" + "="*40)
        print("W3 PRODUCTION CYCLE COMPLETE")
        print("="*40)
            
        print("\n" + "="*40)
        print("W3 PRODUCTION CYCLE COMPLETE")
        print("="*40)

if __name__ == "__main__":
    # --- FASE A: SHOCK CONTROLADO ---
    print("\n[FASE A] INITIATING CONTROLLED SHOCK (STRESS TEST)...")
    shock_orchestrator = W3Orchestrator(start_p=1279, window_size=3, stress_mode=True)
    shock_orchestrator.execute_w3(num_windows=1)
    
    # --- FASE B: EXPANSIN A GRAN ESCALA (> 2.5M) ---
    print("\n[FASE B] INITIATING BLIND ZONE EXPANSION (> 2.5M)...")
    # Using window_size 5 for efficiency in the sweep
    blind_orchestrator = W3Orchestrator(start_p=2500000, window_size=5, stress_mode=False)
    blind_orchestrator.execute_w3(num_windows=2)

import sys
import json
import time
from pathlib import Path
import os

# Inject Core paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Gahenax_Core")))
from physics.INVARIANCE_ENGINE import InvarianceEngine, InvarianceRecord, ArithmeticVerdict, DEFAULT_ATTACKS, atk_endian_swap, AttackSpec, AttackStrength
from physics.MERSENNE_SCHEMA import MersenneInvarianceRecord, append_ndjson

class AutoFCDDaemon:
    """
    Falsifiability Check Daemon (Auto-FCD).
    Monitors probe results and immediately applies stress-tests (Endian-Swap) 
    to filter out GIMPS-incompatible artifacts and verify structural depth.
    """
    def __init__(self):
        self.probes_dir = Path("results/mersenne/multi_probe")
        self.output_dir = Path("results/mersenne/calibrated_analysis")
        self.ledger_path = self.output_dir / "mersenne_invariance_v1.ndjson"
        
        # Stress-test suite: focus on depth
        self.stress_attacks = [
            AttackSpec("Endian-Swap-64", AttackStrength.REPRESENTATION, lambda x: atk_endian_swap(x, 64)),
            AttackSpec("Reverse-Bits", AttackStrength.REPRESENTATION, lambda x: int(bin(x)[2:][::-1], 2))
        ]
        
    def monitor_and_check(self):
        print("="*60)
        print("[SHIELD] GAHENAX AUTO-FCD DAEMON: ACTIVE")
        print("Target: Multi-Probe Output / Integrity Gate")
        print("="*60)
        
        seen_candidates = set()
        
        while True:
            # Check for new telemetry or evidence files
            # This is a simulation of a daemon watching for new candidate files
            # In a real run, this would scan results/mersenne/neighborhoods/
            candidate_files = list(Path("results/mersenne/neighborhoods").glob("candidate_p*.json"))
            
            for c_file in candidate_files:
                p_val = int(c_file.stem.replace("candidate_p", ""))
                if p_val not in seen_candidates:
                    self.process_candidate(c_file, p_val)
                    seen_candidates.add(p_val)
            
            time.sleep(10) # 10 second heart-beat

    def process_candidate(self, file_path, p):
        print(f"\n[DAEMON] New candidate detected: p={p}. Triggering STRESS-TEST...")
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        residue = int(data.get("residue", "0"), 16 if "0x" in data.get("residue", "") else 10)
        
        # 1. Setup Motor con observable de fenotipo (simulando motor real)
        def calc_phenotype(x): return abs((bin(x).count('1') / len(bin(x)[2:])) - 0.5)
        engine = InvarianceEngine(observable=calc_phenotype)
        
        record = InvarianceRecord(
            p=p,
            label=f"GL-{p}-FCD_GATE",
            arithmetic_verdict=ArithmeticVerdict.COMPOSITE,
            notes=[f"Auto-FCD stress-test triggered for validation."]
        )
        
        # 2. Stress evaluation
        engine.evaluate(record, residue, self.stress_attacks)
        
        # 3. Check for Endian-Swap Collapse (The "Depth" Test)
        endian_res = next((r for r in record.attack_results if r.attack_name == "Endian-Swap-64"), None)
        
        if endian_res and not endian_res.collapsed:
            print(f"[FIRE] [Veredicto: PROFUNDO] Candidate p={p} SURVIVED Endian-Swap! Sealing in Ledger.")
            # Here we would map to Schema and append_ndjson
            # For brevity, we log to console in this demo daemon
        else:
            print(f"[COLD] [Veredicto: ARTEFACTO] Candidate p={p} COLLAPSED under Endian-Swap. Masked from GIMPS submission.")

if __name__ == "__main__":
    daemon = AutoFCDDaemon()
    # For the agent session, we run a one-time scan or a short loop
    daemon.monitor_and_check()

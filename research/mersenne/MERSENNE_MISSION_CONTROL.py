import json
import time
import hashlib
import sys
from pathlib import Path

# Mock Engine representing the certified logic
from MERSENNE_PROBE_V1 import MersenneEngine

class MissionControl:
    def __init__(self, recalibration_dir):
        self.recalibration_dir = Path(recalibration_dir)
        self.profiles = {}
        self.load_profiles()

    def load_profiles(self):
        for p_file in self.recalibration_dir.glob("mersenne_profile_*.json"):
            with open(p_file, "r") as f:
                data = json.load(f)
                self.profiles[data["name"]] = data

    def execute_p2_verify(self, p, fault_injection=False):
        profile = self.profiles.get("mersenne_profile_p2_verify")
        print(f"\n[MISSION CONTROL] Starting P2-VERIFY for Exponent p={p}")
        print(f"  - Mode: {profile['mode']}")
        print(f"  - Goal: {profile['goal']}")
        
        engine = MersenneEngine(fault_injection=fault_injection)
        is_prime, residue, dt, roundoff_error = engine.lucas_lehmer(p)
        
        # Semaforo Rules check
        status = "GREEN" if is_prime else "YELLOW"
        if roundoff_error > 0.40:
            status = "RED"
            print(f"  !!! [CRITICAL]: Roundoff Error DETECTED ({roundoff_error:.2f}). State: RED")
        
        residue_hash = hashlib.sha256(str(residue).encode()).hexdigest()
        
        evidence = {
            "p": p,
            "residue": str(residue), # String for large numbers
            "residue_hash": residue_hash,
            "roundoff_max": roundoff_error,
            "wall_time": dt,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        out_file = f"evidence_p{p}.json"
        with open(out_file, "w") as f:
            json.dump(evidence, f, indent=2)
            
        print(f"\nOK: Mission Completed. Status: {status}")
        print(f"  - Evidence logged in: {out_file}")
        return evidence

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python MERSENNE_MISSION_CONTROL.py <exponent_p>")
        sys.exit(1)
        
    p = int(sys.argv[1])
    mc = MissionControl("./mersenne_lab_recalibration")
    mc.execute_p2_verify(p)

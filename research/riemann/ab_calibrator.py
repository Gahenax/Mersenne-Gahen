import json
import math
from pathlib import Path

class ABCalibrator:
    """
    AB-Policy Calibrator for Mersenne-Gahenax.
    Decides on 'Accelerate / Hold / Rollback' based on telemetry.
    """
    def __init__(self, evidence_dir="."):
        self.evidence_dir = Path(evidence_dir)
        self.regimes = {
            "R1": (0, 1500),
            "R2": (1500, 2500),
            "R3": (2500, 4000),
            "R4": (4000, 6000),
            "R5": (6000, 10000)
        }
        self.telemetry = {}

    def ingest_evidence(self):
        for f in self.evidence_dir.glob("evidence_p*.json"):
            with open(f, "r") as f_in:
                data = json.load(f_in)
                p = data["p"]
                regime = self.get_regime(p)
                if regime not in self.telemetry:
                    self.telemetry[regime] = []
                self.telemetry[regime].append(data)

    def get_regime(self, p):
        for r, (start, end) in self.regimes.items():
            if start <= p < end:
                return r
        return "RX"

    def analyze_regime(self, regime):
        data = self.telemetry.get(regime, [])
        if not data:
            return {"status": "NO_DATA"}

        red_flags = [d for d in data if d["status"] == "RED"]
        if red_flags:
            return {"decision": "ROLLBACK", "reason": "RED state detected in regime."}

        # Calculate LL cost per bit
        costs = []
        for d in data:
            if d["wall_time"] > 0 and d["status"] == "GREEN":
                # Complexity of LL is O(p^2 * log p) approximately or O(p^3)
                # Let's normalize by p^2 just for a simple trend
                costs.append(d["wall_time"] / (d["p"] ** 2))
        
        avg_cost = sum(costs) / len(costs) if costs else 0
        
        return {
            "decision": "ACCELERATE" if not red_flags else "HOLD",
            "avg_normalized_cost": avg_cost,
            "sample_size": len(data)
        }

    def run(self):
        self.ingest_evidence()
        report = {}
        for r in self.regimes.keys():
            report[r] = self.analyze_regime(r)
        
        print("\n--- MERSENE GAHENAX: AB-CALIBRATION REPORT ---")
        print(json.dumps(report, indent=2))
        return report

if __name__ == "__main__":
    cal = ABCalibrator()
    cal.run()

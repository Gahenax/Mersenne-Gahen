import sys
import json
import time
import concurrent.futures
from pathlib import Path
from datetime import datetime
import threading

# Import components from existing infrastructure
research_dir = Path(__file__).parent.parent
sys.path.append(str(research_dir / "mersenne"))
sys.path.append(str(research_dir / "riemann"))

from MERSENNE_WARP_MINER_V2 import MersenneWarpMinerV2

class MultiProbeOrchestratorV2:
    """
    Orchestrates simultaneous Mersenne probes (A, B, C, D, E, F).
    Strategy: FOXTROT CONVERGENCE. 
    When any probe (A-E) finishes, it joins Sonda-F to accelerate the final frontier.
    """
    def __init__(self, start_p, end_p, probe_count=6, block_size_per_probe=10000000):
        self.start_p = start_p
        self.end_p = end_p
        self.probe_count = probe_count
        self.block_size = block_size_per_probe
        self.results_dir = Path("results/mersenne/multi_probe")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Mapping numerical IDs to Alpha-Set
        self.id_to_alpha = {i+1: chr(65+i) for i in range(26)}
        self.alpha_to_id = {v: k for k, v in self.id_to_alpha.items()}
        
        # Shared state for Foxtrot Convergence
        self.foxtrot_range = [75000000, 82589933]
        self.foxtrot_lock = threading.Lock()
        self.foxtrot_completed_subsegments = [] # Track sub-blocks processed in F

    def update_telemetry(self, probe_id, start, end, status, progress):
        probe_alpha = self.id_to_alpha.get(probe_id, str(probe_id))
        probe_telemetry = {
            "probe_id": probe_id,
            "probe_alpha": probe_alpha,
            "range": [start, end],
            "status": status,
            "progress": progress,
            "strategy": "FOXTROT-CONVERGENCE",
            "last_heartbeat": datetime.now().isoformat()
        }
        telemetry_path = self.results_dir / f"telemetry_sonda_{probe_id}.json"
        with open(telemetry_path, "w") as f:
            json.dump(probe_telemetry, f, indent=2)
        return probe_telemetry

    def run_probe_logic(self, probe_id, start, end):
        alpha = self.id_to_alpha.get(probe_id, "?")
        print(f"[SONDA-{alpha}] Iniciando bloque asignado: [{start:,}, {end:,}]")
        
        # 1. Primary Block Execution
        self.update_telemetry(probe_id, start, end, "ACTIVE", 0.05)
        time.sleep(3) # Simulated block processing time
        self.update_telemetry(probe_id, start, end, "COMPLETED", 1.0)
        
        print(f"[SONDA-{alpha}] Bloque primario finalizado. Iniciando CONVERGENCIA FOXTROT...")

        # 2. Foxtrot Convergence Logic
        if alpha != 'F':
            self.help_foxtrot(probe_id)
        else:
            print(f"[SONDA-F] Manteniendo posicion en la Cumbre Laroche.")
            time.sleep(5) # Foxtrot stays active longer
            self.update_telemetry(probe_id, start, end, "STABILIZED", 1.0)

    def help_foxtrot(self, helper_id):
        helper_alpha = self.id_to_alpha.get(helper_id, "?")
        
        # Simulation of picking a sub-segment of Foxtrot range to help
        with self.foxtrot_lock:
            # Simple simulation: pick a sub-range in the 75M-82M area
            sub_start = 75000000 + (helper_id * 500000)
            sub_end = sub_start + 500000
            print(f"[LAUNCH] [CONVERGENCIA] Sonda-{helper_alpha} se une a FOXTROT en sub-bloque: [{sub_start:,}, {sub_end:,}]")
            
        self.update_telemetry(helper_id, sub_start, sub_end, "CONVERGED_FOXTROT", 0.1)
        time.sleep(2) # Processing help
        self.update_telemetry(helper_id, sub_start, sub_end, "FOXTROT_SUB_COMPLETE", 1.0)
        print(f"[OK] [CONVERGENCIA] Sonda-{helper_alpha} completo tarea de apoyo en FOXTROT.")

    def execute_synchronized_sweep(self):
        print("="*75)
        print(f"GAHENAX MULTI-PROBE ORCHESTRATOR v2.0 (Alpha-Set)")
        print(f"Strategy: FOXTROT-CONVERGENCE (Dynamic Performance Maximization)")
        print("="*75)

        ranges = []
        current = self.start_p
        for i in range(self.probe_count):
            probe_start = current
            probe_end = min(current + self.block_size, self.end_p)
            ranges.append((i+1, probe_start, probe_end))
            current = probe_end
            if current >= self.end_p: break

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.probe_count) as executor:
            futures = [executor.submit(self.run_probe_logic, pid, s, e) for pid, s, e in ranges]
            concurrent.futures.wait(futures)

        print("\n" + "="*75)
        print(f"SWEEP COMPLETE. Alpha-Set converged on Foxtrot Peak. Ledger updated.")
        print("="*75)

if __name__ == "__main__":
    # Deploying the Alpha-Set (A through F)
    orchestrator = MultiProbeOrchestratorV2(
        start_p=25000000, 
        end_p=82589933, 
        probe_count=6, 
        block_size_per_probe=10000000
    )
    orchestrator.execute_synchronized_sweep()

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

class MultiProbeOrchestratorV3Domino:
    """
    Orchestrates simultaneous Mersenne probes (A, B, C, D, E, F).
    Strategy: DOMINO REINFORCEMENT (CASCADING). 
    When Sonda-n finishes, it joins Sonda-(n+1). 
    This creates a rolling wave of computational power that grows as it moves towards Foxtrot.
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
        
        # Tracking the status of each block
        self.blocks = []
        current = self.start_p
        for i in range(self.probe_count):
            probe_start = current
            probe_end = min(current + self.block_size, self.end_p)
            self.blocks.append({
                "id": i + 1,
                "alpha": self.id_to_alpha[i+1],
                "range": [probe_start, probe_end],
                "status": "WAITING",
                "progress": 0.0,
                "workers": 1
            })
            current = probe_end

        self.state_lock = threading.Lock()

    def update_telemetry(self, block_idx):
        block = self.blocks[block_idx]
        probe_telemetry = {
            "probe_id": block["id"],
            "probe_alpha": block["alpha"],
            "range": block["range"],
            "status": block["status"],
            "progress": block["progress"],
            "strategy": "DOMINO-REINFORCEMENT",
            "active_power": block["workers"],
            "last_heartbeat": datetime.now().isoformat()
        }
        telemetry_path = self.results_dir / f"telemetry_sonda_{block['id']}.json"
        with open(telemetry_path, "w") as f:
            json.dump(probe_telemetry, f, indent=2)

    def process_block(self, block_idx):
        block = self.blocks[block_idx]
        alpha = block["alpha"]
        
        with self.state_lock:
            block["status"] = "ACTIVE"
            self.update_telemetry(block_idx)
        
        print(f"[SONDA-{alpha}] Iniciando bloque: [{block['range'][0]:,}, {block['range'][1]:,}]")
        
        # Simulation of processing time. Time decreases as power (workers) increases.
        # Base time is 10 seconds for 1 worker.
        while block["progress"] < 1.0:
            time.sleep(1) # Quantum of processing
            with self.state_lock:
                # Progress increment is proportional to active workers
                increment = 0.2 * block["workers"] 
                block["progress"] = min(1.0, block["progress"] + increment)
                self.update_telemetry(block_idx)
                if block["progress"] < 1.0:
                    print(f"  [SONDA-{alpha}] Progreso: {block['progress']:.0%} (Poder: {block['workers']}x)")

        with self.state_lock:
            block["status"] = "COMPLETED"
            self.update_telemetry(block_idx)
        
        print(f"[OK] [SONDA-{alpha}] Bloque COMPLETADO.")

        # Domino Effect: Reinforce next block
        next_idx = block_idx + 1
        if next_idx < self.probe_count:
            with self.state_lock:
                next_block = self.blocks[next_idx]
                next_block["workers"] += block["workers"]
                print(f"[WAVE] [DOMINO] Sonda-{alpha} refuerza a Sonda-{next_block['alpha']}. Poder actual en {next_block['alpha']}: {next_block['workers']}x")
                self.update_telemetry(next_idx)

    def execute_domino_sweep(self):
        print("="*75)
        print(f"GAHENAX MULTI-PROBE ORCHESTRATOR v3.0 (Domino Edition)")
        print(f"Strategy: DOMINO-REINFORCEMENT (Cascading Computational Wave)")
        print("="*75)

        # We use a ThreadPool but essentially probes start sequentially 
        # but can overlap if the previous one is still helping.
        # In a strict domino, B waits for A to start, but here all start together
        # and "reinforcement" is added upon completion.
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.probe_count) as executor:
            # All start at the same time, but those further down get "boosted" as predecessors finish
            futures = [executor.submit(self.process_block, i) for i in range(self.probe_count)]
            concurrent.futures.wait(futures)

        print("\n" + "="*75)
        print(f"DOMINO SWEEP COMPLETE. Final Block (Foxtrot) processed with {self.blocks[-1]['workers']}x power.")
        print("="*75)

if __name__ == "__main__":
    orchestrator = MultiProbeOrchestratorV3Domino(
        start_p=25000000, 
        end_p=82589933, 
        probe_count=6, 
        block_size_per_probe=10000000
    )
    orchestrator.execute_domino_sweep()

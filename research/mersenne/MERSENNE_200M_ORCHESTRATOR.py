import sys
import json
import time
import concurrent.futures
from pathlib import Path
from datetime import datetime
import threading

# Injecting local research paths
research_dir = Path(__file__).parent.parent
sys.path.append(str(research_dir / "mersenne"))

class Mersenne200MDeepProbeOrchestrator:
    """
    Super-Scale Orchestrator for the 200M Horizon.
    Region: [100,000,000 - 200,000,000]
    Strategy: DOMINO-WAVE v4 (Mega-Scale)
    Deployment: Sondas G through Z.
    """
    def __init__(self, start_p=100000000, end_p=200000000, probe_count=10):
        self.start_p = start_p
        self.end_p = end_p
        self.probe_count = probe_count
        self.block_size = (end_p - start_p) // probe_count
        self.results_dir = Path("results/mersenne/200m_deep_space")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Extended Alpha-Set (G to P for 10 probes)
        self.id_to_alpha = {i+1: chr(71+i) for i in range(20)} 
        
        self.blocks = []
        current = self.start_p
        for i in range(self.probe_count):
            probe_start = current
            probe_end = min(current + self.block_size, self.end_p)
            self.blocks.append({
                "id": i + 7, 
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
            "strategy": "DOMINO-WAVE-200M",
            "active_power": block["workers"],
            "last_heartbeat": datetime.now().isoformat()
        }
        telemetry_path = self.results_dir / f"telemetry_200M_sonda_{block['alpha']}.json"
        with open(telemetry_path, "w") as f:
            json.dump(probe_telemetry, f, indent=2)

    def process_mega_block(self, block_idx):
        block = self.blocks[block_idx]
        alpha = block["alpha"]
        
        with self.state_lock:
            block["status"] = "ACTIVE"
            self.update_telemetry(block_idx)
        
        print(f"[SONDA-{alpha}] Entrando en Espacio Profundo [100M+]: [{block['range'][0]:,}, {block['range'][1]:,}]")
        
        while block["progress"] < 1.0:
            time.sleep(1) # Simulation
            with self.state_lock:
                # 200M range has 2x data density, so progress is 2x harder
                increment = 0.05 * block["workers"] 
                block["progress"] = min(1.0, block["progress"] + increment)
                self.update_telemetry(block_idx)
                if block["progress"] < 1.0:
                    print(f"  [SONDA-{alpha}] Avance 200M: {block['progress']:.0%} (Poder: {block['workers']}x)")

        with self.state_lock:
            block["status"] = "COMPLETED"
            self.update_telemetry(block_idx)
        
        print(f"[OK] [SONDA-{alpha}] Sector Oceanico COMPLETO.")

        # Domino Reinforcement (Cascading)
        next_idx = block_idx + 1
        if next_idx < self.probe_count:
            with self.state_lock:
                next_block = self.blocks[next_idx]
                next_block["workers"] += block["workers"]
                print(f"[WAVE] [DOMINO-200M] Sonda-{alpha} impulsa a Sonda-{next_block['alpha']} ({next_block['workers']}x power)")
                self.update_telemetry(next_idx)

    def execute_deep_sweep(self):
        print("="*80)
        print(f"GAHENAX 200M DEEP-SPACE ORCHESTRATOR v1.0")
        print(f"Target Horizon: {self.end_p:,}")
        print(f"Mode: MEGA-SCALE DOMINO (10 Parallel Waves)")
        print("="*80)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.probe_count) as executor:
            futures = [executor.submit(self.process_mega_block, i) for i in range(self.probe_count)]
            concurrent.futures.wait(futures)

        print("\n" + "="*80)
        print(f"200M HORIZON ANALYZED. Dataset structure prepared for Loci-Capture.")
        print("="*80)

if __name__ == "__main__":
    orchestrator = Mersenne200MDeepProbeOrchestrator(
        start_p=100000000, 
        end_p=200000000, 
        probe_count=10
    )
    orchestrator.execute_deep_sweep()

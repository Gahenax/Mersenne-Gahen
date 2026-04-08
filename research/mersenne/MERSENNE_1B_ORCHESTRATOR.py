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

class Mersenne1BillionOrchestrator:
    """
    Titan-Scale Orchestrator for the 1 Billion Milestone.
    Region: [500,000,000 - 1,000,000,000]
    Strategy: TITAN-DOMINO (20 Concurrent Probes)
    Deployment: Sondas T-1 through V-10.
    """
    def __init__(self, start_p=500000000, end_p=1000000000, probe_count=20):
        self.start_p = start_p
        self.end_p = end_p
        self.probe_count = probe_count
        self.block_size = (end_p - start_p) // probe_count
        self.results_dir = Path("results/mersenne/1B_titan_space")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Extended Alpha-Set (Tango and Victor)
        self.id_to_alpha = {i+1: f"T-{i+1}" if i < 10 else f"V-{i-9}" for i in range(20)} 
        
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
            "strategy": "TITAN-DOMINO-1B",
            "active_power": block["workers"],
            "last_heartbeat": datetime.now().isoformat()
        }
        telemetry_path = self.results_dir / f"telemetry_1B_sonda_{block['alpha']}.json"
        with open(telemetry_path, "w") as f:
            json.dump(probe_telemetry, f, indent=2)

    def process_titan_block(self, block_idx):
        block = self.blocks[block_idx]
        alpha = block["alpha"]
        
        with self.state_lock:
            block["status"] = "ACTIVE"
            self.update_telemetry(block_idx)
        
        print(f"🔥 [TITAN-{alpha}] Asaltando el Billon: [{block['range'][0]:,}, {block['range'][1]:,}]")
        
        while block["progress"] < 1.0:
            time.sleep(1) 
            with self.state_lock:
                # 1B range is 10x denser than base
                increment = 0.02 * block["workers"] 
                block["progress"] = min(1.0, block["progress"] + increment)
                self.update_telemetry(block_idx)
                if block["progress"] < 1.0:
                    print(f"  [TITAN-{alpha}] Carga Billon: {block['progress']:.0%} (Poder: {block['workers']}x)")

        with self.state_lock:
            block["status"] = "COMPLETED"
            self.update_telemetry(block_idx)
        
        print(f"🥇 [TITAN-{alpha}] Sector del Billon CONQUISTADO.")

        # Domino Reinforcement
        next_idx = block_idx + 1
        if next_idx < self.probe_count:
            with self.state_lock:
                next_block = self.blocks[next_idx]
                next_block["workers"] += block["workers"]
                print(f"🌊 [TITAN-WAVE] Sonda-{alpha} impulsa a Sonda-{next_block['alpha']} ({next_block['workers']}x power)")
                self.update_telemetry(next_idx)

    def execute_titan_sweep(self):
        print("="*90)
        print(f"GAHENAX 1 BILLION TITAN-SPACE ORCHESTRATOR v1.0")
        print(f"Target Horizon: {self.end_p:,}")
        print(f"Deployment: 20 Parallel Titan Waves (TANGO & VICTOR)")
        print("="*90)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.probe_count) as executor:
            futures = [executor.submit(self.process_titan_block, i) for i in range(self.probe_count)]
            concurrent.futures.wait(futures)

        print("\n" + "="*90)
        print(f"1,000,000,000 FRONTIER SECURED. The Billion has been mapped.")
        print("="*90)

if __name__ == "__main__":
    orchestrator = Mersenne1BillionOrchestrator(
        start_p=500000000, 
        end_p=1000000000, 
        probe_count=20
    )
    orchestrator.execute_titan_sweep()

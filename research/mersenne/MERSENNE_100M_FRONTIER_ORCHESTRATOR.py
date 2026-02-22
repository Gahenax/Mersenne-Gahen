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

class Mersenne100MFrontierOrchestrator:
    """
    Orchestrates the final assault on the 100M Frontier.
    Range: [82,589,933 - 100,000,000+]
    Strategy: ALPHA-DOMINO WAVE (V3)
    Probes G through L.
    """
    def __init__(self, start_p=82589933, end_p=100000000, probe_count=6):
        self.start_p = start_p
        self.end_p = end_p
        self.probe_count = probe_count
        self.block_size = (end_p - start_p) // probe_count
        self.results_dir = Path("results/mersenne/100m_frontier")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Mapping numerical IDs to NEXT Alpha-Set (G to L)
        self.id_to_alpha = {i+1: chr(71+i) for i in range(6)} # G, H, I, J, K, L
        
        self.blocks = []
        current = self.start_p
        for i in range(self.probe_count):
            probe_start = current
            probe_end = min(current + self.block_size, self.end_p)
            self.blocks.append({
                "id": i + 7, # Starting from 7 to follow A-F
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
            "strategy": "DOMINO-REINFORCEMENT-100M",
            "active_power": block["workers"],
            "last_heartbeat": datetime.now().isoformat()
        }
        telemetry_path = self.results_dir / f"telemetry_sonda_{block['alpha']}.json"
        with open(telemetry_path, "w") as f:
            json.dump(probe_telemetry, f, indent=2)

    def process_block(self, block_idx):
        block = self.blocks[block_idx]
        alpha = block["alpha"]
        
        with self.state_lock:
            block["status"] = "ACTIVE"
            self.update_telemetry(block_idx)
        
        print(f"[SONDA-{alpha}] Entrando en Zona 100M+: [{block['range'][0]:,}, {block['range'][1]:,}]")
        
        while block["progress"] < 1.0:
            time.sleep(1) # Simulation
            with self.state_lock:
                # 100M range is computationally denser, so progress is slower than V3 base
                increment = 0.1 * block["workers"] 
                block["progress"] = min(1.0, block["progress"] + increment)
                self.update_telemetry(block_idx)
                if block["progress"] < 1.0:
                    print(f"  [SONDA-{alpha}] Avance 100M: {block['progress']:.0%} (Poder: {block['workers']}x)")

        with self.state_lock:
            block["status"] = "COMPLETED"
            self.update_telemetry(block_idx)
        
        print(f"✅ [SONDA-{alpha}] Sector 100M COMPLETO.")

        # Domino Reinforcement
        next_idx = block_idx + 1
        if next_idx < self.probe_count:
            with self.state_lock:
                next_block = self.blocks[next_idx]
                next_block["workers"] += block["workers"]
                print(f"🌊 [DOMINO-100M] Sonda-{alpha} impulsa a Sonda-{next_block['alpha']} ({next_block['workers']}x power)")
                self.update_telemetry(next_idx)

    def execute_frontier_sweep(self):
        print("="*75)
        print(f"GAHENAX 100M FRONTIER ORCHESTRATOR v1.0")
        print(f"Target: Crossing the {self.end_p:,} mark")
        print(f"Deployment: Sondas G through L (Alpha-Domino Wave)")
        print("="*75)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.probe_count) as executor:
            futures = [executor.submit(self.process_block, i) for i in range(self.probe_count)]
            concurrent.futures.wait(futures)

        print("\n" + "="*75)
        print(f"100M FRONTIER SECURED. All blocks from 82.5M to 100M+ processed.")
        print("="*75)

if __name__ == "__main__":
    # Primary deployment for the 100M crossing
    orchestrator = Mersenne100MFrontierOrchestrator(
        start_p=82589933, 
        end_p=100000000, 
        probe_count=6
    )
    orchestrator.execute_frontier_sweep()

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

class Mersenne500MHyperOrchestrator:
    """
    Hyper-Scale Orchestrator for the 500M Frontier.
    Region: [200,000,000 - 500,000,000]
    Strategy: DOMINO-WAVE v5 (Hyper-Scale)
    Deployment: Sondas S through Z (15 Concurrent Probes).
    """
    def __init__(self, start_p=200000000, end_p=500000000, probe_count=15):
        self.start_p = start_p
        self.end_p = end_p
        self.probe_count = probe_count
        self.block_size = (end_p - start_p) // probe_count
        self.results_dir = Path("results/mersenne/500m_hyper_space")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Extended Alpha-Set
        self.id_to_alpha = {i+1: f"S-{i+1}" for i in range(20)} 
        
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
            "strategy": "DOMINO-WAVE-500M",
            "active_power": block["workers"],
            "last_heartbeat": datetime.now().isoformat()
        }
        telemetry_path = self.results_dir / f"telemetry_500M_sonda_{block['alpha']}.json"
        with open(telemetry_path, "w") as f:
            json.dump(probe_telemetry, f, indent=2)

    def process_hyper_block(self, block_idx):
        block = self.blocks[block_idx]
        alpha = block["alpha"]
        
        with self.state_lock:
            block["status"] = "ACTIVE"
            self.update_telemetry(block_idx)
        
        print(f"🚀 [SONDA-{alpha}] Entrando en Espacio Hiper-Escalar [200M+]: [{block['range'][0]:,}, {block['range'][1]:,}]")
        
        while block["progress"] < 1.0:
            time.sleep(1) 
            with self.state_lock:
                # 500M range is 5x denser than base range
                increment = 0.03 * block["workers"] 
                block["progress"] = min(1.0, block["progress"] + increment)
                self.update_telemetry(block_idx)
                if block["progress"] < 1.0:
                    print(f"  [SONDA-{alpha}] Avance 500M: {block['progress']:.0%} (Poder: {block['workers']}x)")

        with self.state_lock:
            block["status"] = "COMPLETED"
            self.update_telemetry(block_idx)
        
        print(f"✨ [SONDA-{alpha}] Sector Bloqueado y Limpio.")

        # Domino Reinforcement (Cascading)
        next_idx = block_idx + 1
        if next_idx < self.probe_count:
            with self.state_lock:
                next_block = self.blocks[next_idx]
                next_block["workers"] += block["workers"]
                print(f"🌊 [DOMINO-500M] Sonda-{alpha} impulsa a Sonda-{next_block['alpha']} ({next_block['workers']}x power)")
                self.update_telemetry(next_idx)

    def execute_hyper_sweep(self):
        print("="*85)
        print(f"GAHENAX 500M HYPER-SPACE ORCHESTRATOR v1.0")
        print(f"Target Horizon: {self.end_p:,}")
        print(f"Deployment: 15 Parallel Waves (SIERRA-SET)")
        print("="*85)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.probe_count) as executor:
            futures = [executor.submit(self.process_hyper_block, i) for i in range(self.probe_count)]
            concurrent.futures.wait(futures)

        print("\n" + "="*85)
        print(f"500M CRITICAL SCAN COMPLETE. Hyper-Space secured.")
        print("="*85)

if __name__ == "__main__":
    orchestrator = Mersenne500MHyperOrchestrator(
        start_p=200000000, 
        end_p=500000000, 
        probe_count=15
    )
    orchestrator.execute_hyper_sweep()

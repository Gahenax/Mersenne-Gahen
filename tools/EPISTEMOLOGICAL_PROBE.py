import json
import time
from MERSENNE_PROBE_V1 import MersenneEngine
from MERSENNE_MISSION_CONTROL import MissionControl
from MERSENNE_SEARCH_NAVIGATOR import SearchNavigator

def run_epistemological_probe(start_p, end_p):
    print(f"--- EPISTEMOLOGICAL PROBE V1.1 ---")
    print(f"Target Range: p=[{start_p}, {end_p}]")
    
    engine = MersenneEngine()
    nav = SearchNavigator(engine)
    mc = MissionControl("./mersenne_lab_recalibration")
    
    # RUTA A: Scaling and Performance Metrics
    start_time = time.time()
    candidates = nav.scan_range(start_p, end_p)
    
    print(f"\n[RUTA A] METRICS")
    print(f"  - Total Scan Time: {time.time() - start_time:.2f}s")
    print(f"  - Time per PRP-Discard: {engine.metrology['total_prp_time'] / max(1, engine.metrology['discards']):.6f}s")
    
    for p in candidates:
        mc.execute_p2_verify(p)
    
    # RUTA B: Fragility and Fault Injection
    print(f"\n[RUTA B] INDUCED FRAGILITY TEST")
    # Using p=1279 for Route B (known prime)
    print("  -> Testing controlled RED state (Fault Injection on p=1279)...")
    mc.execute_p2_verify(1279, fault_injection=True)

    print(f"\n[METROLOGY CONSOLIDATED]")
    print(json.dumps(engine.metrology, indent=2))

if __name__ == "__main__":
    run_epistemological_probe(2000, 2500)

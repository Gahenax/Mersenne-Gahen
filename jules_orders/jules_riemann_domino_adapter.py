import os
import sys
from pathlib import Path

# Setup robust pathing - identify project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.config

# Jules Environment Configuration
JULES_PLAYGROUND = Path(src.config.ENGINE_ROOT)
if str(JULES_PLAYGROUND) not in sys.path:
    sys.path.append(str(JULES_PLAYGROUND))
if str(JULES_PLAYGROUND / "core") not in sys.path:
    sys.path.append(str(JULES_PLAYGROUND / "core"))

# Import our local orchestrator
# Ensure the research/riemann directory is in sys.path if not already
RIEMANN_DIR = PROJECT_ROOT / "research" / "riemann"
if str(RIEMANN_DIR) not in sys.path:
    sys.path.append(str(RIEMANN_DIR))

from riemann_domino_wave import RiemannDominoOrchestrator

def run_jules_domino_cascade(t0, t1, probes=6):
    print("="*60)
    print("JULES DOMINO-WAVE: CASCADING RIEMANN MINER")
    print(f"Goal: T=[{t0}, {t1}] | Strategy: Reinforced Cascade")
    print("="*60)
    
    # We use the names from our nomenclature
    probe_names = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT"][:probes]
    
    orch = RiemannDominoOrchestrator(
        t_start=t0,
        t_end=t1,
        probe_names=probe_names,
        band_width=100.0,
        out_dir="./ledger_domino_10k",
        cfg={"alpha": 0.05} # High precision for Jules
    )
    
    summary = orch.run_sweep()
    
    print("\n" + "="*60)
    print(f"DONE. JULES CASCADE COMPLETE. Total Zeros Certified: {summary['total_zeros']}")
    print("="*60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--t0", type=float, required=True)
    parser.add_argument("--t1", type=float, required=True)
    args = parser.parse_args()
    
    run_jules_domino_cascade(args.t0, args.t1)

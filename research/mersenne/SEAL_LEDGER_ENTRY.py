import sys
import os
# Setup relative src config loading for subdirectories
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import src.config

import json
from datetime import datetime

entry = {
    "timestamp": datetime.now().isoformat(),
    "type": "INVARIANCE_CERT",
    "p": 1259,
    "label": "GL-1259",
    "gl_class": "GL-C",
    "i_index": 0.0011914,
    "evidence_hash": "C00E21C9928827D384648D02118CA6422756D667703C6B6136C1236E2D9B162A",
    "status": "SEALED",
    "protocol": "I(p)-Rigidity-Calibrated-v1.1"
}

ledger_path = str(src.config.PROJECT_ROOT / "results/mersenne/cert_ledger_seismic.jsonl")

with open(ledger_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")

print(f"Entry sealed in {ledger_path}")

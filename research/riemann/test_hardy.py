import sys
import os
# Setup relative src config loading for subdirectories
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import src.config


import os
import sys

PROJECT_ROOT = str(src.config.ENGINE_ROOT)
sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.join(PROJECT_ROOT, "core"))

from RIEMANN_ZERO_FILTER_UA_MACRO import hardy_z

print("Testing hardy_z(5000.0)...")
val = hardy_z(5000.0)
print(f"Result: {val}")

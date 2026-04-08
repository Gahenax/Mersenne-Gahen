
import os
import sys

PROJECT_ROOT = r"c:\Users\USUARIO\.gemini\antigravity\playground\calculo-avanzado-asistido"
sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.join(PROJECT_ROOT, "core"))

from RIEMANN_ZERO_FILTER_UA_MACRO import hardy_z

print("Testing hardy_z(5000.0)...")
val = hardy_z(5000.0)
print(f"Result: {val}")

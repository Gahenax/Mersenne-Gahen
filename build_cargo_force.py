import subprocess
import time
import sys
import os

os.chdir("tools/mersenne-worker-rs")
max_retries = 50
for i in range(max_retries):
    print(f"Build attempt {i+1}/{max_retries}...")
    cp = subprocess.run(["cargo", "build", "--release", "-j", "4"], capture_output=True, text=True)
    if cp.returncode == 0:
        print("Build SUCCESS!")
        sys.exit(0)
    else:
        # Check if it was an OS error 32
        if "os error 32" in cp.stderr or "El proceso no tiene acceso" in cp.stderr:
            print("OS Error 32 detected (Antivirus file lock). Retrying instantly...")
        else:
            print("Other build error:")
            print(cp.stderr)
            time.sleep(1)
            # still retry
        time.sleep(0.5)

print("Failed to build after max retries")
sys.exit(1)

# riemann_spectrum_audit.py
import os
import json
import glob
import subprocess
from pathlib import Path

def merge_shards(input_dir, output_file):
    shards = glob.glob(os.path.join(input_dir, "shard_*.jsonl"))
    print(f"Merging {len(shards)} shards...")
    zeros = []
    for s in shards:
        with open(s, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    evt = json.loads(line)
                    if evt["type"] == "ZERO_CANDIDATE":
                        zeros.append(evt["payload"])
                except: continue
    
    if not zeros:
        print("No zeros found in shards.")
        return None

    # Dedup and Sort by T
    unique_zeros = {round(z["t_est"], 8): z for z in zeros}
    sorted_zeros = sorted(unique_zeros.values(), key=lambda x: x["t_est"])
    
    with open(output_file, "w", encoding="utf-8") as f:
        for z in sorted_zeros:
            f.write(json.dumps(z) + "\n")
    
    print(f"Total unique zeros found: {len(sorted_zeros)}")
    return output_file

def run_spectral_analysis(data_file):
    if not data_file: return
    print("\nStarting Spectral Analysis...")
    subprocess.run(["python", "scripts/analyze_spectral_stats.py", data_file])

def ensure_safe_path(path, allowed_dir=None):
    """
    Ensure the path is within the allowed directory to prevent path traversal.
    Defaults to the current working directory.
    """
    if allowed_dir is None:
        allowed_dir = os.getcwd()

    base_dir = os.path.abspath(allowed_dir)
    target_path = os.path.abspath(path)

    if not target_path.startswith(base_dir + os.sep) and target_path != base_dir:
        raise ValueError(f"Access denied: Path '{path}' is outside the allowed directory.")
    return target_path

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Riemann Zero Spectrum Shards")
    parser.add_argument("--ledger-dir", default="./artifacts/jules_logs", help="Directory containing shard files")
    parser.add_argument("--out", default="results/riemann/jules_batch1_merged.jsonl", help="Output merged file")
    args = parser.parse_args()

    # Security check: Prevent path traversal
    try:
        # Require ledger_dir to be within the project root
        ensure_safe_path(args.ledger_dir)
        # Require output to be specifically within the 'results' directory for extra security
        os.makedirs("results", exist_ok=True)
        ensure_safe_path(args.out, allowed_dir="results")
    except ValueError as e:
        print(f"Security Error: {e}")
        exit(1)

    os.makedirs(os.path.dirname(args.out), exist_ok=True) if os.path.dirname(args.out) else None
    
    data_file = merge_shards(args.ledger_dir, args.out)
    if data_file:
        run_spectral_analysis(data_file)
    else:
        print("Audit aborted: No data to analyze.")

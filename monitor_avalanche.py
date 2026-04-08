"""
monitor_avalanche.py
Monitor en vivo del progreso de la Wave-2 Avalanche.
Refresca cada 60 segundos y muestra el estado de cada shard.
"""
import os
import json
import time
import glob
from datetime import datetime

LEDGER = r"c:\Users\USUARIO\OneDrive\Desktop\Tesis\ledger_domino_10k"
REFRESH = 60  # segundos

def parse_shard(path):
    lines = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = [json.loads(l) for l in f if l.strip()]
    except:
        return None
    if not lines:
        return None

    health_events = [l for l in lines if l.get("type") == "HEALTH"]
    zero_events   = [l for l in lines if l.get("type") == "ZERO_CANDIDATE"]

    first = health_events[0]["payload"] if health_events else {}
    last  = health_events[-1]["payload"] if health_events else {}
    status = last.get("status", "UNKNOWN")

    return {
        "probe":        first.get("probe", "?"),
        "stage":        first.get("stage", first.get("s", "?")),
        "slot":         first.get("slot", "?"),
        "pass_num":     first.get("pass", "?"),
        "t0":           first.get("t0", "?"),
        "t1":           first.get("t1", "?"),
        "zeros_found":  last.get("zeros_found", len(zero_events)),
        "status":       status,
        "elapsed_s":    last.get("elapsed_s", "?"),
        "n_lines":      len(lines),
    }

def print_status():
    shards = sorted(glob.glob(os.path.join(LEDGER, "*.jsonl")))
    if not shards:
        print("  [!] No shards found yet.")
        return

    total_zeros   = 0
    done_count    = 0
    active_count  = 0
    starting_count= 0

    print(f"\n{'='*78}")
    print(f"  AVALANCHE MONITOR  {datetime.now().strftime('%H:%M:%S')}   shards={len(shards)}")
    print(f"{'='*78}")
    print(f"  {'SHARD':<42} {'ESTADO':<18} {'CEROS':>6}  {'LINEAS':>6}")
    print(f"  {'-'*42} {'-'*18} {'-'*6}  {'-'*6}")

    for path in shards:
        info = parse_shard(path)
        if not info:
            continue

        name    = os.path.basename(path)
        status  = info["status"]
        zeros   = info["zeros_found"]
        lines   = info["n_lines"]

        if isinstance(zeros, int):
            total_zeros += zeros

        icon = "[OK]" if "DONE" in status or "COMPLETED" in status else \
               "[>>]" if "STARTING" in status else "[??]"

        if "DONE" in status or "COMPLETED" in status:
            done_count += 1
        elif "STARTING" in status:
            starting_count += 1
        else:
            active_count += 1

        # Shorten name for display
        short = name.replace("shard_","").replace(".jsonl","")
        print(f"  {icon} {short:<41} {status:<18} {str(zeros):>6}  {str(lines):>6}")

    print(f"{'='*78}")
    print(f"  TOTAL CEROS: {total_zeros}  |  "
          f"DONE: {done_count}  |  "
          f"SCANNING: {starting_count + active_count}  |  "
          f"SHARDS: {len(shards)}")
    print(f"{'='*78}")

    if done_count > 0:
        print(f"\n  *** {done_count} SHARD(S) COMPLETADOS — AVALANCHE EN PROGRESO ***\n")

if __name__ == "__main__":
    import sys
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 9999

    print("  GAHENAX AVALANCHE MONITOR — iniciando...")
    print(f"  Ledger: {LEDGER}")
    print(f"  Refresco: cada {REFRESH}s\n")

    for i in range(runs):
        print_status()
        if i < runs - 1:
            time.sleep(REFRESH)

    print("\n  [MONITOR] Ciclos completados.")

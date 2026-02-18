"""
recalibrate_gahenax_from_gimps.py

Objetivo:
1) Consumir https://www.mersenne.org/report_recent_results/ (feed reciente)
2) Extraer exponentes p y un resumen del resultado (PRP/LL/TF/ECM, etc.)
3) Construir un mapa de estado (gimps_state.jsonl)
4) Recalibrar umbrales adaptativos para el Gatekeeper (B: +k*sigma robusto)
5) Emitir policy.json para Gahenax Core v2.0 PCP
"""

from __future__ import annotations

import re
import json
import time
import math
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# -------------------------
# Config
# -------------------------

RECENT_RESULTS_URL = "https://www.mersenne.org/report_recent_results/"
UA = {"User-Agent": "GahenaxCore-v2.0-PCP-Recalibrator/1.0"}

# Regex robusto para detectar exponentes p en texto:
P_REGEX = re.compile(r"(?:\bM\s*([0-9]{2,9})\b|\b2\^\s*([0-9]{2,9})\b|\bp\s*=\s*([0-9]{2,9})\b|\bexponent\s+([0-9]{2,9})\b)", re.IGNORECASE)

# Clasificación “suave” por palabras clave
KIND_RULES = [
    ("PRP", re.compile(r"\bPRP\b", re.IGNORECASE)),
    ("LL", re.compile(r"\bLucas[- ]?Lehmer\b|\bLL\b", re.IGNORECASE)),
    ("TF", re.compile(r"\btrial factoring\b|\bTF\b", re.IGNORECASE)),
    ("ECM", re.compile(r"\bECM\b", re.IGNORECASE)),
    ("P-1", re.compile(r"\bP-1\b", re.IGNORECASE)),
    ("CERT", re.compile(r"\bcertif", re.IGNORECASE)),
]

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def safe_write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def median(xs: List[float]) -> float:
    ys = sorted(xs)
    n = len(ys)
    if n == 0:
        return float("nan")
    m = n // 2
    return ys[m] if n % 2 else 0.5 * (ys[m-1] + ys[m])

def mad(xs: List[float], med: float) -> float:
    return median([abs(x - med) for x in xs])

def robust_sigma_from_mad(mad_val: float, eps: float = 1e-12) -> float:
    return 1.4826 * max(mad_val, eps)

# -------------------------
# Fetch + Parse
# -------------------------

def fetch_recent_results_html(timeout_s: int = 20) -> str:
    try:
        import requests  # type: ignore
        r = requests.get(RECENT_RESULTS_URL, headers=UA, timeout=timeout_s)
        r.raise_for_status()
        return r.text
    except Exception:
        import urllib.request
        req = urllib.request.Request(RECENT_RESULTS_URL, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.read().decode("utf-8", errors="replace")

def classify_kind(text: str) -> str:
    for name, rx in KIND_RULES:
        if rx.search(text):
            return name
    return "UNKNOWN"

def extract_ps_from_text(text: str) -> List[int]:
    ps = []
    for m in P_REGEX.finditer(text):
        for g in m.groups():
            if g:
                try:
                    ps.append(int(g))
                except ValueError:
                    pass
    return ps

def parse_recent_results(html: str) -> List[Dict[str, Any]]:
    lines: List[str] = []
    try:
        from bs4 import BeautifulSoup  # type: ignore
        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(["tr", "li", "p"]):
            t = " ".join(el.get_text(" ", strip=True).split())
            if t:
                lines.append(t)
    except Exception:
        stripped = re.sub(r"<[^>]+>", "\n", html)
        for raw in stripped.splitlines():
            t = " ".join(raw.strip().split())
            if len(t) >= 10:
                lines.append(t)

    events: List[Dict[str, Any]] = []
    for ln in lines:
        ps = extract_ps_from_text(ln)
        if not ps:
            continue
        kind = classify_kind(ln)
        for p in set(ps):
            events.append({
                "timestamp": utc_now_iso(),
                "source": "mersenne_recent_results",
                "p": p,
                "kind": kind,
                "raw_hash": sha256_hex(ln),
                "raw_excerpt": ln[:240],
            })
    return events

# -------------------------
# Build state map
# -------------------------

def build_state_map(events: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    state: Dict[int, Dict[str, Any]] = {}
    for e in events:
        p = int(e["p"])
        s = state.setdefault(p, {
            "p": p,
            "last_seen": None,
            "kinds": {},
            "last_event": None,
        })
        s["last_seen"] = e["timestamp"]
        s["last_event"] = e
        k = e["kind"]
        s["kinds"][k] = int(s["kinds"].get(k, 0)) + 1
    return state

# -------------------------
# Recalibration
# -------------------------

@dataclass
class Policy:
    version: str = "GahenaxCore-v2.0-PCP-policy"
    updated_at: str = utc_now_iso()
    j_threshold: float = 0.70
    z_gate1: float = 3.0
    z_gate2: float = 3.0
    z_gate1_high: float = 3.5
    z_gate2_high: float = 3.5
    regime_bins: List[Tuple[int, int]] = None  # type: ignore

def default_regime_bins() -> List[Tuple[int, int]]:
    return [
        (2, 99999),
        (100000, 999999),
        (1000000, 9999999),
        (10000000, 99999999),
        (100000000, 999999999),
    ]

def assign_regime(p: int, bins: List[Tuple[int,int]]) -> str:
    for lo, hi in bins:
        if lo <= p <= hi:
            return f"{lo}-{hi}"
    return "out_of_range"

def recalibrate_policy_from_ledger(
    cert_ledger_path: str,
    bins: Optional[List[Tuple[int,int]]] = None,
    target_fp_rate: float = 0.01
) -> Policy:
    if bins is None:
        bins = default_regime_bins()

    rows = []
    with open(cert_ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("type") == "RUN_HEADER":
                continue
            if "p" in r and "metrics" in r:
                rows.append(r)

    per_regime: Dict[str, Dict[str, List[float]]] = {}
    for r in rows:
        p = int(r["p"])
        reg = assign_regime(p, bins)
        per_regime.setdefault(reg, {"z_h": [], "z_j": [], "j_mean": []})
        per_regime[reg]["z_h"].append(float(r["metrics"].get("z_h", 0.0)))
        per_regime[reg]["z_j"].append(float(r["metrics"].get("z_j", 0.0)))
        per_regime[reg]["j_mean"].append(float(r["metrics"].get("topk_jaccard_mean", 0.0)))

    def percentile(xs: List[float], q: float) -> float:
        if not xs:
            return float("nan")
        ys = sorted(xs)
        idx = int(min(len(ys)-1, max(0, round(q*(len(ys)-1)))))
        return ys[idx]

    global_z1, global_z2 = [], []
    high_z1, high_z2 = [], []
    high_regs = {"1000000-9999999", "10000000-99999999", "100000000-999999999"}

    for reg, d in per_regime.items():
        z1 = percentile(d["z_h"], 1.0 - target_fp_rate)
        z2 = percentile(d["z_j"], 1.0 - target_fp_rate)
        if not (math.isfinite(z1) and math.isfinite(z2)):
            continue
        global_z1.append(z1)
        global_z2.append(z2)
        if reg in high_regs:
            high_z1.append(z1)
            high_z2.append(z2)

    z_gate1 = median(global_z1) if global_z1 else 3.0
    z_gate2 = median(global_z2) if global_z2 else 3.0
    z_gate1_high = median(high_z1) if high_z1 else max(3.5, z_gate1)
    z_gate2_high = median(high_z2) if high_z2 else max(3.5, z_gate2)

    pol = Policy(
        updated_at=utc_now_iso(),
        j_threshold=0.70,
        z_gate1=round(float(z_gate1), 3),
        z_gate2=round(float(z_gate2), 3),
        z_gate1_high=round(float(z_gate1_high), 3),
        z_gate2_high=round(float(z_gate2_high), 3),
        regime_bins=bins
    )
    return pol

# -------------------------
# Main
# -------------------------

def main():
    html = fetch_recent_results_html()
    raw_snapshot_path = f"recent_results_snapshot_{int(time.time())}.html"
    with open(raw_snapshot_path, "w", encoding="utf-8") as f:
        f.write(html)

    events = parse_recent_results(html)
    safe_write_jsonl("gimps_recent_events.jsonl", events)

    state_map = build_state_map(events)
    state_rows = [{"timestamp": utc_now_iso(), **v} for v in state_map.values()]
    safe_write_jsonl("gimps_state.jsonl", state_rows)

    print(f"[OK] snapshot: {raw_snapshot_path}")
    print(f"[OK] events: gimps_recent_events.jsonl ({len(events)} rows)")
    print(f"[OK] state:  gimps_state.jsonl ({len(state_rows)} unique p)")

    try:
        # Note: Changed from cert_ledger.jsonl to cert_ledger_seismic.jsonl to match Step 1760 output
        pol = recalibrate_policy_from_ledger("cert_ledger_seismic.jsonl", target_fp_rate=0.01)
        with open("policy.json", "w", encoding="utf-8") as f:
            json.dump(asdict(pol), f, ensure_ascii=False, indent=2)
        print("[OK] policy: policy.json")
        print(f"     z_gate1={pol.z_gate1}  z_gate2={pol.z_gate2}  (high: {pol.z_gate1_high}/{pol.z_gate2_high})")
    except FileNotFoundError:
        print("[WARN] cert_ledger_seismic.jsonl no encontrado. Se generó solo GIMPS state.")

if __name__ == "__main__":
    main()

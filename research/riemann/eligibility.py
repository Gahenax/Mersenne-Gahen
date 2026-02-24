# eligibility.py
from __future__ import annotations
import json
import random
import hashlib
from dataclasses import dataclass
from typing import Set, Dict, Any, Optional

@dataclass
class EligibilityConfig:
    mode: str = "SOFT"        # "HARD" | "SOFT" | "AUTO"
    soft_rate: float = 0.02   # rho: % de blacklist que se deja pasar como control
    auto_soft_rate: float = 0.01
    auto_hard_when_ua_low: bool = True
    ua_low_threshold: float = 0.25  # ejemplo (25% UA restante)
    seed: int = 1337
    # determinismo por p (reproducible): si True, la decisión soft depende de hash(p,seed)
    deterministic_soft: bool = True

class EligibilityPolicy:
    def __init__(self, blacklist: Set[int], cfg: EligibilityConfig):
        self.blacklist = blacklist
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)

    def _hash01(self, p: int) -> float:
        h = hashlib.sha256(f"{p}:{self.cfg.seed}".encode()).hexdigest()
        # tomar 8 hex = 32 bits
        x = int(h[:8], 16)
        return x / (2**32 - 1)

    def allow(self, p: int, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Returns decision dict:
          { "allow": bool, "reason": str, "mode": str, "p": int }
        context can include: {"ua_remaining": 0..1, "calibration": bool}
        """
        context = context or {}
        ua_remaining = float(context.get("ua_remaining", 1.0))
        calibration = bool(context.get("calibration", False))

        mode = self.cfg.mode.upper()

        # AUTO: decide mode based on context
        if mode == "AUTO":
            if calibration:
                mode_eff = "SOFT"
                soft_rate = self.cfg.auto_soft_rate
            elif self.cfg.auto_hard_when_ua_low and ua_remaining <= self.cfg.ua_low_threshold:
                mode_eff = "HARD"
                soft_rate = 0.0
            else:
                mode_eff = "SOFT"
                soft_rate = self.cfg.auto_soft_rate
        elif mode == "HARD":
            mode_eff = "HARD"
            soft_rate = 0.0
        else:
            mode_eff = "SOFT"
            soft_rate = self.cfg.soft_rate

        in_blacklist = (p in self.blacklist)

        if not in_blacklist:
            return {"allow": True, "reason": "not_blacklisted", "mode": mode_eff, "p": p}

        # blacklisted:
        if mode_eff == "HARD":
            return {"allow": False, "reason": "blacklisted_hard_block", "mode": mode_eff, "p": p}

        # SOFT: allow with probability rho (control negative sampling)
        if self.cfg.deterministic_soft:
            u = self._hash01(p)
        else:
            u = self.rng.random()

        allow = (u < soft_rate)
        return {
            "allow": allow,
            "reason": "blacklisted_soft_pass" if allow else "blacklisted_soft_skip",
            "mode": mode_eff,
            "p": p,
            "soft_rate": soft_rate,
            "u": u,
        }

def load_blacklist(path: str) -> Set[int]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict):
            xs = obj.get("blacklist", [])
        else:
            xs = obj
        return set(int(p) for p in xs)
    except FileNotFoundError:
        return set()

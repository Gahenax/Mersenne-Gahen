#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHIM: This module has been moved to the central Ouroboros-v2-Sigil engine.
Please refer to .agent/sigil_mirrors/phase3_prereg.py
"""

import sys
import os
from pathlib import Path

# Insert the central .agent path
AGENT_PATH = os.path.abspath(os.path.join(Path(__file__).resolve().parent.parent.parent.parent, ".agent", "sigil_mirrors"))
sys.path.insert(0, AGENT_PATH)

from phase3_prereg import *

if __name__ == "__main__":
    import phase3_prereg
    sys.exit(phase3_prereg.main())

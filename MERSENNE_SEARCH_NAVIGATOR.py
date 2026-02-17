import json
import time
from pathlib import Path
from MERSENNE_PROBE_V1 import MersenneEngine

class SearchNavigator:
    def __init__(self, engine):
        self.engine = engine
        self.found_candidates = []

    def scan_range(self, start_p, end_p):
        print(f"\n[SEARCH NAVIGATOR] Initiating P1-SEARCH in range p=[{start_p}, {end_p}]")
        print("-" * 50)
        
        # Sieve: Only odd exponents are candidates for Mersenne primes (except p=2)
        candidates = [p for p in range(start_p, end_p + 1) if p % 2 != 0]
        
        for p in candidates:
            # P1: Fast Probabilistic Test
            is_probable, residue, dt = self.engine.prp_test(p)
            
            if is_probable:
                print(f"  [!] CANDIDATE FOUND: p={p} (PRP residue matched) dt={dt:.4f}s")
                self.found_candidates.append(p)
            else:
                if p % 50 == 1 or p % 50 == 0: # Status update every 50
                    print(f"  ... scanning p={p} (Negative)")

        print("-" * 50)
        print(f"Total candidates detected: {len(self.found_candidates)}")
        return self.found_candidates

if __name__ == "__main__":
    import sys
    engine = MersenneEngine()
    nav = SearchNavigator(engine)
    
    start_p = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    end_p = int(sys.argv[2]) if len(sys.argv) > 2 else 1300
    
    found = nav.scan_range(start_p, end_p)
    
    if found:
        print("\n[SCENARIO]: Writing findings to Mission Control...")
        with open("search_results.json", "w") as f:
            json.dump({"found_p": found, "timestamp": time.time()}, f)

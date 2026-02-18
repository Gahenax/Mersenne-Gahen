import hashlib
import time
import json
import sys
from pathlib import Path

# Increase limit for integer string conversion (M_19937+ compatibility)
if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(50000)

class MersenneEngine:
    """
    Antigravity Mersenne Engine - Epistemological Edition v1.1
    Detailed metrology, fault injection, and performance tracking.
    """
    def __init__(self, dps=80, fault_injection=False, artifact_base="artifacts"):
        self.dps = dps
        self.fault_injection = fault_injection
        self.artifact_base = Path(artifact_base)
        self.metrology = {
            "total_prp_time": 0.0,
            "total_ll_time": 0.0,
            "discards": 0,
            "certifications": 0,
            "faults_detected": 0
        }

    def get_artifact_path(self, p, file_type="evidence"):
        path = self.artifact_base / str(p)
        path.mkdir(parents=True, exist_ok=True)
        if file_type == "evidence":
            return path / f"evidence_{p}.json"
        elif file_type == "checkpoint":
            return path / f"checkpoint_{p}.json"
        return path / f"{file_type}_{p}.json"

    def prp_test(self, p):
        """
        Probabilistic Primality Test (PRP) with Metrology.
        """
        if p % 2 == 0 and p > 2: return False, 0, 0.0
        start_time = time.time()
        m_p = (1 << p) - 1
        
        # Fault injection simulation: simulate bit-flip during pow
        res = pow(3, (m_p - 1) // 2, m_p)
        if self.fault_injection:
            res = (res + 1) % m_p
            
        duration = time.time() - start_time
        self.metrology["total_prp_time"] += duration
        
        is_probable_prime = (res == m_p - 1)
        if not is_probable_prime:
            self.metrology["discards"] += 1
            
        return is_probable_prime, res, duration

    def lucas_lehmer(self, p, checkpoint_cadence=1000):
        """
        Lucas-Lehmer test with Persistence and Dual-Path Verification.
        """
        if p == 2: return True, 0, 0.0
        start_time = time.time()
        m_p = (1 << p) - 1
        s = 4
        
        # Persistence Logic
        cp_file = self.get_artifact_path(p, "checkpoint")
        start_iter = 0
        
        if cp_file.exists():
            print(f"  -> Resuming from checkpoint: {cp_file}")
            with open(cp_file, "r") as f:
                data = json.load(f)
                # Verify Hash to prevent corruption (Audit B2)
                recorded_hash = data.get("hash")
                payload = f"{data['s']}-{data['iter']}"
                if recorded_hash != hashlib.sha256(payload.encode()).hexdigest():
                    print(f"  !!! [RED]: Checkpoint CORRUPTION detected.")
                    return False, -1, 0.0, 1.0 # RED State
                s = data["s"]
                start_iter = data["iter"]

        # LL Loop
        for i in range(start_iter, p - 2):
            # Dual-Path Verification (Audit B3)
            # Path A: Standard
            s_next_a = (s * s - 2) % m_p
            
            # Path B: Bitwise Optimization (Mersenne property: x % (2^p-1) == (x & (2^p-1)) + (x >> p))
            sq = s * s - 2
            s_next_b = (sq & m_p) + (sq >> p)
            if s_next_b >= m_p: s_next_b -= m_p
            
            if s_next_a != s_next_b:
                print(f"  !!! [RED]: Dual-Path MISMATCH at iter {i}")
                return False, -2, 0.0, 1.0 # RED State
                
            s = s_next_a
            
            # Checkpointing
            if (i + 1) % checkpoint_cadence == 0:
                self.save_checkpoint(p, s, i + 1)

        duration = time.time() - start_time
        self.metrology["total_ll_time"] += duration
        
        is_prime = (s == 0)
        if is_prime:
            self.metrology["certifications"] += 1
            if cp_file.exists(): cp_file.unlink() # Clean up on success
            
        return is_prime, s, duration, 0.0

    def save_checkpoint(self, p, s, itinerary):
        cp_file = self.get_artifact_path(p, "checkpoint")
        payload = f"{s}-{itinerary}"
        data = {
            "p": p,
            "s": s,
            "iter": itinerary,
            "hash": hashlib.sha256(payload.encode()).hexdigest(),
            "timestamp": time.time()
        }
        with open(cp_file, "w") as f:
            json.dump(data, f)

    def run_p0_boot(self):
        """
        P0 (Boot): Hardware and logic integrity check using known small primes.
        """
        print("\n[P0-BOOT] Initializing Hardware/Logic Audit...")
        test_cases = [
            (3, True),   # M3 = 7
            (5, True),   # M5 = 31
            (7, True),   # M7 = 127
            (11, False), # M11 = 2047 (23 * 89)
            (13, True),  # M13 = 8191
        ]
        
        results = []
        for p, expected in test_cases:
            is_prime, residue, dt = self.lucas_lehmer(p)
            match = (is_prime == expected)
            status = "PASS" if match else "FAIL"
            print(f"  - M_{p:2d}: {status} (dt={dt:.6f}s)")
            results.append(match)
            
        integrity = all(results)
        return integrity

def main():
    engine = MersenneEngine()
    
    # Run P0
    if engine.run_p0_boot():
        print("\nOK: [INTEGRITY]: P0-BOOT SUCCESSFUL. ALU and Logic Gates certified.")
        
        # Deploy P1/P2 on a target exponent if requested
        # For now, let's target M_127 (a known prime) to verify deeper logic
        target_p = 127
        print(f"\n[P2-VERIFY] Testing M_{target_p} (Lucas-Lehmer Certification)...")
        is_p, res, dt = engine.lucas_lehmer(target_p)
        
        residue_hash = hashlib.sha256(str(res).encode()).hexdigest()
        
        report = {
            "p": target_p,
            "is_prime": is_p,
            "residue_hash": residue_hash,
            "wall_time": dt,
            "status": "GREEN" if is_p else "YELLOW"
        }
        
        print(json.dumps(report, indent=2))
        
        with open("mersenne_evidence_M127.json", "w") as f:
            json.dump(report, f, indent=2)
    else:
        print("\nERROR: [CRITICAL]: P0-BOOT FAILED. Hardware or Logic instability detected.")
        sys.exit(1)

if __name__ == "__main__":
    main()

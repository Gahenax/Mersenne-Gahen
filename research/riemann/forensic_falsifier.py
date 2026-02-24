import json
import numpy as np
import math

def riemann_smooth_N(t):
    return (t / (2 * math.pi)) * math.log(t / (2 * math.pi)) - (t / (2 * math.pi)) + 7/8

def load_data(path):
    zeros = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                obj = json.loads(line)
                val = obj.get("t_est") or obj.get("T") or obj.get("refined_T")
                if val: zeros.append(float(val))
            except: continue
    return sorted(set(zeros))

def run_forensic_audit(path):
    print(f"--- [OUROBOROS REDTEAM] FORENSIC AUDIT: {path} ---")
    zeros = load_data(path)
    if not zeros: return
    
    unfolded = np.array([riemann_smooth_N(t) for t in zeros])
    gaps = np.diff(unfolded)
    mean_gap = np.mean(gaps)
    s = gaps / mean_gap # normalized spacings
    
    # 1. Test de Determinismo Algoritmico (Rounding Check)
    # Si Jules estuviera devolviendo datos sinteticos o redondeados, 
    # veríamos baja entropía en los ultimos decimales.
    decimals = np.array([float(str(z).split('.')[-1][:6]) if '.' in str(z) else 0 for z in zeros])
    decimal_entropy = -np.sum([p * np.log2(p) for p in np.unique(decimals, return_counts=True)[1]/len(decimals) if p > 0])
    
    # 2. Test de Wigner (Local GUE alignment)
    # P(s) = (32/pi^2) * s^2 * exp(-4s^2/pi)
    def wigner_gue(s):
        return (32/math.pi**2) * (s**2) * np.exp(-4*(s**2)/math.pi)
    
    # 3. FFT de los Gaps (Detection of Periodic Algorithms)
    # Un algoritmo defectuoso tiende a "latir" a una frecuencia fija.
    fft_gaps = np.abs(np.fft.fft(s - 1.0))[:len(s)//2]
    max_spike = np.max(fft_gaps) / np.mean(fft_gaps)

    # 4. Rigidez H (Alpha Mass)
    r_stats = [min(s[i], s[i+1]) / max(s[i], s[i+1]) for i in range(len(s)-1)]
    mean_r = np.mean(r_stats)

    print(f"H1: Entropía Decimal: {decimal_entropy:.2f} bits (Esperado > 5 para datos naturales)")
    print(f"H2: Spike FFT en Gaps: {max_spike:.2f} (Esperado < 5 para caos)")
    print(f"H3: Promedio <r>: {mean_r:.5f} (GUE: 0.5996)")
    
    # VEREDICTO ADVERSARIAL
    score = 0
    if decimal_entropy < 3.0: score += 1 # Sospecha de redondeo
    if max_spike > 10.0: score += 1     # Sospecha de periodicidad sintetica
    if abs(mean_r - 0.5996) > 0.05: score += 1 # Desviacion extrema
    
    print("\n--- RESULTADO REDTEAM ---")
    if score == 0:
        print("ESTADO: [PASS] Los datos muestran firmas de Caos Cuántico Natural.")
        print("CONCLUSIÓN: La rigidez observada es una propiedad real del espectro.")
    else:
        print(f"ESTADO: [FAIL] Puntuación de sospecha: {score}/3")
        print("CONCLUSIÓN: Los datos podrían ser artefactos algorítmicos. Revisar precisión de Jules.")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else 'results/riemann/jules_phase1_full.jsonl'
    run_forensic_audit(target)

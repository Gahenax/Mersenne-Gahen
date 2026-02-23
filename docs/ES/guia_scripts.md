# Guía de Scripts — Laboratorio Gahenax / Hodge-Rigidity

> **Política de idiomas:** El código Python está en inglés (estándar internacional de revisión científica). Esta guía es la documentación oficial en español para colaboradores hispanohablantes.

---

## Índice

1. [Instrumentos espectrales](#1-instrumentos-espectrales)
2. [Pipeline Phase-3 (Jules)](#2-pipeline-phase-3-jules)
3. [Auditoría y validación](#3-auditoría-y-validación)
4. [Análisis de resonancia](#4-análisis-de-resonancia)
5. [Flujo de trabajo completo](#5-flujo-de-trabajo-completo)

---

## 1. Instrumentos espectrales

### `mersenne_spectral_poc.py`
**Prueba de concepto: huellas de Mersenne en el espectro de Riemann**

Implementa el estadístico de la fórmula explícita de Guinand-Weil:

$$S(u) = \sum_{\gamma} w(\gamma) \cdot e^{i\gamma u}$$

Evaluado en $u = \log(M_k) = \log(2^k - 1)$, debería mostrar exceso estadístico cuando $M_k$ es primo respecto a cuando $M_k$ es compuesto.

**Tres capas pre-registradas:**
- **Capa A — Sanidad:** Verifica que el instrumento detecta picos en $u = \log p$ para primos pequeños $p = 2, 3, 5, 7$. Si falla, el resto no tiene sentido.
- **Capa B — Mersenne vs Control:** Test A/B falsable. $k$ con $M_k$ primo vs $k$ con $M_k$ compuesto. Métrica: AUC (área bajo curva ROC). Umbral de éxito: AUC ≥ 0.60.
- **Capa C — Estructura del 2:** Energía en $u = k \log 2$ para $k = 1 \ldots 30$. Exploratoria, sin umbral.

**Nulo estadístico:** Aleatorización de fase — reemplaza $e^{i\gamma u}$ por $e^{i\phi_k}$ con $\phi_k \sim U[0, 2\pi]$. Destruye la coherencia sin alterar los pesos de ventana.

**Cómo ejecutar:**
```bash
python scripts/mersenne_spectral_poc.py
```

---

### `poc_25_mersenne.py`
**POC con 25 exponentes Mersenne certificados**

Extensión del POC anterior con los primeros 25 exponentes Mersenne verificados por GIMPS, comparados contra 25 exponentes control ($k$ primo, $M_k$ compuesto).

Desglose de AUC por rango de $k$:
- $k \leq 127$: amplitud detectable teóricamente ($\sim 10^{-2}$ a $10^{-8}$)
- $k > 521$: amplitud $\sim 1/\sqrt{M_k} \approx 0$, test de ruido puro (valida el nulo)

**Resultado Phase-1 (N=332 ceros):**
- AUC global: 0.562 — ligeramente por encima del azar
- AUC ($k \leq 127$): 0.603 — señal real emergente, insuficiente con N=332

**Cómo ejecutar:**
```bash
python scripts/poc_25_mersenne.py
```

---

## 2. Pipeline Phase-3 (Jules)

### `phase3_aggregator.py`
**Agregador de bloques + Gate 0: integridad**

Lee los bloques de ceros generados por Jules (20 bloques independientes, $T \in [7000, 15000]$) y ejecuta controles de calidad antes de cualquier análisis espectral.

**Gate 0 — Controles de integridad:**
| Check | Criterio |
|:------|:---------|
| G0.1 Monotonicidad | $\gamma_{i+1} > \gamma_i$ para todo $i$ |
| G0.2 Sin duplicados | No hay pares con diferencia $< 10^{-6}$ |
| G0.3 Densidad esperada | Gap medio dentro del 20% del teórico $2\pi/\log T$ |
| G0.4 N suficiente | $N \geq 10{,}000$ |

**Gate 1 temprano (sanidad):** Se ejecuta en cuanto hay 2000 ceros. Si falla antes de completar los 20 bloques, se aborta — evita gastar computación Jules en datos defectuosos.

**Salidas:**
```
results/riemann/RIEMANN_GAMMAS_PHASE3.npy   ← array float64 ordenado
results/riemann/PHASE3_MANIFEST.json         ← metadatos, sha256, rango
results/riemann/PHASE3_INTEGRITY_REPORT.json ← veredicto gates 0 y 1
```

**Cómo ejecutar (una vez Jules entregue los shards):**
```bash
python scripts/phase3_aggregator.py
```

---

### `layer_c_adversarial.py`
**Auditoría adversarial de los picos en $u = k \log 2$**

En Phase-1 se detectaron picos anómalos en $k = 10, 11, 29$. Este script determina si son artefactos o estructura real, sometiéndolos a tres nulos distintos en tres ventanas de $T$ no solapadas.

**Protocolo de supervivencia:**
Un pico "sobrevive" solo si:
- Tiene $z > 1.5$ en $\geq 2$ de los 3 métodos de nulo
- Y eso se cumple en $\geq 2$ de las 3 ventanas de $T$

**Tres métodos de nulo:**
1. **Aleatorización de fase** — destruye toda coherencia en $u$
2. **Permutación de bloques** — permuta bloques de $\gamma$ consecutivos, preserva densidad local
3. **Sustituto GUE** — reemplaza los ceros por espaciados sintéticos con distribución Wigner-GUE

Si el pico muere ante cualquiera de estos: es artefacto de ventana/nulo. Si sobrevive los tres: hay estructura real en $u = k \log 2$ que merece capítulo propio.

**Hipótesis competidoras para $k = 10, 11, 29$:**
1. Artefacto de leakage espectral por elección de $\Delta T$
2. Artefacto de nulo mal calibrado
3. Estructura real de potencias $p^m$ (no primalidad Mersenne)
4. Coincidencia estadística con $N = 332$

**Cómo ejecutar (requiere RIEMANN_GAMMAS_PHASE3.npy):**
```bash
python scripts/layer_c_adversarial.py
```

---

## 3. Auditoría y validación

### `audit_dataset.py`
**Auditoría completa del dataset Phase-1**

Carga todos los shards del ledger y calcula estadísticas de espectro completas:

| Métrica | Qué mide |
|:--------|:---------|
| Gaps naturales (T) | Espaciado bruto, media, std |
| Gaps normalizados | Tras unfolding, deben tener media = 1 |
| r-statistic | Orden local; GUE esperado: $\langle r \rangle \approx 0.5996$ |
| ACF lag-1 | Correlación entre gaps consecutivos; GUE: $\approx -0.25$ |
| FFT de residuos | Busca periodicidades en la densidad |
| $\Sigma^2(L)$ | Varianza numérica; GUE: $\sim \frac{1}{\pi^2}(\log L + \text{cte})$ |

**Cómo ejecutar:**
```bash
python scripts/audit_dataset.py
```

---

### `phase2_probe_recal.py`
**Recalibración de sondas Phase-2: $S(P)$, $C$, $\alpha$**

Estima tres métricas globales sobre los 332 ceros de Phase-1:

- **$S(P)$** — fracción de energía de gaps explicada por los primeros 11 primos via ajuste de resonancias
- **$C$** — puntuación de caos residual (1.0 = completamente GUE-like)
- **$\alpha$** — exponente efectivo del escalado $\Sigma^2(L) \sim L^\alpha$ (Poisson: $\alpha \approx 1$; GUE: $\alpha \approx 0$; rígido: $\alpha < 0$)

El estimador de $\Sigma^2(L)$ usa **orígenes aleatorios** para evitar correlaciones espurias de ventanas solapadas (ver Appendix A del reporte LaTeX).

**Cómo ejecutar:**
```bash
python scripts/phase2_probe_recal.py
```

---

## 4. Análisis de resonancia

### `prime_resonance_analysis.py`
**Correlación entre el eco espectral y las frecuencias de primos**

Verifica que el pico dominante en la FFT de los residuos del unfolding corresponde a un primo específico vía la fórmula explícita. Cada primo $p$ induce oscilaciones de período:

$$T_p = \frac{2\pi}{\log p} \quad \text{[en unidades de T]}$$

Lo que equivale a frecuencia (en ciclos/cero):
$$f_p = \frac{\bar{\delta}_T \cdot \log p}{2\pi}$$

El análisis muestra que el pico en $f \approx 0.099$ ciclos/cero corresponde al primo dominante, con error de ajuste $< 5\%$.

**Cómo ejecutar:**
```bash
python scripts/prime_resonance_analysis.py
```

---

### `analyze_spectral_stats.py` / `riemann_pattern_miner.py`
**Scripts de apoyo para estadísticas espectrales**

Calculan métricas auxiliares del espectro (distribución de gaps, ACF, FFT). Usados en las fases preliminares del análisis.

---

## 5. Flujo de trabajo completo

```
                    PHASE-1 (completada)
                    ─────────────────────
   jules_phase1_full.jsonl  →  audit_dataset.py
                           →  phase2_probe_recal.py
                           →  prime_resonance_analysis.py
                           →  mersenne_spectral_poc.py    [POC N=332]
                           →  poc_25_mersenne.py          [25 MP, N=332]

                    PHASE-3 (pendiente Jules)
                    ─────────────────────────
   Jules bloques 0–19      →  phase3_aggregator.py       [Gate 0 + Gate 1]
                               ↓ (si gates pasan)
                           →  mersenne_spectral_poc.py    [N=12000]
                           →  poc_25_mersenne.py          [AUC objetivo ≥ 0.65]
                           →  layer_c_adversarial.py      [k=10,11,29]
```

### Gates de decisión

| Gate | Condición de éxito | Acción si falla |
|:-----|:-------------------|:----------------|
| **Gate 0** | Integridad: monotonicidad, duplicados, densidad, N≥10000 | Rechazar shards defectuosos |
| **Gate 1** | Sanidad: ≥ 4/8 primos $p$ con $z > 1.5$ | Abortar análisis espectral |
| **Gate 2** | AUC($k \leq 127$) ≥ 0.60 | Archivar hipótesis B |
| **Gate 3** | Layer C: $k$ anómalos sobreviven protocolo adversarial | Cerrar anomalía como artefacto |

---

## Glosario rápido (código → concepto)

| Término en código | Concepto en español |
|:------------------|:--------------------|
| `gammas` | Ordinadas de ceros de Riemann ($\gamma_n$ tal que $\zeta(\frac{1}{2} + i\gamma_n) = 0$) |
| `unfolding` | Normalización espectral por la función de conteo $N(T)$ |
| `S(u)` | Estadístico de la fórmula explícita evaluado en frecuencia $u$ |
| `null_distribution` | Distribución nula por aleatorización de fase |
| `z-score` | Desviación estándar sobre el nulo |
| `AUC` | Área bajo la curva ROC: $P(\text{primo} > \text{control})$ |
| `GUE` | Ensemble Unitario Gaussiano (referencia de caos cuántico) |
| `Layer A/B/C` | Capas del POC: sanidad / test A-B / estructura del 2 |
| `Phase-1/3` | Fases del experimento por rango de $T$ |

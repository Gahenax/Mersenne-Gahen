# TRANSITION.md — Fronteras de Certificabilidad

## 1. El Desacople Probabilístico vs Determinista
Se identifica una frontera operativa entre la búsqueda mediante **PRP (Euler Criterion)** y la certificación **LL (Lucas-Lehmer)**.
- **P1 (Search)**: Eficiente para el descarte masivo de candidatos no-primos.
- **P2 (Verify)**: Única fuente de verdad determinista aceptable para el Ledger.

## 2. La Frontera de Integridad Instrumental
La certificabilidad no depende solo de la matemática del número, sino de la estabilidad del instrumento (ALU/FFT).
- **Ruptura de Integridad**: Definida por un error de redondeo (Roundoff) $> 0.40$.
- **Fenómeno Observado**: En inyecciones de fallo controladas (Ruta B), el sistema detecta la corrupción antes de emitir un veredicto falso, marcando el estatus **RED**.

## 3. Límite de la Memoria
A medida que el exponente $p$ crece, la ventana de integridad se estrecha. El "Desacople del Auditor" en este contexto ocurre cuando el error de redondeo acumulado invalida el bit-check del residuo.

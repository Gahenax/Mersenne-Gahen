# RESEARCH_LOG.md — Bitácora Metodológica Mersene Gahenax

## 1. Scope
Este log documenta la transición tecnológica de la investigación Riemann hacia la certificación determinista de primos grandes en el laboratorio **MERSENE GAHENAX**.

## 2. Pregunta Inicial
¿Es posible recalibrar un entorno de minería heurística para que produzca verdades matemáticas deterministas (LL) con la misma eficiencia y rigor de auditoría?

## 3. Decisiones de Instrumentación
- **Elección LL**: Se seleccionó el test de Lucas-Lehmer por su carácter binario y concluyente para números de Mersenne.
- **Implementación PRP**: Se añadió el criterio de Euler como filtro de alta velocidad (Ruta A) para optimizar el uso de UA (Unidades Athena).
- **Gate de Ruido**: Se fijó el umbral de 0.40 como breakpoint de integridad inyectable.

## 4. Cronología de Hallazgos
- **T0 (Recalibración)**: Creación del `Mersenne Recalibration Pack`. Mapeo de `seed` -> `p`.
- **T1 (Boot)**: Ejecución de P0. Certificación de la ALU mediante exponentes conocidos ($p < 127$).
- **T2 (Escala)**: Procesamiento del rango [1200, 2500]. Identificación y certificación de $M_{1279}, M_{2203}, M_{2281}$.
- **T3 (Fragilidad)**: Inyección de fallo en $M_{1279}$. Validación del estado **RED**.

## 5. Criterio de Cierre
El proyecto se considera estable al demostrar un hit-rate de integridad del 100% en pruebas de inyección de fallo y una escalabilidad lineal en el coste computacional por bit procesado.

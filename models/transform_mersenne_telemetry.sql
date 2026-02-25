-- ============================================================================
-- OEDA DataOps: dbt Model para Transformar Métricas de Telemetría (Mersenne)
-- ============================================================================
-- Este modelo transforma los archivos JSON L en crudo que salen de 
-- 'riemann_avalanche' en una vista consolidada para Analytics BI (Superset/Looker).

{{ config(materialized='table') }}

WITH raw_telemetry AS (
    -- La fuente de datos inyectada por el pipeline ELT (ej. Airbyte desde S3)
    SELECT * FROM {{ source('oeda_warehouse', 'raw_mersenne_telemetry') }}
),

parsed_events AS (
    SELECT
        event_id,
        CAST(json_extract_path_text(raw_json, 'timestamp') AS TIMESTAMP) AS time_logged,
        json_extract_path_text(raw_json, 'experiment') AS experiment_name,
        CAST(json_extract_path_text(raw_json, 'variance') AS FLOAT) AS spectral_variance,
        CASE
            WHEN CAST(json_extract_path_text(raw_json, 'variance') AS FLOAT) > 0.178 THEN 'ANOMALY'
            ELSE 'STABLE'
        END as gue_state
    FROM raw_telemetry
)

SELECT
    DATE_TRUNC('hour', time_logged) as event_hour,
    experiment_name,
    AVG(spectral_variance) as mean_hourly_variance,
    COUNT(CASE WHEN gue_state = 'ANOMALY' THEN 1 END) as anomaly_count,
    COUNT(*) as total_events
FROM parsed_events
GROUP BY 1, 2
ORDER BY 1 DESC

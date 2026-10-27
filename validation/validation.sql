-- =====================================================================
-- IRIS-SIG-17: Berlin Bebauungspläne Portal Harvester
-- Database Staging Validation Queries
-- Target Schema: iris_staging
-- Target Table:  iris_staging.signal_ingest
-- Database:      PostgreSQL 16 / PostGIS 3.4
-- =====================================================================

-- 1. Verify schema and table creation
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_schema = 'iris_staging' AND table_name = 'signal_ingest';

-- 2. Total record count in staging
SELECT count(*) AS total_ingested_signals 
FROM iris_staging.signal_ingest;

-- 3. Signal breakdown by classified domain type
SELECT 
    signal_type, 
    count(*) AS signal_count,
    round(avg(confidence_score)::numeric, 2) AS avg_confidence
FROM iris_staging.signal_ingest
GROUP BY signal_type
ORDER BY signal_count DESC;

-- 4. Idempotency & Unique constraint validation
-- (Must return 0 rows to prove zero duplicate source_ids exist)
SELECT 
    source_id, 
    count(*) AS occurrences
FROM iris_staging.signal_ingest
GROUP BY source_id
HAVING count(*) > 1;

-- 5. Spatial validation (EPSG:25832)
-- Validates coordinate bounds in UTM zone 32N and non-null geometry
SELECT 
    source_id,
    district,
    location_status,
    round(easting_25832::numeric, 1) AS easting_m,
    round(northing_25832::numeric, 1) AS northing_m,
    ST_AsText(geom) AS postgis_wkt
FROM iris_staging.signal_ingest
ORDER BY location_status ASC;

-- 6. Unresolved / Ambiguous location audit
-- Checks records where coordinates could not be resolved or were invalid
SELECT 
    source_id, 
    title, 
    location_status, 
    metadata_json->'validation_notes' AS validation_notes
FROM iris_staging.signal_ingest
WHERE location_status != 'resolved';

-- 7. Audit recency check
SELECT 
    source_id,
    created_at,
    updated_at,
    (updated_at > created_at) AS was_updated_on_rerun
FROM iris_staging.signal_ingest
ORDER BY updated_at DESC;

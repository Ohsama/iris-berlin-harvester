# 📊 IRIS-SIG-17 Data Quality & Error Report

**Task**: Berlin Bebauungspläne Portal Harvester  
**Integration Pattern**: B (HTML Harvester)  
**Target Destination**: `iris_staging.signal_ingest`  
**Projection**: EPSG:25832 (ETRS89 / UTM zone 32N)  

---

## 1. Executive Summary

This report documents data quality observations, anomaly detection, coordinate validation rules, and error handling behaviors observed during harvesting of the Berlin Bebauungsplan notices.

The ingestion pipeline was verified against representative fixtures covering:
- Urban industrial reconversion filings (`urban_industrial_reconversion`)
- High-power substation infrastructure alerts (`high_power_substation_alert`)
- Edge data center campus filings (`edge_dc_filing`)
- Purely residential/non-industrial filings (correctly excluded)
- Malformed inputs (unparseable dates, corrupted coordinates)

---

## 2. Source Endpoint Status (HTTP 410 Gone Investigation)

- **Configured Endpoint in Brief**: `https://berlin.de/bebauungsplaene`
- **Network Probe Result**: `HTTP 410 (Gone)`
- **Investigation**:
  The legacy URL path `https://berlin.de/bebauungsplaene` has been retired by the Berlin state administration. Active Bebauungsplan notices and spatial geometries are now hosted on:
  1. **Geoportal Berlin (FIS-Broker)**: The spatial WFS/WMS and B-Plan search catalog (`https://gdi.berlin.de`).
  2. **Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen**: Formal procedure notices under `https://www.berlin.de/sen/stadtentwicklung/planung/bebauungsplanverfahren/`.
  3. **Bezirksämter Stadtentwicklungsämter**: District-level publication lists.
- **Resilience Design**:
  Following the **Candidate Notes** in the task brief:
  > *"If an endpoint, feed, or HTML selector in the brief is obsolete or inaccessible, document the issue and provide a tested fixture-based implementation and a justified alternative."*
  
  The harvester detects HTTP 410 cleanly, logs the deprecation without crashing, records diagnostic notes in the ingestion metadata, and supports full offline execution via validated HTML fixtures (`fixtures/`).

---

## 3. Data Cleansing & Validation Rules

### A. Coordinate Projection & Bounds Check
- **Target Projection**: `EPSG:25832` (ETRS89 / UTM 32N in meters).
- **Validation**:
  - Raw WGS84 coordinates are verified to reside within the greater Berlin metropolitan bounding box (`52.2 <= lat <= 52.8`, `12.9 <= lon <= 13.9`).
  - Out-of-bounds coordinates are tagged as `location_status = 'invalid'` and logged.
  - Corrupted string values (e.g. `'CORRUPT_LAT'`) are trapped, logged with warnings, and preserved as `location_status = 'invalid'` rather than crashing or silently inserting `(0, 0)`.
  - Coordinates are projected to metric coordinates:
    - Example: `(52.53120, 13.33640)` $\rightarrow$ `Easting: 794,228.6m, Northing: 5,829,088.1m` in `EPSG:25832`.

### B. Publication Date Normalization
- Dates are normalized to ISO-8601 `YYYY-MM-DD`.
- Multiple German and international date formats (`YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY`) are parsed.
- Corrupted dates (e.g. `'ungültig-datum'`) are recorded as `NULL` with a validation error note in `metadata_json`.

### C. Signal Relevance & Noise Filtering
- Projects lacking industrial, energy, or data center relevance (such as purely residential developments, e.g., `PAN-05-RES`) are filtered out at the transformer stage to maintain high precision in `iris_staging`.

---

## 4. Idempotency & Repeatability Metrics

| Metric | First Run | Re-Run (Same Data) | Mixed Batch (1 New, 1 Update, 1 Duplicate) |
| :--- | :--- | :--- | :--- |
| **Submitted Records** | 4 | 4 | 3 |
| **Unique Processed** | 4 | 4 | 2 |
| **New Inserts** | 4 | 0 | 1 |
| **Updates** | 0 | 4 | 1 |
| **Duplicates Skipped** | 0 | 0 | 1 |
| **Database Row Count** | 4 | 4 | 5 |

**Conclusion**: Re-running the pipeline is strictly idempotent. No duplicate rows can enter the staging table.

---

## 5. Summary of Harvested Fixture Records

| Source ID | District | Signal Type | Confidence | Coords (WGS84) | EPSG:25832 (Easting / Northing) | Location Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `I-B14a` | Mitte | `urban_industrial_reconversion` | 0.85 | 52.5312, 13.3364 | 794228.6m / 5829088.1m | `resolved` |
| `SPA-88-UW` | Spandau | `high_power_substation_alert` | 1.00 | 52.5458, 13.2351 | 787309.4m / 5830282.8m | `resolved` |
| `MZ-B202-DC` | Marzahn | `edge_dc_filing` | 1.00 | 52.5510, 13.5380 | 807849.0m / 5831969.8m | `resolved` |
| `NK-ERR-99` | Neukölln | `high_power_substation_alert` | 0.70 | Invalid format | NULL / NULL | `invalid` |
| `PAN-05-RES` | Pankow | *(Non-relevant residential)* | 0.00 | 52.5701, 13.4025 | N/A | Excluded |

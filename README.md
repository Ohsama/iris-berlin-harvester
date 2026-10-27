# 🏛️ IRIS-SIG-17: Berlin Bebauungspläne Portal Harvester

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![PostGIS 3.4](https://img.shields.io/badge/PostGIS-3.4-5B8C00.svg)](https://postgis.net/)
[![Spatial CRS](https://img.shields.io/badge/CRS-EPSG%3A25832-orange.svg)](https://epsg.io/25832)
[![Tests](https://img.shields.io/badge/pytest-16%20passed-brightgreen.svg)]()

Production-grade HTML Harvester, Domain Signal Classifier, and PostGIS Ingestion Pipeline developed for **IRIS Technical Assignment `IRIS-SIG-17`**.

---

## 📋 Table of Contents

- [Overview & Objective](#-overview--objective)
- [Architecture & Design](#-architecture--design)
- [Source Status & 410 Gone Analysis](#-source-status--410-gone-analysis)
- [Signal Classification Rules](#-signal-classification-rules)
- [Spatial Geometry & Coordinate Transformation](#-spatial-geometry--coordinate-transformation)
- [Database Schema & Idempotency](#-database-schema--idempotency)
- [Project Structure](#-project-structure)
- [Quick Start & Execution](#-quick-start--execution)
- [Automated Testing](#-automated-testing)
- [Validation & Quality Report](#-validation--quality-report)
- [Known Limitations & Assumptions](#-known-limitations--assumptions)

---

## 🎯 Overview & Objective

The objective of **IRIS-SIG-17** is to scan municipal zoning notices (*Bebauungspläne*) across Berlin to identify spatial and infrastructure signals critical to data center site evaluation:

1. **Urban Industrial Reconversions**: Identification of brownfields, industrial estates (*Industriegebiete/Gewerbegebiete*), and former commercial plots transitioning to new uses.
2. **High-Power Substation Alerts**: Notices mentioning electrical substations (*Umspannwerke*), high-voltage transmission lines (110kV/220kV/380kV), and grid expansion points.
3. **Edge Data Center Filings**: Explicit mentions of data centers (*Rechenzentren*), server farms, and high-megawatt IT load campus designations.

Extracted records are normalized, projected to **`EPSG:25832`**, and idempotently loaded into **`iris_staging.signal_ingest`** in PostgreSQL 16 / PostGIS 3.4.

---

## 🏗️ Architecture & Design

Following the reference architecture demonstrated in [`iris-sample`](https://github.com/amaurisantosjr/iris-sample):

```
┌─────────────────────────┐
│ Berlin B-Plan Notices   │ (HTML Web Pages / Fixtures)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ HttpClient              │ (Session, Retry with Backoff, Rate-limiting, 410 handling)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ BplanParser             │ (BeautifulSoup4 extraction of IDs, dates, titles, coords)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ SignalClassifier        │ (Filters residential noise; scores target signals)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ GeoResolver             │ (Validates bounds, transforms WGS84 -> EPSG:25832)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ SignalLoader            │ (Idempotent batch upsert into iris_staging.signal_ingest)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ PostgreSQL 16 + PostGIS │ (Stored with EPSG:25832 Point geometries and audit trails)
└─────────────────────────┘
```

---

## ⚠️ Source Status & 410 Gone Analysis

The endpoint specified in the task brief is `https://berlin.de/bebauungsplaene`.

### Investigation & Discovery
Direct HTTP inspection reveals that this URL returns **`HTTP 410 (Gone)`**, as the legacy static directory was deprecated by the Berlin IT administration.

Per the **Candidate Notes** in the task brief:
> *"If an endpoint, feed, or HTML selector in the brief is obsolete or inaccessible, document the issue and provide a tested fixture-based implementation and a justified alternative."*

### Resolution & Justified Alternative
1. **Documented & Trapped**: The harvester's `HttpClient` recognizes HTTP 410, logs an explanatory warning, and adds diagnostic notes to `metadata_json`.
2. **Offline Fixture Pipeline**: Included under `fixtures/` are representative HTML fixtures modeled after actual Berlin B-Plan notices.
3. **Justified Production Alternatives**:
   - **Geoportal Berlin / FIS-Broker**: The official spatial information broker (`https://gdi.berlin.de/viewer/bplan/`) providing WFS/WMS feeds.
   - **Senatsverwaltung für Stadtentwicklung**: Formal procedure overview under `https://www.berlin.de/sen/stadtentwicklung/planung/bebauungsplanverfahren/`.

---

## 🏷️ Signal Classification Rules

The `SignalClassifier` evaluates document headings and planning justifications against compiled German/English domain patterns:

| Signal Type | Indicators / Keywords | Example Matching Notice |
| :--- | :--- | :--- |
| `urban_industrial_reconversion` | *Konversion, Brachfläche, Industriegebiet, Gewerbegebiet, Wiedernutzbarmachung, Revitalisierung, Brownfield, GI/GE* | *I-B14a: Industrie- und Gewerbegebiet Moabit West Umstrukturierung* |
| `high_power_substation_alert` | *Umspannwerk, Transformator, Trafostation, 110kV, 220kV, 380kV, Hochspannung, Höchstspannung, Übertragungsnetz, Schaltanlage* | *SPA-88-UW: Errichtung 110kV/380kV Umspannwerk Haselhorst & Netzverstärkung* |
| `edge_dc_filing` | *Rechenzentrum, Datacenter, Data Center, Hyperscale, Edge Computing, Cloud-Infrastruktur, IT-Last, SO Datacenter* | *MZ-B202-DC: CleanTech Business Park - Neubau Hyperscale & Edge Rechenzentrum* |

*Noise Exclusion*: Notices describing pure residential developments (*Reines Wohngebiet*, *Kindertagesstätte*, *Spielplatz*) without energy or commercial components are automatically filtered out.

---

## 🗺️ Spatial Geometry & Coordinate Transformation

- **Metric Standard**: **`EPSG:25832`** (ETRS89 / UTM Zone 32N), standard for geospatial data across Germany and the IRIS intelligence platform.
- **Transformation Engine**: `pyproj.Transformer` transforms raw coordinates `(lon, lat)` into projected metric easting and northing.
- **Strict Validation**:
  - Validates that coordinates lie within the Berlin metropolitan bounding box (`52.2` - `52.8` N, `12.9` - `13.9` E).
  - Corrupt coordinate strings (e.g., `'CORRUPT_LAT'`) are rejected and marked with `location_status = 'invalid'` with detailed reason notes. Invalid coordinates are **never silently accepted**.

---

## 🗄️ Database Schema & Idempotency

### Table: `iris_staging.signal_ingest`

```sql
CREATE SCHEMA IF NOT EXISTS iris_staging;

CREATE TABLE iris_staging.signal_ingest (
    id VARCHAR(36) PRIMARY KEY,
    source_id VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    signal_type VARCHAR(64) NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    publication_date DATE,
    source_url TEXT NOT NULL,
    district VARCHAR(128),
    description TEXT,
    easting_25832 FLOAT,
    northing_25832 FLOAT,
    geometry_wkt TEXT,
    location_status VARCHAR(32) DEFAULT 'unresolved',
    geom geometry(Point, 25832),
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Idempotency Guarantee
The pipeline identifies records by their unique `source_id`.
- **First Run**: Inserts record into `iris_staging.signal_ingest`.
- **Subsequent Runs**: Performs an update on existing rows if modified, or skips unchanged records.
- **Batch Duplicates**: Deduplicates in-memory before committing. Re-running the harvester $N$ times will **never create duplicate records**.

---

## 📂 Project Structure

```
iris-berlin-harvester/
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore file
├── pyproject.toml                   # Project metadata & pytest configuration
├── requirements.txt                 # Pinned dependencies
├── docker-compose.yml               # PostgreSQL 16 + PostGIS 3.4 container
├── README.md                        # Project documentation (this file)
├── main.py                          # CLI runner entrypoint
├── app/
│   ├── config/                      # Settings & Path utilities
│   ├── scrapers/                    # BaseScraper, HttpClient, BerlinBplanScraper
│   ├── parsers/                     # HTML BeautifulSoup4 Parser
│   ├── filters/                     # SignalClassifier (domain keywords & noise filtering)
│   ├── spatial/                     # GeoResolver (WGS84 -> EPSG:25832 projection & validation)
│   ├── transformers/                # SignalTransformer (normalizes records & builds GeoJSON)
│   ├── database/                    # SQLAlchemy Base, Session, Models & Repositories
│   ├── loaders/                     # Idempotent SignalLoader
│   └── runners/                     # HarvestRunner orchestration
├── fixtures/                        # Representative Berlin B-Plan HTML fixtures
├── output/                          # Exported sample deliverables
│   ├── sample_signals.json          # Normalized JSON signal records
│   └── sample_signals.geojson       # WGS84 GeoJSON visualization features
├── validation/                      # SQL verification queries
│   └── validation.sql
├── docs/                            # In-depth Quality & Anomaly Report
│   └── data_quality_report.md
└── tests/                           # Comprehensive automated test suite
    ├── conftest.py
    ├── test_scraper.py
    ├── test_parser.py
    ├── test_classifier.py
    ├── test_geo_resolver.py
    ├── test_transformer.py
    └── test_loader_idempotency.py
```

---

## 🚀 Quick Start & Execution

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-submitted-repo-url>
cd iris-berlin-harvester

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```
*(No passwords or production keys are hardcoded in the codebase).*

### 3. Start PostgreSQL / PostGIS (Optional / Docker)

```bash
docker compose up -d
```

### 4. Run Harvester

```bash
# Run in default verified offline mode (generates JSON and GeoJSON outputs):
python main.py --mode offline --no-db

# Or run with database ingestion (requires PostgreSQL running):
python main.py --mode offline
```

---

## 🧪 Automated Testing

Run the automated test suite with `pytest`:

```bash
python -m pytest tests
```

Output:
```
tests/test_classifier.py::test_classify_industrial_reconversion PASSED
tests/test_classifier.py::test_classify_substation_alert PASSED
tests/test_classifier.py::test_classify_datacenter_filing PASSED
tests/test_classifier.py::test_filter_purely_residential PASSED
tests/test_geo_resolver.py::test_resolve_valid_berlin_coordinates PASSED
tests/test_geo_resolver.py::test_resolve_corrupt_coordinates_rejected PASSED
tests/test_geo_resolver.py::test_resolve_out_of_bounds_rejected PASSED
tests/test_geo_resolver.py::test_resolve_missing_coordinates PASSED
tests/test_loader_idempotency.py::test_loader_idempotency_and_no_duplicates PASSED
tests/test_parser.py::test_parse_portal_list PASSED
tests/test_parser.py::test_parse_detail_industrial PASSED
tests/test_parser.py::test_parse_detail_malformed PASSED
tests/test_scraper.py::test_scraper_loads_offline_fixtures PASSED
tests/test_scraper.py::test_scraper_handles_http_410_gone PASSED
tests/test_transformer.py::test_transformer_filters_and_normalizes PASSED
tests/test_transformer.py::test_geojson_export PASSED

============================= 16 passed in 0.49s ==============================
```

---

## 🔍 Validation & Quality Report

- **Validation SQL**: Execute [`validation/validation.sql`](validation/validation.sql) inside PostgreSQL to verify record counts, geometry projections, and absence of duplicates.
- **Detailed Quality Report**: Read [`docs/data_quality_report.md`](docs/data_quality_report.md) for full error analysis, coordinate bounding box verification, and data quality metrics.

---

## 📌 Known Limitations & Assumptions

1. **HTML Selector Sensitivity**: Scrapers targeting municipal HTML portals are sensitive to UI redesigns. For production usage, an automated monitor or migrating to the Geoportal Berlin WFS API is recommended.
2. **Text-based Geocoding**: When coordinates are absent from the notice body, addresses can be geocoded using the Berlin ALKIS parcel database or an internal address geocoder.
3. **Multi-polygon Boundaries**: This harvester extracts centroid/point geometries into `EPSG:25832`. In the future, full B-Plan boundary polygons can be joined from the Berlin GDI WFS service.

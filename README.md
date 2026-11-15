# Smart Highway Speed Radar & Ticket Generator

An enterprise-grade, academic automated speed enforcement radar and electronic citation system built with **FastAPI**, **Pandas**, **NumPy**, **OpenCV**, **Pillow**, and **Chart.js**.

The application models a roadside automated highway speed checkpoint that ingests NGSIM (Next Generation Simulation) vehicle trajectory telemetry, detects speeding violations using vectorized numerical operations, calculates fines, generates official high-resolution electronic citation documents (E-Tickets), and renders dynamic analytical dashboards.

---

## Table of Contents

- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture & Directory Structure](#architecture--directory-structure)
- [Object-Oriented Design & Mathematical Models](#object-oriented-design--mathematical-models)
  - [NGSIM Velocity Conversion](#ngsim-velocity-conversion)
  - [Vectorized Fine Computation](#vectorized-fine-computation)
  - [Academic Enforcement Checkpoint Assumption](#academic-enforcement-checkpoint-assumption)
- [Quickstart & Single-Command Launch](#quickstart--single-command-launch)
- [Data Ingestion Modes](#data-ingestion-modes)
  - [1. Offline Synthetic NGSIM Demo Generator](#1-offline-synthetic-ngsim-demo-generator)
  - [2. Local NGSIM CSV Import](#2-local-ngsim-csv-import)
  - [3. US DOT Socrata Open Data API](#3-us-dot-socrata-open-data-api)
- [REST API Reference](#rest-api-reference)
- [Computer Vision Citation Image Generator (OpenCV & PIL)](#computer-vision-citation-image-generator-opencv--pil)
- [JSON Database & Persistence Engine](#json-database--persistence-engine)
- [Testing & Quality Assurance](#testing--quality-assurance)

---

## Key Features

1. **Dark Navy Glassmorphic UI**: High-contrast, clean visual design with electric cyan, violation red, and compliance green accents.
2. **100% Dynamic Telemetry**: Zero mock numbers; all dashboard KPI cards, observation streams, charts, and ticket records are powered by real-time backend API endpoints.
3. **Vectorized Violation Detection**: Employs Pandas and NumPy arrays for high-throughput batch evaluation of vehicle velocities and penalties.
4. **Computer Vision E-Ticket Rendering**: Combines OpenCV for surveillance HUD graphics (perspective road lanes, target bounding reticles, radar crosshairs) with Pillow for high-definition typography, official seals, and barcodes.
5. **Thread-Safe Atomic JSON Persistence**: Implements atomic temporary-file replacement and read/write locking to prevent race conditions or data corruption.
6. **Multi-Modal Data Ingestion**:
   - Zero-dependency offline synthetic NGSIM trajectory generator.
   - Local CSV file upload with format verification.
   - Live integration with the US DOT Socrata Open Data endpoint (`https://data.transportation.gov/resource/8ect-6jqj.csv`).
7. **Comprehensive Interactive Analytics**: 4 responsive Chart.js visualizations (hourly violation trends, velocity histogram vs limit, vehicle class compliance, fine revenue distribution).

---

## Technology Stack

### Backend
- **Python 3.10+ / 3.13+ / 3.14+**
- **FastAPI**: Modern, high-performance web framework for building APIs.
- **Uvicorn**: Lightning-fast ASGI server.
- **Pandas**: Data manipulation, grouping, and trajectory filtering.
- **NumPy**: Vectorized mathematical fine calculations and histograms.
- **OpenCV (`opencv-python`)**: Computer vision HUD graphics, reticles, and image transformation.
- **Pillow (`PIL`)**: High-res typography, structured citation tables, digital seals, and barcodes.
- **Pydantic v2**: Request/response schema validation and type safety.
- **Requests**: External HTTP ingestion for government open data.

### Frontend
- **HTML5 & Modern CSS3**: Custom dark navy glassmorphic layout (no Bootstrap bloat).
- **Vanilla JavaScript (ES6+)**: Modular MVC architecture without heavy frameworks.
- **Chart.js**: Dynamic interactive data visualizations.
- **Inline SVG Icons**: Crisp Lucide-equivalent vector icons with zero external font dependencies.

### Persistent Storage
- **JSON Flat-File Database**: `vehicles.json`, `violations.json`, `tickets.json`, `settings.json`, and `processing_state.json`.

---

## Architecture & Directory Structure

```
smart_highway/
│
├── main.py                     # FastAPI application entry point & REST route controllers
├── config.py                   # Centralized configuration, filesystem paths, & defaults
├── requirements.txt            # Python package dependencies
├── test_integration.py         # Automated end-to-end integration test suite
│
├── backend/
│   ├── __init__.py
│   ├── models.py               # Pydantic schemas for request/response validation
│   ├── vehicle.py              # Object-Oriented Vehicle entity
│   ├── radar.py                # RadarSystem class & vectorized fine computation
│   ├── data_manager.py         # DataManager orchestration engine
│   ├── dataset_adapter.py      # NGSIM data normalization, CSV & Socrata API adapter
│   ├── ticket_generator.py     # OpenCV + Pillow citation image generator
│   ├── analytics.py            # Pandas/NumPy analytics and distribution engine
│   └── storage.py              # Atomic, thread-safe JSON persistence layer
│
├── database/
│   ├── vehicles.json           # Persisted vehicle observation records
│   ├── violations.json         # Detected speeding infractions
│   ├── tickets.json            # Electronic citation metadata
│   ├── settings.json           # Enforcement thresholds and camera parameters
│   └── processing_state.json   # Radar scanner runtime state
│
├── frontend/
│   ├── index.html              # Single-page dashboard application
│   ├── css/
│   │   └── style.css           # Custom dark navy & electric cyan stylesheet
│   └── js/
│       ├── app.js              # Router, API client, toast alerts, & modal controllers
│       ├── dashboard.js        # Dashboard KPIs, recent violations, & Chart.js instances
│       ├── radar.js            # Radar monitoring, sweep HUD, & observation feed
│       ├── vehicles.js         # Searchable, filterable, paginated vehicles table
│       ├── tickets.js          # E-Ticket gallery, image viewer, & JSON exporter
│       └── analytics.js        # Deep analytics charts & vehicle category breakdown
│
├── sample_data/
│   └── sample_ngsim.csv        # Bundled sample NGSIM trajectory dataset
│
├── generated_tickets/          # Directory storing generated citation PNG images
│   └── TKT-2026-*.png
│
└── README.md
```

---

## Object-Oriented Design & Mathematical Models

### NGSIM Velocity Conversion
NGSIM datasets record instantaneous velocity (`v_Vel`) in **feet per second (ft/s)**. To convert native trajectory velocity into standard statutory enforcement units (**km/h**):

$$\text{speed}_{\text{km/h}} = v_{\text{Vel}} \times 1.09728$$

Derived from:
$$1\text{ ft} = 0.3048\text{ m} \implies 1\text{ ft/s} = 0.3048 \times 3.6\text{ km/h} = 1.09728\text{ km/h}$$

### Vectorized Fine Computation
Speeding fines are computed using high-performance NumPy vectorization. For vehicles exceeding the posted speed limit:

$$\text{excess} = \max(0.0, \text{speed} - \text{speed\_limit})$$

$$\text{fine} = \begin{cases} 
\text{base\_fine} + (\text{excess} \times \text{fine\_per\_kmh}) & \text{if } \text{speed} > \text{speed\_limit} \\
0.0 & \text{otherwise}
\end{cases}$$

Example with standard defaults ($\text{speed\_limit} = 80.0\text{ km/h}$, $\text{base\_fine} = \$500.00$, $\text{fine\_per\_kmh} = \$50.00$):
- Vehicle speed: $105.5\text{ km/h}$
- Excess speed: $25.5\text{ km/h}$
- Fine: $\$500.00 + (25.5 \times \$50.00) = \$1,775.00$

### Academic Enforcement Checkpoint Assumption
In raw NGSIM trajectory recordings, an individual vehicle is tracked at sub-second intervals (typically 10 Hz), yielding dozens or hundreds of successive observation frames.

> **Enforcement Assumption**:
> In accordance with academic radar checkpoint simulation principles and to prevent double-jeopardy citation spamming, the radar checkpoint groups observations by `Vehicle_ID` and issues at most **one citation per vehicle per processing session**, based on its **maximum recorded speed** during that pass.

---

## Quickstart & Single-Command Launch

### 1. Prerequisites
- Python 3.10 or higher.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Application (Single Command)
Run the application using Python:
```bash
python main.py
```
Or directly with Uvicorn:
```bash
uvicorn main.py:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Access the Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
Interactive Swagger API documentation is available at:
```
http://127.0.0.1:8000/docs
```

---

## Data Ingestion Modes

The system provides three data sources configured under the **Data Sources** tab:

### 1. Offline Synthetic NGSIM Demo Generator
- **Zero external dependencies**: Works 100% offline without network connectivity or file downloads.
- Generates 120 vehicles across 3 NGSIM classifications (Sedans, Motorcycles, Heavy Trucks) with multi-frame velocity tracking and realistic speed variations.

### 2. Local NGSIM CSV Import
- Import custom NGSIM CSV trajectory files using the web interface or load the bundled sample dataset located at `sample_data/sample_ngsim.csv`.
- Robust column normalization handles case-insensitive naming (`Vehicle_ID`, `v_Vel`, `Global_Time`, `Local_X`, `Local_Y`).

### 3. US DOT Socrata Open Data API
- Verified endpoint: `https://data.transportation.gov/resource/8ect-6jqj.csv`
- Ingests real-world transportation open data with clean exception diagnostics if the remote government service is unreachable.

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend service health and status |
| `GET` | `/api/dashboard` | Dashboard KPI summary statistics |
| `GET` | `/api/vehicles` | Paginated, filtered, and searchable vehicle records |
| `GET` | `/api/violations` | Speeding violation infractions |
| `GET` | `/api/tickets` | Generated citation records |
| `GET` | `/api/tickets/{ticket_id}` | Detailed citation record |
| `GET` | `/api/tickets/{ticket_id}/image` | Secure download/stream of generated citation PNG |
| `POST` | `/api/tickets/generate` | Generate official e-tickets for violations |
| `POST` | `/api/radar/start` | Start radar vehicle scanning and violation detection |
| `POST` | `/api/radar/stop` | Halt active radar simulation |
| `GET` | `/api/radar/status` | Query current scanner status |
| `POST` | `/api/dataset/upload` | Upload a custom NGSIM CSV trajectory file |
| `POST` | `/api/dataset/process` | Trigger processing for a specific data source |
| `GET` | `/api/analytics/hourly` | 24-hour violation distribution |
| `GET` | `/api/analytics/distribution`| Velocity histogram binned in 10 km/h increments |
| `GET` | `/api/analytics/categories` | Classification compliance breakdown (Sedan, Truck, Motorcycle) |
| `GET` | `/api/analytics/fines` | Fine amounts grouped by penalty brackets |
| `GET` | `/api/settings` | Retrieve active radar parameters |
| `PUT` | `/api/settings` | Update radar limits, fines, and location |
| `POST` | `/api/database/reset` | Reset dynamic database records after explicit confirmation |

---

## Computer Vision Citation Image Generator (OpenCV & PIL)

Each speeding citation is rendered into an official, high-resolution PNG document stored in `generated_tickets/`:

1. **Surveillance HUD Reticle (OpenCV)**:
   - Perspective highway lanes with shoulder markers.
   - Vehicle silhouette sized according to NGSIM vehicle class.
   - Radar HUD targeting box with corner reticles and crosshair marker.
   - High-contrast electric cyan / red HUD velocity tags.
   - **Mandatory Academic Notice Watermark**: `ILLUSTRATIVE EVIDENCE - NGSIM ACADEMIC SIMULATION` prominently embedded on the evidence frame.
2. **Citation Document Typography & Assembly (Pillow)**:
   - Official Department of Transportation / Highway Patrol header.
   - Digital circular verification seal emblem.
   - Structured telemetry breakdown table (Vehicle ID, Class, Recorded Speed, Permitted Limit, Excess, Base Penalty, Excess Surcharge).
   - Prominent red total fine card (`$X,XXX.XX`).
   - Barcode graphic encoding ticket and vehicle identification.
   - Digital cryptographic officer signature stamp.

---

## JSON Database & Persistence Engine

### Atomic Write Protocol
To prevent corrupted JSON files caused by sudden process termination:
1. Data is written to a temporary file (`{stem}_tmp_{rand}.json`) within the same directory.
2. The file is flushed to disk and synced using `os.fsync()`.
3. The temporary file replaces the target file atomically via `os.replace()`.

### Thread-Safe File Locking
All disk reads and writes are protected by a re-entrant thread lock (`threading.RLock()`), preventing simultaneous thread collisions.

### Limitations for Production Workloads
JSON flat-file persistence is ideal for educational demonstrations, small-scale deployments, and isolated testing. For high-concurrency production workloads with thousands of simultaneous writes:
- Lack of row-level locking (the entire file is read and written).
- Process-level locking does not serialize separate operating system processes.
- For high-scale production, migration to PostgreSQL with PostGIS or a time-series database is recommended.

---

## Testing & Quality Assurance

Run the comprehensive integration test suite:

```bash
python test_integration.py
```

### Test Suite Coverage
- `GET /api/health` connectivity.
- Database clean reset.
- Dynamic settings updates.
- Radar scan execution and vehicle counts.
- Mathematical accuracy of vectorized fine calculations.
- Vehicle pagination, search, and status filtering.
- OpenCV/PIL ticket generation and PNG byte verification.
- Duplicate ticket prevention.
- Path traversal attack protection (`/api/tickets/../../config/image`).
- Analytical distribution endpoints.
- CSV upload and validation.
- Single-page frontend delivery.

---

## License & Academic Disclaimer

Developed as an academic demonstration of Object-Oriented Programming (OOP), Data Science with Pandas/NumPy, Computer Vision with OpenCV/PIL, and Web Engineering with FastAPI.

Vehicle trajectories are modeled on the Next Generation Simulation (NGSIM) program datasets collected by the Federal Highway Administration (FHWA). Photographic evidence is illustrative and computer-generated for simulation purposes.

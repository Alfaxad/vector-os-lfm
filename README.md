# VectorOS LFM

<p align="left">
  <a href="https://huggingface.co/Alfaxad/Vector-LFM2.5-VL-450M"><img alt="Hugging Face model: Alfaxad/Vector-LFM2.5-VL-450M" src="https://img.shields.io/badge/%F0%9F%A4%97%20Model-Vector--LFM2.5--VL--450M-FFD21E?style=for-the-badge&labelColor=222326" /></a>
  <a href="https://huggingface.co/datasets/Alfaxad/vector-100k"><img alt="Hugging Face dataset: Alfaxad/vector-100k" src="https://img.shields.io/badge/%F0%9F%A4%97%20Dataset-vector--100k-FFD21E?style=for-the-badge&labelColor=222326" /></a>
  <a href="vector-lfm25vl-tech-report.pdf"><img alt="Technical report PDF" src="https://img.shields.io/badge/Technical%20Report-PDF-F4F5F8?style=for-the-badge&labelColor=222326" /></a>
</p>

**VectorOS LFM** is an open geospatial epidemiology demo for population-level
surveillance reasoning. It combines satellite imagery, map context, climate,
surface water, land cover, population exposure, OpenStreetMap features, and weak
vector/disease labels, then grounds live vision-language model responses with
selected-chip citations.

The demo runs locally with Django, React, Leaflet, and
[`Alfaxad/Vector-LFM2.5-VL-450M`](https://huggingface.co/Alfaxad/Vector-LFM2.5-VL-450M),
a fine-tuned LiquidAI LFM2.5-VL-450M model for geospatial epidemiology tasks.

![VectorOS app screenshot](docs/assets/vectoros-app-screenshot.png)

## Problem

Vector-borne and water-associated disease surveillance often depends on
fragmented signals:

- satellite imagery showing water, vegetation, urban texture, or shoreline context;
- rainfall and surface-water products;
- population and settlement exposure;
- OpenStreetMap facilities, schools, roads, waterways, and land-use features;
- presence-biased GBIF, MAP, or OpenDengue records;
- local review by public-health or field teams.

These signals are useful together, but they are difficult to inspect quickly.
They also carry uncertainty: weak labels are not field-confirmed transmission,
satellite rasters can be cloudy or missing, and an AOI-wide source may not apply
to the selected map chip.

VectorOS frames this as **geospatial epidemiology**: grounded, population-level
reasoning over environmental and exposure evidence. The app is not a clinical
tool. It does not diagnose individuals, confirm transmission, prescribe
treatment, or replace field validation.

## What This Repo Contains

- A Django backend serving the VectorOS API and local live inference worker.
- A React/Vite frontend with an interactive Leaflet AOI map.
- A compact demo dataset under `data/processed/vector-100k-demo`.
- SimSat Sentinel-2 and Mapbox image crops for the bundled demo chips.
- Compact per-chip OSM and weak-label context patches for hoverable map
  analysis.
- Model training/evaluation metadata under `artifacts/vector-lfm2.5-vl`.
- Technical report: [vector-lfm25vl-tech-report.pdf](vector-lfm25vl-tech-report.pdf).
- Product specification: [docs/VectorOS_product_spec.md](docs/VectorOS_product_spec.md).

The full training dataset and model weights are hosted on Hugging Face:

- Dataset: [Alfaxad/vector-100k](https://huggingface.co/datasets/Alfaxad/vector-100k)
- Model: [Alfaxad/Vector-LFM2.5-VL-450M](https://huggingface.co/Alfaxad/Vector-LFM2.5-VL-450M)

## Demo Data

The bundled dataset is a compact runtime subset derived from
`Alfaxad/vector-100k`. It is designed to make the app usable from a fresh clone
without committing the full 100k training package or raw raster mirrors.

| Item | Count |
| --- | ---: |
| AOIs | 30 |
| Evidence chips | 90 |
| SFT records | 900 |
| Task templates | 10 |
| Context patch files | 90 |
| OSM / weak-label patch features | 34,437 |

Module coverage:

| Module | Demo chips |
| --- | ---: |
| Aedes / dengue | 30 |
| Anopheles / malaria | 30 |
| Schistosomiasis | 30 |

Risk-class coverage:

| Risk class | Demo chips |
| --- | ---: |
| Very high | 2 |
| High | 18 |
| Moderate | 15 |
| Low | 55 |

Sample four-panel image packet:

![VectorOS sample image packet](docs/assets/vectoros-sample-image-packet.png)

Each image packet follows this layout:

- top-left: SimSat Sentinel-2 true-color RGB;
- top-right: SimSat Sentinel-2 NIR false color;
- bottom-left: Mapbox satellite context;
- bottom-right: aligned evidence overlay from environmental, population, OSM,
  and weak-label layers.

## Data Collection And Sources

The full `vector-100k` dataset was built by selecting 30 AOIs across the three
supported disease modules and generating geospatial chips with aligned imagery,
environmental context, exposure statistics, and weak labels.

| Source | Role in VectorOS | Runtime use |
| --- | --- | --- |
| SimSat Sentinel-2 | Multispectral Sentinel-2 imagery, RGB, false color, source metadata | Bundled cached crops; optional live SimSat connector |
| SimSat Mapbox satellite | High-resolution visual map context | Bundled cached crops; optional live SimSat connector |
| CHIRPS | Rainfall statistics and lag context | Bundled sidecar numeric features |
| JRC Global Surface Water | Water occurrence and seasonality context | Bundled sidecar numeric features |
| ESA WorldCover | 10 m land-cover context | Bundled sidecar numeric features and evidence overlays |
| WorldPop | Population and exposure context | Bundled sidecar numeric features |
| OpenStreetMap / Overpass | Roads, waterways, urban land-use, schools, waterpoints, facilities | Bundled compact per-chip context patches |
| Healthsites.io | Health facility reference layer | Optional server-side live lookup when key is configured |
| GBIF | Vector and intermediate-host occurrence labels | Bundled weak-label counts and context patches |
| OpenDengue / MAP | Disease/vector-context weak labels depending on module and AOI | Bundled weak-label counts and context patches |

### SimSat Integration

VectorOS uses SimSat as the imagery provider abstraction for the demo chips.
The app records SimSat source metadata in each sidecar and exposes connector
status through the API.

SimSat endpoints expected by the connector layer:

| SimSat API | Purpose |
| --- | --- |
| `GET {SIMSAT_API_BASE_URL}/data/image/sentinel` | Sentinel-2 imagery retrieval |
| `GET {SIMSAT_API_BASE_URL}/data/image/mapbox` | Mapbox satellite context retrieval |

For the bundled open-source demo, these images are already cached in
`data/processed/vector-100k-demo/simsat_raw/...`. A live SimSat instance is not
required to launch the app.

## Grounding And Responses

The app performs live inference with
`Alfaxad/Vector-LFM2.5-VL-450M`, but user-facing responses are grounded against
verified selected-chip facts:

- risk score, risk class, confidence, and uncertainty interval;
- CHIRPS rainfall values;
- JRC water status and valid-pixel count;
- OSM water and exposure counts;
- WorldPop population signal;
- module-specific weak-label counts;
- scope notes that distinguish selected-chip truth from AOI-wide truth.

If the raw model draft drifts from the verified facts, the UI shows an
evidence-aligned answer and keeps the citations visible. This preserves live
model inference while preventing numeric hallucinations in the demo.

## Model And Evaluation

Base model:
[`LiquidAI/LFM2.5-VL-450M`](https://huggingface.co/LiquidAI/LFM2.5-VL-450M)

Fine-tuned model:
[`Alfaxad/Vector-LFM2.5-VL-450M`](https://huggingface.co/Alfaxad/Vector-LFM2.5-VL-450M)

Full dataset:
[`Alfaxad/vector-100k`](https://huggingface.co/datasets/Alfaxad/vector-100k)

Technical report:
[vector-lfm25vl-tech-report.pdf](vector-lfm25vl-tech-report.pdf)

The fixed evaluation artifact is stored at
`artifacts/vector-lfm2.5-vl/eval_comparison_fixed.json`.

| Metric | Base LFM2.5-VL-450M | Vector-LFM2.5-VL-450M | Delta |
| --- | ---: | ---: | ---: |
| Validation loss | 2.2434 | 0.0826 | -2.1608 |
| Validation perplexity | 9.4255 | 1.0861 | -8.3394 |
| Test loss | 2.2448 | 0.0913 | -2.1535 |
| Test perplexity | 9.4383 | 1.0956 | -8.3428 |
| Median sequence similarity | 0.1344 | 0.9984 | +0.8640 |
| Normalized exact match | 0.0000 | 0.4733 | +0.4733 |
| Risk-class accuracy | 0.0000 | 0.4333 | +0.4333 |
| JSON parse rate | 0.9933 | 1.0000 | +0.0067 |
| Source-grounding recall | 0.5652 | 1.0000 | +0.4348 |
| Safety violation rate | 0.0000 | 0.0000 | 0.0000 |

These metrics compare the base model and merged fine-tuned model on held-out
VectorOS test records and structured generation tasks.

## Architecture

```text
vector-os-lfm/
├── manage.py
├── sat_dashboard/              # Django project settings and routing
├── simulation/                 # VectorOS API, data loading, inference worker
├── frontend/                   # React + Vite + Leaflet frontend
├── data/processed/vector-100k-demo/
│   ├── chip_index.json
│   ├── image_packets/
│   ├── sidecars/
│   ├── targets/
│   ├── simsat_raw/
│   └── context_patches/
├── artifacts/vector-lfm2.5-vl/ # Training/evaluation metadata
├── docs/assets/                # README screenshots
└── vector-lfm25vl-tech-report.pdf
```

Backend responsibilities:

- serve the React app;
- expose AOI, chip, map-layer, image, and connector APIs;
- load compact data manifests and per-chip context patches;
- run local live Transformers inference;
- attach verified citations to generated answers.

Frontend responsibilities:

- select modules and AOIs;
- render Mapbox/SimSat image overlays in Leaflet;
- display OSM/weak-label/risk context patches with hover cards;
- show image packets and selected-chip evidence;
- submit prompt suggestions to live inference.

## API Surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/vectoros/summary/` | Product, dataset, connector, and inference summary |
| `GET /api/vectoros/aois/` | List AOIs, optionally filtered by module |
| `GET /api/vectoros/risk-tiles/` | List selected evidence chips |
| `GET /api/vectoros/risk-tiles/<chip_id>/` | Full target, sidecar, report, and evidence cards for one chip |
| `GET /api/vectoros/map-layers/` | Leaflet-ready AOI overlays and context patches |
| `GET /api/vectoros/images/<path>` | Serve bundled image packets and SimSat raw crops |
| `GET /api/vectoros/inference/status/` | Local model runtime status |
| `POST /api/vectoros/infer/` | Live VLM inference with grounded citations |
| `POST /api/vectoros/copilot/` | Lightweight non-model fallback report summary |
| `GET /api/vectoros/healthsites/` | Optional live Healthsites lookup by bbox |

## Installation

Prerequisites:

- Python 3.10 or newer;
- Node.js 20 or newer;
- enough disk space for the bundled demo data and model cache;
- optional CUDA or Apple Silicon MPS for faster local inference.

Clone the repo:

```bash
git clone https://github.com/Alfaxad/vector-os-lfm.git
cd vector-os-lfm
```

Create environment:

```bash
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install and build the frontend:

```bash
cd frontend
npm ci
npm run build
cd ..
```

Initialize Django:

```bash
python manage.py migrate
```

## Starting The App

### Option A: Single Django Server

This is the simplest way to run the demo. Django serves both the API and the
built React app.

Terminal 1:

```bash
python manage.py runserver 127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000
```

### Option B: Two Servers For Frontend Development

Use this while editing React, CSS, or map interactions. Django serves the API,
and Vite serves the frontend with hot reload. The Vite dev server proxies
`/api/...` requests to Django.

Terminal 1, from the repo root:

```bash
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

Terminal 2:

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173
```

The first live inference request downloads
`Alfaxad/Vector-LFM2.5-VL-450M` from Hugging Face if it is not already cached.
The worker chooses CUDA when available, then Apple MPS, then CPU.

### Optional Live Data Servers

The bundled demo does not require external data servers because the compact
SimSat image crops, sidecars, and context patches are already checked in.

Optional live connectors can be enabled through `.env`:

- `SIMSAT_API_BASE_URL`: points to a running SimSat service. VectorOS expects
  Sentinel-2 at `/data/image/sentinel` and Mapbox imagery at `/data/image/mapbox`.
  If unset or unavailable, the app uses the bundled cached crops.
- `MAPBOX_ACCESS_TOKEN`: optional server-side token for live Mapbox-backed
  SimSat imagery. Do not expose this token in browser code.
- `HEALTHSITES_API_KEY`: optional server-side key for live Healthsites lookup.

After changing `.env`, restart the Django server.

## Configuration

The included demo dataset is used by default. To run against the full dataset,
download [Alfaxad/vector-100k](https://huggingface.co/datasets/Alfaxad/vector-100k)
and set `VECTOROS_DATASET_ROOT`.

```bash
python scripts/download_full_dataset.py --target data/processed/vector-100k
```

Example `.env`:

```bash
DJANGO_SECRET_KEY=dev-secret-key-change-me
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

VECTOROS_MODEL_ID=Alfaxad/Vector-LFM2.5-VL-450M
VECTOROS_DATASET_ROOT=
SIMSAT_API_BASE_URL=http://localhost:9005

# Optional server-side connectors. Do not expose these in the browser.
MAPBOX_ACCESS_TOKEN=
HEALTHSITES_API_KEY=
```

Notes:

- Leave `VECTOROS_DATASET_ROOT` blank to use the bundled demo data.
- `MAPBOX_ACCESS_TOKEN` is optional for the bundled demo because image crops are
  already cached.
- `HEALTHSITES_API_KEY` is optional and only affects live health-facility lookup.
- Do not commit `.env` or real API tokens.

## Development Workflow

Rebuild frontend after editing React/CSS:

```bash
cd frontend
npm run build
cd ..
```

Run backend checks:

```bash
python manage.py check
```

Regenerate the compact demo subset from a local full dataset:

```bash
python scripts/build_demo_dataset.py \
  --source ../data/processed/vector-100k \
  --target data/processed/vector-100k-demo \
  --per-aoi 3
```

The demo builder copies image packets, sidecars, risk targets, SimSat raw
Sentinel/Mapbox crops, and compact per-chip context patches. It does not copy
the full raw AOI raster mirrors.

## Safety Scope

VectorOS is for population-level surveillance support only.

It should not be used to:

- diagnose individuals;
- confirm local disease transmission;
- infer infection status;
- prescribe treatment;
- replace local public-health review or field validation.

Weak labels from GBIF, OpenDengue, and MAP are presence-biased surveillance
context. They are useful for prioritization and model adaptation, but they are
not calibrated epidemiological ground truth.

## License

This repository inherits the included AGPL-3.0 license.

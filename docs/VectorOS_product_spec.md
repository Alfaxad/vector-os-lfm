# VectorOS: Product, Data, Fine-Tuning, and Platform Specification

**Version:** 1.0  
**Date:** 2026-05-04  
**Primary language:** English  
**Primary model path:** `LiquidAI/LFM2.5-VL-450M` plus calibrated geospatial risk models  
**Product thesis:** A vector, habitat, reservoir, hydrology, and climate-sensitive disease intelligence platform for public-health teams.

---

## 1. Executive Summary

VectorOS is a geospatial public-health intelligence platform that converts Earth-observation imagery, climate signals, hydrology, terrain, soils, population exposure, health surveillance, entomology, host/reservoir observations, field validation, and operational response data into actionable disease-risk maps and health-officer-grade reports.

The first flagship module should be **mosquito habitat and mosquito-borne disease surveillance**: malaria, dengue, chikungunya, Zika, yellow fever, Japanese encephalitis, West Nile fever, Rift Valley fever, and other mosquito-linked threats. The second flagship should be **schistosomiasis**, because its transmission depends on freshwater habitat, freshwater snails, aquatic vegetation, and human water contact, all of which are more directly observable from satellite, hydrology, field, and population layers than many other neglected tropical diseases.

The product should then expand into modules for **onchocerciasis**, **tsetse-borne human African trypanosomiasis**, **leishmaniasis**, and **tick/livestock-associated disease risk**, especially Crimean-Congo haemorrhagic fever. Each module shares the same platform substrate but uses a different ecological model: standing-water habitat for mosquitoes, snail/water-contact habitat for schistosomiasis, river-corridor blackfly habitat for onchocerciasis, vegetation-and-landscape niche mapping for tsetse and sandflies, and rangeland/livestock/tick suitability modeling for CCHF.

The model fine-tuning strategy should treat `LiquidAI/LFM2.5-VL-450M` as a **structured visual intelligence layer**, not as the sole epidemiological model. The VLM should learn to interpret satellite chips, multi-index panels, annotated overlays, and geospatial context, then produce strict JSON outputs and concise English reports. A separate calibrated risk stack should combine the VLM outputs with spatiotemporal statistical models, ecological niche models, anomaly detection, and health-surveillance time series. This separation makes VectorOS safer, more explainable, and more reliable: the VLM explains and structures evidence; the risk models calibrate probabilities and uncertainty.

The product interface should be “Palantir-like” in the useful sense: **ontology-centered, map-native, audit-heavy, workflow-oriented, and operationally elegant**. It should not be just a dashboard. It should be an investigation workspace where a health officer can ask, “Why is this district high-risk this week?”, inspect the data lineage, compare rainfall lags, see persistent water bodies and new floodwater, view population and facility exposure, generate a district report, assign field-validation tasks, and export an intervention brief.

### Safety scope

VectorOS is designed for public-health surveillance, environmental risk mapping, field validation, and operational planning. It is not a diagnostic tool for individual patients, not a clinical treatment engine, and not a platform for pathogen handling, culture, genetic modification, or laboratory protocols. All health data should be aggregated, de-identified, access-controlled, and used under ministry, institutional, and community governance.

---

## 2. Hackathon Fit and Strategic Product Positioning

The Liquid AI x DPhi Space hackathon brief emphasizes satellite intelligence, DPhi API imagery, Liquid Track use of LFM2-VL/LFM2.5-VL, and fine-tuning on domain-specific satellite data. The judging criteria include use of satellite imagery from the DPhi API, innovation/problem-solution fit, a working implementation, and an end-to-end demo. DPhi/SimSat provides access to Sentinel-2 and Mapbox imagery, with Sentinel-2 positioned as the temporally useful multispectral layer and Mapbox as the high-spatial-resolution visual context layer. The uploaded hackathon brief also notes that Sentinel-2 historical data and Mapbox data can be used for fine-tuning, and current/latest endpoints can be used for inference. [1]

Liquid AI describes LFM2.5-VL-450M as a compact 450M-parameter vision-language model for structured visual intelligence, low-latency inference, edge-to-cloud deployment, grounding, improved instruction following, and function calling. Liquid’s documentation lists a 32K context length and edge-ready deployment profile; the Hugging Face model card describes bounding-box prediction/object-detection-style grounding, multilingual vision understanding, and function-calling support. [2–4]

VectorOS is therefore an unusually good Liquid Track project because it can demonstrate:

- **DPhi API imagery use**: Sentinel-2 and Mapbox are central to the product, not decoration.
- **Domain-specific VLM fine-tuning**: the model learns disease-specific geospatial visual interpretation.
- **Structured outputs**: the VLM emits JSON objects that power the product UI and API.
- **Edge/onboard relevance**: the platform can run low-bandwidth pre-screening onboard or near the sensor, sending only risk metadata and cropped evidence patches.
- **Public-health stakes**: vector-borne diseases cause major preventable burden, especially in tropical and subtropical regions. WHO states that vector-borne diseases account for more than 17% of all infectious diseases and cause more than 700,000 deaths annually. [5]

---

## 3. Product Definition

### 3.1 What VectorOS is

VectorOS is a disease-surveillance operating system for climate-sensitive, vector-borne, reservoir-linked, and water-associated disease risk.

It unifies five capabilities:

1. **Geospatial habitat intelligence**: detect and characterize environmental conditions that support vectors, intermediate hosts, reservoirs, or human exposure.
2. **Epidemiological signal fusion**: combine official case counts, entomological observations, citizen-science signals, field surveys, and historical prevalence data.
3. **Exposure mapping**: estimate people, facilities, schools, livestock, water-contact sites, settlements, and logistics infrastructure exposed to risk.
4. **Operational tasking**: turn risk maps into field inspections, larval-source-management reviews, water-contact-site checks, vector trapping priorities, livestock/tick monitoring priorities, and local reports.
5. **Copilot intelligence**: provide natural-language English answers grounded in data layers, model outputs, provenance, and uncertainty.

### 3.2 What VectorOS is not

VectorOS is not a replacement for ministries of health, clinicians, epidemiologists, entomologists, malacologists, veterinarians, or field teams. It is not a patient-level diagnostic product. It should not provide medical treatment instructions. It should not suggest pathogen manipulation, vector breeding, or laboratory workflows. Its output should be framed as environmental and surveillance intelligence, not definitive disease causation.

### 3.3 The core user promise

A public-health officer should be able to open VectorOS and immediately answer:

- Where are the highest-risk areas this week?
- What changed since last week?
- What evidence supports the model’s risk judgment?
- Which villages, schools, facilities, water-contact sites, and livestock corridors are exposed?
- Which field checks should be prioritized?
- What official, citation-ready English report can I send to a district health team?
- Which model outputs are uncertain and need validation?

---

## 4. Disease Module Roadmap

VectorOS should be modular. Each disease module should define disease targets, vector/intermediate-host/reservoir ecology, Earth-observation signals, climate and hydrology signals, exposure signals, label sources, risk outputs, and recommended public-health workflows.

### 4.1 Module overview

| Module | Primary diseases | Vector / host / exposure ecology | Core EO signal | Best first output |
|---|---|---|---|---|
| **Mosquito Habitat OS** | Malaria, dengue, chikungunya, Zika, yellow fever, Japanese encephalitis, West Nile fever, Rift Valley fever | Anopheles, Aedes, Culex mosquitoes; standing water; containers; irrigation; vegetated aquatic fringes; settlement proximity | NDWI/MNDWI, NDMI, red-edge/NDVI, Sentinel-1 flood/wetness, rainfall lags, temperature/humidity, settlement texture | Weekly habitat suitability and exposed-population risk tiles |
| **Schisto OS** | Schistosomiasis | Freshwater snails, aquatic vegetation, slow/stagnant freshwater, human water contact | water seasonality, aquatic vegetation, shoreline/contact sites, hydrology, settlement/school proximity | Snail-habitat and water-contact risk atlas |
| **River Vector OS** | Onchocerciasis | Blackflies breeding in fast-flowing rivers and streams; adult dispersal corridors | HydroRIVERS, slope, flow accumulation, river morphology, rapids proxies, vegetation edges | River-corridor monitoring priority map |
| **Tsetse OS** | Human African trypanosomiasis, animal African trypanosomiasis | Tsetse habitat linked to vegetation, humidity, temperature, landscape configuration, livestock/wildlife interface | land cover, vegetation phenology, LST, humidity, riverine vegetation, livestock/wildlife proxies | Tsetse ecological suitability and trap-priority map |
| **Sandfly OS** | Leishmaniasis | Sandfly habitat, peri-domestic ecotones, poor housing, land disturbance, animal/reservoir proximity | land cover, built-up texture, vegetation edges, deforestation/disturbance, temperature/moisture | Settlement/ecotone risk and surveillance-priority map |
| **Tick & Livestock OS** | CCHF and other tick/livestock-linked risks | Tick habitat, rangelands, livestock density/movement, temperature/humidity, seasonality | NDVI phenology, rangeland moisture, temperature, livestock density, market/slaughterhouse proximity | Livestock-worker and rangeland risk dashboard |
| **Water & Climate OS** | Cholera, leptospirosis, flood-linked diarrheal outbreaks, harmful algal bloom risk | Flooding, poor water/sanitation exposure, surface water anomalies, coastal/water quality indicators | flood extent, precipitation anomalies, surface temperature, water persistence, population exposure | Environmental early-warning add-on |

### 4.2 Mosquito module: first flagship

The mosquito module should support Anopheles, Aedes, and Culex reasoning without collapsing them into a single “mosquito” label.

**Anopheles / malaria** needs village-scale standing-water suitability, vegetation fringes, irrigation, puddling, wet soils, rainfall lag, temperature, humidity, and human proximity. The best operational target is not “malaria cases tomorrow”; it is “habitat suitability and field-check priority under known rainfall and exposure conditions.” WHO’s 2024 malaria fact sheet estimates 263 million malaria cases and 597,000 malaria deaths in 2023, with the African Region carrying the overwhelming burden. [6]

**Aedes / dengue, chikungunya, Zika, yellow fever** requires a different ecology: urban and peri-urban containers, settlement texture, vegetation, micro-water accumulation, rainfall lags, and human density. The satellite signal is less direct at 10 m, so VectorOS should use Mapbox-like high-resolution imagery where available, OSM building density, GHSL built-up structure, rainfall/temperature, and open case data such as OpenDengue and PAHO regional reporting. WHO’s 2025 dengue fact sheet states that about half the world’s population is now at risk of dengue, with an estimated 100–400 million infections each year and a historic 2024 global spike in reported cases. [7]

**Culex / West Nile and Japanese encephalitis** needs wetlands, rice paddies, livestock/bird interface proxies, irrigation, and seasonal water. This module can share much of the Anopheles stack but should add livestock, agriculture, wetland, and migratory-bird/wetland context where appropriate.

**Rift Valley fever** is a strong expansion inside the mosquito module because it is climate-sensitive and livestock-associated. It benefits from rainfall anomalies, flooded vegetation, livestock density, and mosquito habitat mapping.

**Oropouche fever** can be a later arboviral add-on because WHO reports that it is spread mainly by biting midges and possibly some mosquitoes, with notable expansion in the Americas since late 2023. [8]

### 4.3 Schistosomiasis: second flagship

Schistosomiasis is the clearest non-mosquito expansion. WHO describes transmission through contact with infested freshwater, with freshwater snails acting as intermediate hosts; WHO’s 2026 fact sheet reports that at least 253.7 million people required preventive treatment in 2024. [9]

VectorOS should model:

- persistent or seasonal freshwater,
- aquatic or shoreline vegetation,
- slow-moving or stagnant water bodies,
- likely water-contact access points,
- proximity to schools, villages, farms, and health facilities,
- seasonality and rainfall anomalies,
- snail occurrence records and local survey data where available.

The product should output a **water-contact and snail-habitat risk layer**, not a claim that snails or infections are definitely present.

### 4.4 Onchocerciasis: river-corridor intelligence

WHO describes onchocerciasis transmission through repeated bites from infected blackflies that breed in rapidly flowing rivers and streams; WHO also reported that at least 252.3 million people required preventive treatment against onchocerciasis in 2024. [10]

VectorOS should not use a naive “water nearby = risk” rule. It should map:

- fast-flowing rivers and streams,
- river slope, rapids, and flow proxies,
- downstream and upstream corridor risk,
- human settlements and fields along river corridors,
- adult dispersal buffers,
- historical endemicity and preventive-treatment program context when available.

Output should be **breeding-corridor and surveillance-priority maps**, not point-level predictions of infection.

### 4.5 Tsetse and human African trypanosomiasis

WHO frames human African trypanosomiasis as a rural, tsetse-transmitted disease in sub-Saharan Africa, with most exposed people living in rural areas and depending on agriculture, fishing, animal husbandry, or hunting. [11]

The tsetse module should shift the product from “standing water detection” to **vector niche mapping**. It should use:

- vegetation structure and phenology,
- land cover and riverine vegetation,
- humidity and temperature constraints,
- livestock/wildlife interface proxies,
- settlement and travel-corridor exposure,
- known tsetse occurrence or trap data where available.

The first output should be a **tsetse ecological suitability surface** plus trap-priority suggestions for field teams.

### 4.6 Leishmaniasis and sandfly risk

WHO notes that more than one billion people live in areas endemic for leishmaniasis and are at risk of infection; the disease is transmitted by female phlebotomine sandflies and is associated with poverty, poor housing, displacement, environmental change, and climate change. [12,13]

The sandfly signal is less direct than mosquito water habitat or schistosomiasis freshwater habitat, so leishmaniasis should be a Phase II or Phase III module. It should use:

- settlement structure,
- land cover and vegetation ecotones,
- deforestation and environmental disturbance,
- temperature and moisture suitability,
- animal/reservoir proxies where permitted and available,
- historical case and vector occurrence data.

The output should be **ecotone and settlement vulnerability mapping**, not a definitive transmission map.

### 4.7 CCHF and tick/livestock-linked risk

WHO describes Crimean-Congo haemorrhagic fever as a tick-borne viral disease with livestock involvement, wide geographic distribution, and high case-fatality potential. WHO identifies Hyalomma ticks as the principal vector and describes transmission via tick bites or contact with infected animal blood/tissues. [14]

VectorOS should model CCHF as a different ecological module:

- rangeland greenness and phenology,
- temperature and humidity suitability,
- livestock density and seasonality,
- livestock markets, abattoirs, and animal-movement proxies where available,
- tick occurrence records,
- human occupational exposure proxies.

The product should support **risk awareness and surveillance prioritization** for public-health and veterinary-health coordination. It should avoid individual diagnostic or clinical guidance.

---

## 5. Strategic Data Organization

VectorOS should separate data into five layers: image, environment, exposure, surveillance labels, and operations. Every layer should have a common spatial-temporal indexing system so it can be joined into model-ready examples and product-ready objects.

### 5.1 Canonical spatial-temporal unit

Use a canonical **Risk Tile** as the base unit.

Recommended defaults:

- **Tile geometry**: H3 cell or Web Mercator tile plus exact polygon boundary.
- **Core spatial resolution**: 250 m to 1 km for national risk surfaces; 10 m to 30 m for habitat evidence; sub-meter to 30 cm where licensed imagery is available.
- **Temporal cadence**: weekly for operational risk; daily for rainfall/flood alerts; monthly for slower ecological suitability.
- **Model time window**: use disease-specific lags, not just same-day imagery.
- **AOI hierarchy**: tile → village/settlement → facility catchment → district → province → country.

A Risk Tile should never be just a raster cell. It should be an ontology object with provenance, evidence, risk score, uncertainty, nearby exposed populations, linked reports, linked tasks, and validation status.

### 5.2 Layer 1: Core image and remote-sensing data

| Data source | Role in VectorOS | Training usage | Inference usage | Notes |
|---|---|---|---|---|
| **DPhi SimSat Sentinel-2** | Hackathon-required multispectral satellite image source | Fine-tune model on official competition imagery | Demo-time current or recent inference | Use as the core demo imagery layer; verify exact endpoint names in the SimSat repo before coding. [1] |
| **DPhi SimSat Mapbox** | High-resolution context imagery | Fine-tune visual interpretation of settlement/water/contact-site context | Static high-resolution map context | Great for visual inspection and product UX; not radiometrically reliable for index computation. [1] |
| **Sentinel-2 L2A** | Global optical backbone | Generate RGB, false color, red-edge, NDWI/MNDWI, NDMI, NDVI, NDRE panels | Routine risk-map updates | Sentinel-2 has 13 spectral bands, 10 m resolution for key bands, and 5-day revisit. [15] |
| **Sentinel-1 SAR** | All-weather wetness and flood evidence | Train cloud-robust wetness/flood/habitat signals | Fill gaps during cloudy/rainy periods | Sentinel-1 provides all-weather, day-and-night radar imagery. [16] |
| **Harmonized Landsat-Sentinel (HLS)** | Dense, harmonized time series | Train temporal phenology and lag features | Fill optical time-series gaps | HLS gives analysis-ready harmonized Landsat/Sentinel observations; NASA describes observations every 2–3 days at 30 m. [17] |
| **Landsat archive** | Long historical context | Retrospective label alignment from long-term disease data | Long-term baseline and seasonality | Useful for multi-decade water/land-cover history. |
| **VIIRS / MODIS** | Night lights, land surface temperature, phenology | Context and covariates | Regional anomaly monitoring | Coarser, but useful for temperature, urbanization, and seasonality. |
| **Commercial imagery** | Very high-resolution local inspection | Optional labels for containers, drainage, roofs, peri-domestic features | Premium or partner deployments | Use only when licensing and privacy constraints are satisfied. |

### 5.3 Derived satellite features

The base Sentinel-2 idea should evolve from “NDWI + B8A” to a defensible multi-index stack. B8A is useful as a narrow NIR/red-edge-adjacent vegetation characterization band, but moisture-sensitive SWIR-informed indices are generally stronger for plant/landscape moisture. The better stack is **NDWI + MNDWI + NDMI + NDVI/NDRE + red-edge features + SAR wetness + seasonality + texture + exposure overlays**.

| Feature | Formula / basis | Disease relevance |
|---|---|---|
| **NDWI** | Green and NIR water index | Open water, shallow standing water candidates |
| **MNDWI** | Green and SWIR water index | Built-up-area water discrimination; Aedes urban water context |
| **NDMI** | NIR and SWIR moisture index | Vegetation and landscape moisture; stronger complement than B8A alone for plant-water stress |
| **NDVI / EVI** | Vegetation vigor | Mosquito shade/fringes, tsetse/sandfly niche, rangeland greenness |
| **NDRE / red-edge features** | Red-edge and NIR | Vegetation condition, wetland/aquatic vegetation, crop/irrigation patterns |
| **BSI** | Bare soil index | Construction/disturbance, dry-season pools, peri-domestic surface context |
| **NDBI** | Built-up index | Urban Aedes context and settlement structure |
| **SAR VV/VH backscatter** | Sentinel-1 | Flood/wetness under clouds; vegetation structure; inundation |
| **Water recurrence** | JRC Global Surface Water / historical composites | Persistent vs seasonal water classification |
| **Texture features** | GLCM, edge density, connected components | Container-like urban texture, shoreline complexity, vegetation-water fringe detection |
| **Change features** | difference from seasonal baseline | New water, flooding, land-use disturbance, sudden vegetation changes |

### 5.4 Layer 2: Climate, hydrology, terrain, land, and soils

| Dataset | Role | Notes |
|---|---|---|
| **CHIRPS v2/v3** | Long historical rainfall and rainfall anomalies | CHIRPS v2 spans 1981 to near-present at 0.05° resolution; the Climate Hazards Center notes CHIRPS v3 became operational in 2025 and spans 60°N–60°S. [18,19] |
| **IMERG** | Near-real-time precipitation | NASA states IMERG provides near-real-time half-hour precipitation estimates and is useful for disasters, disease, and resource management. [20] |
| **ERA5-Land** | Temperature, humidity, evapotranspiration, soil/land climate variables | ERA5-Land provides hourly land-surface variables at ~9 km from 1950 to about five days before present. [21] |
| **SMAP** | Soil moisture | NASA describes SMAP as measuring surface soil moisture and freeze-thaw globally every two to three days. [22] |
| **JRC Global Surface Water** | Water occurrence, seasonality, transitions | Maps global surface water location and temporal distribution from Landsat imagery from 1984–2021. [23] |
| **ESA WorldCover** | 10 m land cover | Global 10 m land-cover classification based on Sentinel-1 and Sentinel-2. [24] |
| **Copernicus DEM / SRTM / NASADEM** | Elevation, slope, drainage potential | Core for runoff, puddling, river slope, and catchment context. Copernicus DEM includes global GLO-30 and GLO-90 products. [47] |
| **HydroSHEDS / HydroRIVERS / HydroBASINS** | River networks, sub-basins, flow context | HydroRIVERS provides global river reaches; HydroBASINS provides nested sub-basins. [25,26] |
| **SoilGrids** | Soil texture, drainage-relevant properties, uncertainty | SoilGrids provides global 250 m predictions for standard soil properties. [27] |
| **GloFAS / flood products** | River discharge and flood hazard | Optional operational hydrological risk layer. |
| **Coastline/wetland datasets** | Wetlands, coastal flooding, estuaries | Useful for Culex, RVF, waterborne modules, and coastal cholera risk. |

### 5.5 Layer 3: Human exposure and operational context

| Dataset | Role | Why it matters |
|---|---|---|
| **WorldPop** | Gridded population, age/sex where available | Estimate population exposed to habitats and risk zones. WorldPop develops open high-resolution geospatial population data for health and development. [28] |
| **GHSL** | Built-up surfaces, population, settlement classifications | GHSL provides built-up maps, population density maps, and settlement maps over time. [29] |
| **OpenStreetMap / Overpass API** | Buildings, roads, waterways, land use, settlements | Useful for exposure, routes, facilities, drainage, and community tasking. Overpass is a read-only API for custom OSM data selection. [30] |
| **Healthsites.io** | Health-facility locations | Facility catchments, referral context, health-system exposure; Healthsites provides an open global health-facility map and API/export formats. [31] |
| **Schools / water points / WASH infrastructure** | High-value exposed sites | Especially important for schistosomiasis and waterborne modules. Use national or humanitarian datasets where available. |
| **FAO Gridded Livestock of the World / livestock layers** | Livestock exposure and host density | Important for CCHF, RVF, Japanese encephalitis, tsetse, and One Health modules. FAO describes GLW as a peer-reviewed spatial dataset on livestock distribution and abundance. [48] |
| **Roads and mobility proxies** | Access and intervention logistics | Field-task planning, supply routing, health-facility access. |
| **Administrative boundaries** | Reporting and governance | Required for ministry workflows and integration with HMIS/DHIS2. |

### 5.6 Layer 4: Health, vector, reservoir, and validation labels

VectorOS needs labels, but label quality varies widely. Treat every label source with metadata: spatial precision, temporal precision, reporting bias, access restrictions, and ethical limitations.

| Label source | Disease/module | Use | Caveat |
|---|---|---|---|
| **WHO Global Health Observatory / APIs** | Global disease indicators | Country-level and sometimes subnational trend context | Often too coarse for tile-level modeling. WHO provides a GHO OData API. [32] |
| **PAHO dengue / arboviral reporting** | Dengue, chikungunya, Zika, yellow fever in the Americas | Regional case signal and validation | Coverage and definitions vary by country/reporting period; PAHO reports that 46 countries and territories systematically report weekly dengue indicators. [33] |
| **OpenDengue** | Dengue | Standardized public dengue case counts; strong for retrospective training and validation | Spatial precision varies by country and time; OpenDengue describes a standardized public dengue database, and the peer-reviewed dataset contains tens of millions of dengue case records. [34,35] |
| **MAP / malariaAtlas / Vector Atlas** | Malaria parasite rate, vector occurrence, vector modeling | Malaria risk covariates and labels; Anopheles vector occurrence | Survey dates, displacement, sampling bias. [36] |
| **DHS / MIS** | Malaria indicators, household survey context, WASH and demographic context | Regional model covariates and validation | DHS cluster GPS points are deliberately displaced for confidentiality: up to 2 km in urban clusters, up to 5 km in rural clusters, and 1% of rural clusters up to 10 km. Use buffers or aggregation. [37] |
| **GBIF** | Vector, snail, tick, sandfly, tsetse, reservoir occurrence records | Presence-only occurrence labels, candidate validation | Sampling bias; taxonomic verification needed. GBIF provides APIs and occurrence downloads. [38] |
| **VectorByte** | Vector traits and abundance | Trait-informed models and abundance context | Coverage varies by species and geography. |
| **VectAbundance** | Aedes abundance | Harmonized Aedes observations for calibration | Geographically limited but useful. |
| **Mosquito Alert and citizen science** | Mosquito sightings, breeding sites, images | Field-signal augmentation, image-label bootstrapping | Reporting bias and expert validation status must be tracked. |
| **National DHIS2 / HMIS** | Official case surveillance, aggregate alerts, facility reports | Best operational integration path for ministries | Requires data-sharing agreements and privacy governance. DHIS2 is widely used by ministries and supports disease surveillance workflows and APIs. [39,40] |
| **Field validation app** | All modules | First-party ground truth: habitat observations, vector/snail/tick observations, field photos, task outcomes | Requires QA, consent, GPS fuzzing where needed, and offline sync. |

### 5.7 Layer 5: Operations and intervention data

Operational data is the difference between a map and a product. VectorOS should ingest and produce:

- field team assignments,
- inspection routes,
- habitat validation results,
- intervention logs,
- insecticide-treated net distribution context where relevant,
- larval-source-management logs where locally approved,
- preventive chemotherapy campaign zones for schistosomiasis/onchocerciasis where relevant,
- animal-health surveillance and tick/livestock monitoring activities,
- water-contact-site interventions,
- post-action follow-up outcomes,
- stockouts or facility capacity flags,
- comments, approvals, and audit events.

VectorOS should treat interventions as official public-health workflows configured by the deploying organization, not freely invented by the AI. The AI can prioritize and draft; local authorities approve.

---

## 6. Data Architecture

### 6.1 Data lakehouse structure

Use a geospatial lakehouse with four zones.

```text
vectoros-data/
  bronze_raw/
    satellite/
      dphi_simsat/
      sentinel2/
      sentinel1/
      hls/
      landsat/
    climate/
      chirps/
      imerg/
      era5_land/
      smap/
    hydrology/
      jrc_gsw/
      hydrosheds/
      dem/
    exposure/
      worldpop/
      ghsl/
      osm/
      healthsites/
      livestock/
    surveillance/
      who_gho/
      paho/
      opendengue/
      dhis2_partner/
      map_malariaatlas/
      gbif/
      vectorbyte/
      mosquito_alert/
    operations/
      field_tasks/
      interventions/
      observations/

  silver_processed/
    cloud_masked_composites/
    index_rasters/
    sar_features/
    climate_lags/
    hydrology_features/
    exposure_features/
    label_tables/
    geojson_objects/

  gold_features/
    risk_tile_features/
    disease_module_features/
    training_examples/
    validation_sets/
    product_views/

  model_outputs/
    habitat_detections/
    risk_tiles/
    reports/
    alerts/
    uncertainty_surfaces/
```

Use:

- **Cloud-Optimized GeoTIFFs (COGs)** for raster tiles.
- **Zarr** for large time-series arrays.
- **GeoParquet** for vector features and training examples.
- **PostGIS** for product queries, geospatial joins, and API serving.
- **STAC** for discoverability and provenance. OGC describes STAC as a standard for structuring and querying geospatial asset metadata. [41]
- **Object storage** such as S3, GCS, Azure Blob, or Cloudflare R2 for raw and processed assets.
- **Model registry** for risk models, VLM adapters, calibration models, and prompt/schema versions.

### 6.2 Canonical IDs

Every object should carry stable IDs.

```text
risk_tile_id       = h3_res + h3_index + disease_module + interval_start
habitat_patch_id   = run_id + geometry_hash + habitat_type
model_run_id       = model_name + version + timestamp + region
source_asset_id    = stac_collection + item_id + asset_name
report_id          = admin_id + disease_module + period + generated_at
field_task_id      = task_type + aoi_id + created_at + UUID
```

### 6.3 Provenance requirements

Each generated risk score and report must store:

- source datasets,
- source timestamps,
- preprocessing versions,
- cloud-cover and quality flags,
- model versions,
- prompt/schema versions,
- confidence and uncertainty values,
- human edits and approvals,
- export history,
- data-access permissions.

This is essential for ministry trust, scientific validation, and safe deployment.

---

## 7. Fine-Tuning Strategy for `LiquidAI/LFM2.5-VL-450M`

### 7.1 Fine-tuning role

Fine-tune `LiquidAI/LFM2.5-VL-450M` to be a **geospatial visual analyst and structured-output generator**.

It should learn to:

- read multispectral visual panels,
- compare current imagery with historical or seasonal baseline panels,
- detect likely habitat patterns,
- ground evidence in bounding boxes or polygons where possible,
- connect visual evidence to non-image features,
- output strict JSON matching VectorOS schemas,
- draft concise English health-officer reports,
- express uncertainty and data limitations,
- avoid patient-level diagnosis and unsupported claims.

It should not be the only risk model. The calibrated risk layer should include geospatial statistics, ecological niche models, anomaly detection, and disease-specific time-series models.

### 7.2 Training example design

Each training example should be an **AOI-time disease-module packet**.

```json
{
  "example_id": "vecos_train_000001",
  "disease_module": "mosquito_anopheles_malaria",
  "aoi": {
    "h3": "8844a13687fffff",
    "admin0": "Kenya",
    "admin1": "Kisumu",
    "admin2": "example_district",
    "bbox": [34.62, -0.13, 34.67, -0.08]
  },
  "time_window": {
    "target_week_start": "2025-04-07",
    "target_week_end": "2025-04-13",
    "lag_days": [7, 14, 21, 28, 45]
  },
  "image_panels": [
    {
      "panel_id": "sentinel2_rgb_current",
      "source": "Sentinel-2 L2A / DPhi SimSat",
      "bands": ["B04", "B03", "B02"],
      "timestamp": "2025-04-10"
    },
    {
      "panel_id": "sentinel2_false_color",
      "bands": ["B08", "B04", "B03"]
    },
    {
      "panel_id": "ndwi",
      "derived_index": "NDWI"
    },
    {
      "panel_id": "ndmi",
      "derived_index": "NDMI"
    },
    {
      "panel_id": "sentinel1_wetness",
      "source": "Sentinel-1 GRD"
    },
    {
      "panel_id": "population_overlay",
      "source": "WorldPop/GHSL"
    }
  ],
  "numeric_features": {
    "water_area_m2": 18400,
    "water_persistence_percentile": 0.74,
    "ndmi_median": 0.22,
    "rain_7d_mm": 62.4,
    "rain_21d_mm": 144.9,
    "temp_mean_c_14d": 25.7,
    "population_within_2km": 5100,
    "distance_to_health_facility_m": 3200,
    "cloud_cover_percent": 7.5
  },
  "weak_labels": {
    "habitat_candidates": ["vegetated_standing_water", "irrigation_fringe"],
    "case_signal_trend": "increasing",
    "entomology_presence": "unknown"
  },
  "target_output": {
    "risk_class": "high",
    "risk_score": 82,
    "confidence": 0.71,
    "habitat_findings": [
      {
        "type": "vegetated_standing_water",
        "geometry_ref": "patch_001",
        "evidence": ["NDWI positive", "NDMI elevated", "persistent water", "population within 2 km"]
      }
    ],
    "report": "High habitat suitability for Anopheles-type breeding conditions near exposed settlements. Prioritize field inspection of vegetated standing water and update local surveillance records."
  }
}
```

### 7.3 Image packet format

For every AOI-time example, create a consistent panel layout:

1. True color imagery.
2. False color vegetation/water imagery.
3. NDWI/MNDWI water mask.
4. NDMI moisture panel.
5. NDVI/NDRE vegetation panel.
6. Sentinel-1 wetness/flood proxy panel.
7. JRC water persistence or seasonality panel.
8. Land-cover panel.
9. Population/facility/settlement overlay.
10. Optional high-resolution Mapbox/local imagery panel.

The VLM should see the same panel order during training and inference. Each panel should include a small legend, north arrow, and scale marker where possible. Sidecar JSON should contain exact values so the model is not forced to infer numeric quantities from colors.

### 7.4 Fine-tuning tasks

Use multi-task supervised fine-tuning.

| Task | Input | Target | Why it matters |
|---|---|---|---|
| **Habitat classification** | Image packet + sidecar features | habitat classes and confidence | Teaches disease-specific visual interpretation |
| **Visual grounding** | Image packet | bounding boxes/polygons for habitat evidence | Makes reports explainable and map-clickable |
| **Structured risk report** | Image packet + feature JSON | strict `RiskTile` JSON | Enables reliable product APIs |
| **Evidence explanation** | Image packet + features | evidence cards with source layers | Supports user trust and auditability |
| **Uncertainty expression** | low-quality/cloudy/ambiguous cases | uncertainty and “needs validation” flags | Avoids overclaiming |
| **AOI Q&A** | map context + user question | concise English answer with citations to data layers | Powers the copilot |
| **Change detection summary** | current + baseline packets | “what changed” report | Key for weekly operations |
| **Task drafting** | high-risk tile + field capacity | draft field task | Turns maps into action |

### 7.5 Training data generation pipeline

```text
1. Choose disease module and geography
2. Build AOI-time grid
3. Fetch DPhi/Sentinel/Mapbox imagery and external data layers
4. Generate cloud masks, composites, indices, SAR features, climate lags, and exposure features
5. Create image packets and sidecar JSON
6. Attach labels from cases, entomology, occurrence data, field surveys, and weak ecological rules
7. Sample positives, hard negatives, random negatives, and uncertain cases
8. Human-review a subset with geospatial public-health annotation guidelines
9. Convert to LFM2.5-VL instruction-tuning records
10. Fine-tune LoRA adapters per module and a shared VectorOS adapter
11. Evaluate spatial, temporal, and sensor generalization
12. Register model, schema, and calibration artifacts
```

### 7.6 Sampling strategy

Avoid biased datasets that only contain known outbreaks. Use four sample classes:

- **Positive examples**: known cases, vector occurrences, confirmed field habitats, citizen reports with validation, high-confidence habitat patches.
- **Hard negatives**: water bodies or vegetation that look suspicious but are unsuitable due to flow, salinity, depth, built infrastructure, seasonality, or distance from exposure.
- **Random ecological negatives**: randomly sampled tiles across climate zones, seasons, and land-cover types.
- **Uncertain examples**: cloudy, mixed-resolution, conflicting-label, or sparse-data areas that teach the model to say “uncertain.”

### 7.7 Splits and leakage control

Use strict validation splits:

- **Spatial holdout**: hold out entire districts, ecological zones, and countries.
- **Temporal holdout**: train on past periods and evaluate future weeks/months.
- **Sensor holdout**: evaluate on scenes from different satellites or with missing panels.
- **Disease holdout**: test whether the model generalizes across habitat concepts without hallucinating.
- **Label-source holdout**: evaluate against field validation not used in training.

Do not split randomly by chip only. Random chip splits can leak neighboring pixels and produce inflated scores.

### 7.8 Fine-tuning stages

| Stage | Name | Goal | Data |
|---|---|---|---|
| **FT-0** | Format adaptation | Teach the model VectorOS JSON schemas and report style | Synthetic map panels, generated labels, curated examples |
| **FT-1** | Satellite-habitat grounding | Teach visual patterns for water, vegetation, settlement, wetness, rivers, rangelands | Sentinel/Mapbox/HLS/SAR packets with weak and human labels |
| **FT-2** | Disease-module specialization | Train module-specific adapters | Mosquito, schisto, oncho, tsetse, leish, CCHF packets |
| **FT-3** | Copilot tool calling | Teach safe tool calls and evidence retrieval | Simulated product state + tool-call transcripts |
| **FT-4** | Field-feedback adaptation | Improve with validated observations | Real deployment observations and approved corrections |

### 7.9 Model composition

Recommended stack:

```text
LFM2.5-VL-450M shared base
  ├── VectorOS shared geospatial adapter
  ├── Mosquito adapter
  ├── Schisto adapter
  ├── River-vector/oncho adapter
  ├── Tsetse adapter
  ├── Sandfly/leish adapter
  └── Tick/livestock adapter

Risk calibration layer
  ├── Habitat segmentation/object detection model
  ├── Ecological niche model / MaxEnt / XGBoost
  ├── Bayesian spatiotemporal model
  ├── Case anomaly detector
  ├── Exposure model
  └── Uncertainty ensemble
```

This lets the product keep one general visual-language foundation while allowing disease-specific reasoning.

---

## 8. Structured Outputs

Structured outputs are the backbone of VectorOS. The product should never depend on free-form model text for critical state. Free-form English reports should be generated from structured records.

### 8.1 `RiskTile` schema

```json
{
  "$schema": "https://vectoros.ai/schemas/risk_tile.v1.json",
  "schema_version": "1.0",
  "risk_tile_id": "string",
  "run_id": "string",
  "generated_at": "ISO-8601 datetime",
  "disease_module": "mosquito_anopheles_malaria | mosquito_aedes_arbovirus | schistosomiasis | onchocerciasis | tsetse_hat | leishmaniasis | cchf_tick_livestock | water_climate",
  "disease_targets": ["string"],
  "aoi": {
    "h3_index": "string",
    "admin0": "string",
    "admin1": "string",
    "admin2": "string",
    "bbox": [0, 0, 0, 0],
    "centroid": {"lat": 0, "lon": 0}
  },
  "time_window": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "lag_days_used": [7, 14, 21, 28]
  },
  "risk": {
    "score": 0,
    "class": "very_low | low | moderate | high | very_high",
    "confidence": 0.0,
    "trend_vs_previous_period": "decreasing | stable | increasing | unknown",
    "uncertainty_interval": [0, 0],
    "calibration_model_version": "string"
  },
  "hazards": [
    {
      "hazard_id": "string",
      "type": "standing_water | aquatic_vegetation | fast_flowing_river | vegetation_ecotone | rangeland_tick_habitat | flood_exposure | other",
      "subtype": "string",
      "geometry_ref": "string",
      "bbox": [0, 0, 0, 0],
      "area_m2": 0,
      "persistence": "ephemeral | seasonal | persistent | unknown",
      "evidence_layers": ["NDWI", "NDMI", "Sentinel-1", "JRC-GSW"],
      "confidence": 0.0
    }
  ],
  "exposure": {
    "population_total_est": 0,
    "population_under5_est": 0,
    "settlements_within_buffer": 0,
    "health_facilities_within_buffer": 0,
    "schools_within_buffer": 0,
    "livestock_density_summary": {},
    "buffer_m": 2000
  },
  "signals": {
    "satellite": [
      {"source": "Sentinel-2", "timestamp": "YYYY-MM-DD", "quality": "good", "asset_id": "string"}
    ],
    "climate": {
      "rain_7d_mm": 0,
      "rain_21d_mm": 0,
      "temperature_mean_14d_c": 0,
      "soil_moisture_percentile": 0
    },
    "health_surveillance": {
      "case_signal_available": true,
      "case_trend": "increasing | stable | decreasing | unknown",
      "source": "OpenDengue | DHIS2 | WHO | PAHO | none",
      "spatial_precision": "tile | admin2 | admin1 | country | unknown"
    },
    "entomology_or_host": {
      "observation_available": true,
      "source": "field | GBIF | VectorByte | MosquitoAlert | other",
      "recency_days": 0
    }
  },
  "rationale": [
    {
      "claim": "string",
      "evidence_layer": "string",
      "evidence_ref": "string",
      "confidence": 0.0
    }
  ],
  "recommended_actions": [
    {
      "action_type": "field_inspection | increase_surveillance | larval_source_management_review | water_contact_site_review | vector_trap_priority | livestock_tick_monitoring | community_risk_communication | no_action",
      "description": "string",
      "priority": "low | medium | high",
      "requires_human_approval": true
    }
  ],
  "limitations": ["string"],
  "audit": {
    "model_versions": {},
    "data_versions": {},
    "prompt_version": "string",
    "human_review_status": "unreviewed | reviewed | approved | rejected"
  }
}
```

### 8.2 `HabitatPatch` schema

```json
{
  "habitat_patch_id": "string",
  "disease_module": "string",
  "habitat_type": "string",
  "geometry": "GeoJSON geometry or geometry_ref",
  "detected_at": "ISO-8601 datetime",
  "source_images": ["asset_id"],
  "area_m2": 0,
  "distance_to_nearest_settlement_m": 0,
  "distance_to_nearest_health_facility_m": 0,
  "water_persistence": "ephemeral | seasonal | persistent | unknown",
  "vegetation_fringe_score": 0.0,
  "confidence": 0.0,
  "field_validation": {
    "status": "not_requested | requested | confirmed | rejected | inconclusive",
    "observation_ids": []
  }
}
```

### 8.3 `DiseaseSignal` schema

```json
{
  "signal_id": "string",
  "disease": "string",
  "source": "WHO | PAHO | OpenDengue | DHIS2 | field | other",
  "spatial_unit": {
    "type": "admin0 | admin1 | admin2 | facility | tile | point",
    "id": "string"
  },
  "time_period": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  },
  "metric": "cases | suspected_cases | confirmed_cases | test_positivity | prevalence | vector_count | host_count | citizen_report_count",
  "value": 0,
  "unit": "count | rate | proportion | index",
  "quality": {
    "spatial_precision": "exact | displaced | admin | unknown",
    "temporal_precision": "daily | weekly | monthly | annual | unknown",
    "reporting_bias_notes": "string",
    "confidence": 0.0
  },
  "privacy": {
    "contains_personal_data": false,
    "aggregation_threshold_met": true
  }
}
```

### 8.4 `OperationalTask` schema

```json
{
  "task_id": "string",
  "created_at": "ISO-8601 datetime",
  "created_by": "user | model | rule_engine",
  "requires_approval": true,
  "approval_status": "draft | approved | rejected | completed",
  "task_type": "field_inspection | vector_trap | habitat_validation | water_contact_site_check | livestock_tick_monitoring | facility_followup | report_review",
  "priority": "low | medium | high | urgent",
  "aoi": {
    "geometry_ref": "string",
    "admin2": "string",
    "risk_tile_ids": []
  },
  "reason": "string",
  "linked_evidence": ["risk_tile_id", "habitat_patch_id"],
  "assigned_team": "string",
  "due_date": "YYYY-MM-DD",
  "field_form_schema": "string",
  "completion": {
    "status": "not_started | in_progress | completed | blocked",
    "completed_at": "ISO-8601 datetime",
    "result_observation_ids": []
  }
}
```

### 8.5 `OfficerReport` schema

```json
{
  "report_id": "string",
  "report_type": "district_weekly | outbreak_support | field_brief | ministry_summary | donor_summary",
  "disease_module": "string",
  "period": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
  "geography": {"admin0": "string", "admin1": "string", "admin2": "string"},
  "headline": "string",
  "summary": "string",
  "key_findings": ["string"],
  "map_refs": ["string"],
  "priority_areas": [
    {"name": "string", "risk_class": "high", "main_evidence": ["string"], "recommended_action": "string"}
  ],
  "data_quality_notes": ["string"],
  "approved_by": "string",
  "export_formats": ["PDF", "DOCX", "HTML", "JSON"]
}
```

---

## 9. Risk Modeling and Inference Pipeline

### 9.1 Weekly batch inference

Weekly batch inference should produce national and regional risk maps.

```text
1. Pull newest imagery and climate data
2. Create cloud-masked optical composites
3. Create SAR wetness/flood composites
4. Compute indices, lags, anomalies, and exposure features
5. Generate AOI image packets
6. Run VLM to produce habitat/evidence JSON
7. Run disease-module risk model and uncertainty ensemble
8. Store RiskTile, HabitatPatch, and EvidenceCard objects
9. Generate reports and update dashboards
10. Trigger field-task recommendations for approval
```

### 9.2 Event-driven inference

Run event-driven inference when:

- rainfall exceeds disease-specific percentile thresholds,
- flood extent changes abruptly,
- case signals increase above expected baseline,
- field reports identify new habitat,
- cloud-free imagery becomes available after a long cloudy period,
- a ministry user requests a custom AOI analysis.

### 9.3 Onboard or edge inference

The onboard/edge use case should be realistic and narrow. The satellite or edge node should not run the whole VectorOS platform. It should run **triage inference**:

- cloud detection,
- water/wetness anomaly detection,
- habitat-candidate patch extraction,
- compact metadata generation,
- selection of high-value crops for downlink,
- optional VLM structured caption for selected 512 × 512 patches.

The ground platform should then fuse the patch outputs with health, climate, hydrology, and exposure layers. This preserves the hackathon’s “AI in space / limited downlink” thesis while keeping epidemiological fusion on the ground where broader data access exists.

### 9.4 Modal GPU inference design

Use Modal for serverless GPU inference and scheduled geospatial jobs. Modal’s docs show GPU acceleration through a function `gpu` argument and support multiple GPU types including T4, L4, A10, L40S, A100, H100, H200, and B200. [42]

Recommended services:

```text
modal_app/
  vectoros_vlm_inference.py
    - loads LFM2.5-VL-450M + selected LoRA adapter
    - accepts image_packet_uri + sidecar_json
    - returns strict JSON after schema validation

  vectoros_batch_tiles.py
    - scheduled weekly/daily jobs
    - pulls risk-tile feature batches
    - calls VLM service and calibration models

  vectoros_report_generation.py
    - generates report drafts from structured outputs

  vectoros_evaluation.py
    - runs holdout evaluation and drift checks
```

Because the model is compact, the first production target can be cost-effective GPU inference using L4/T4/A10-class GPUs. For national batch runs, parallelize by AOI and disease module.

---

## 10. Product Architecture

### 10.1 System architecture

```text
                       ┌───────────────────────────────┐
                       │ External data APIs/sources     │
                       │ DPhi, Copernicus, NASA, WHO,   │
                       │ PAHO, OpenDengue, OSM, DHIS2   │
                       └──────────────┬────────────────┘
                                      │
                        ingestion connectors + schedulers
                                      │
                       ┌──────────────▼────────────────┐
                       │ Geospatial lakehouse           │
                       │ COG/Zarr/GeoParquet/STAC       │
                       └──────────────┬────────────────┘
                                      │
                         feature pipelines + QA checks
                                      │
                       ┌──────────────▼────────────────┐
                       │ Geospatial feature store       │
                       │ RiskTile features by module    │
                       └──────────────┬────────────────┘
                                      │
               ┌──────────────────────┼──────────────────────┐
               │                      │                      │
     ┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
     │ LFM2.5-VL service │  │ Risk models       │  │ Anomaly detectors │
     │ Modal GPU         │  │ calibrated scores │  │ case/climate      │
     └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
               └──────────────────────┼──────────────────────┘
                                      │
                       ┌──────────────▼────────────────┐
                       │ VectorOS ontology + PostGIS    │
                       │ RiskTiles, Patches, Reports,   │
                       │ Tasks, Signals, Users, Audit    │
                       └──────────────┬────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
 ┌────────▼────────┐       ┌──────────▼─────────┐       ┌─────────▼────────┐
 │ Web map console │       │ Copilot API        │       │ Field app / API  │
 │ dashboards      │       │ tool-grounded RAG  │       │ offline sync     │
 └─────────────────┘       └────────────────────┘       └──────────────────┘
```

### 10.2 Core backend components

| Component | Recommended stack | Purpose |
|---|---|---|
| **API gateway** | FastAPI or Node/NestJS | Authenticated access to tiles, reports, tasks, copilot, ingestion status |
| **Geospatial DB** | Postgres + PostGIS | Serve vector objects, joins, AOI queries, task state, admin hierarchy |
| **Tile server** | TiTiler / Martin / GeoServer / MapLibre vector tiles | Serve raster and vector map layers |
| **Object storage** | S3/GCS/Azure/R2 | Store COGs, Zarr arrays, image packets, reports, artifacts |
| **Workflow orchestration** | Dagster / Prefect / Airflow | Data ingestion, features, batch inference, validation, reports |
| **Feature store** | GeoParquet + DuckDB/BigQuery/Snowflake/PostGIS | Join raster-derived features, exposure, health signals, labels |
| **GPU inference** | Modal | Run VLM inference and fine-tuned adapters |
| **Model registry** | MLflow / Weights & Biases / custom registry | Store model versions, adapters, metrics, schemas |
| **Frontend** | Next.js + MapLibre GL + deck.gl | Map-native product UI |
| **Copilot** | Tool-using LLM + retrieval + policy guardrails | Data-grounded English chat and report generation |
| **Auth/RBAC** | Auth0/Clerk/Keycloak + ABAC | Ministry, district, analyst, field-team, public-view roles |
| **Audit log** | Append-only event log | Trust, governance, investigation, reproducibility |

### 10.3 API surface

The product should expose clear APIs. These APIs should return structured objects first and report text second.

```http
GET /v1/layers
GET /v1/layers/{layer_id}/tiles/{z}/{x}/{y}
GET /v1/risk-tiles?disease_module=&bbox=&start_date=&end_date=&risk_class=
GET /v1/risk-tiles/{risk_tile_id}
GET /v1/habitat-patches?bbox=&type=&validation_status=
POST /v1/inference/analyze-aoi
POST /v1/reports/generate
GET /v1/reports/{report_id}
POST /v1/tasks
PATCH /v1/tasks/{task_id}
POST /v1/field-observations
GET /v1/disease-signals?source=&disease=&admin_id=&period=
POST /v1/copilot/chat
GET /v1/audit/events?object_id=
```

Example inference request:

```json
{
  "disease_module": "mosquito_anopheles_malaria",
  "aoi": {
    "type": "bbox",
    "bbox": [34.62, -0.13, 34.67, -0.08]
  },
  "time_window": {
    "start_date": "2026-04-20",
    "end_date": "2026-04-27"
  },
  "include_layers": ["sentinel2", "sentinel1", "chirps", "worldpop", "healthsites"],
  "output": ["risk_tiles", "habitat_patches", "officer_report"]
}
```

Example response:

```json
{
  "run_id": "run_20260427_ken_kisumu_malaria_v1",
  "status": "completed",
  "risk_tiles_uri": "s3://vectoros/model_outputs/.../risk_tiles.geojson",
  "habitat_patches_uri": "s3://vectoros/model_outputs/.../patches.geojson",
  "report_id": "rep_20260427_ken_kisumu_malaria",
  "summary": "12 high-risk tiles identified; main drivers are recent rainfall, persistent vegetated water, and high exposed population within 2 km."
}
```

---

## 11. Core Product Features

### 11.1 Home: mission control

The home screen should show:

- national or regional risk summary by disease module,
- weekly changes and anomalies,
- high-confidence alerts,
- uncertain areas requiring field validation,
- task backlog and task completion,
- data freshness status,
- recent case-signal changes,
- model drift warnings,
- quick links to district reports.

The design principle: the user should know within 10 seconds where attention is needed and whether the data is fresh enough to act on.

### 11.2 Map intelligence workspace

The map should be the center of the product. It should support:

- disease module selection,
- date slider and temporal comparison,
- layer stack control,
- risk tiles,
- habitat patches,
- evidence overlays,
- population/facility exposure,
- administrative boundaries,
- field task status,
- field observations and validation points,
- uncertainty layers,
- split-view before/after imagery,
- “why here?” explanation panel.

The user should be able to click any tile or patch and see:

- risk score,
- confidence,
- trend,
- evidence layers,
- source timestamps,
- nearby exposed populations,
- data limitations,
- recommended tasks,
- previous field outcomes,
- report snippets.

### 11.3 Ontology graph

To “Palantirize” VectorOS, do not build a dashboard around loose tables. Build an ontology. The core objects should include:

- `Country`, `Admin1`, `Admin2`, `HealthFacility`, `Settlement`, `School`, `WaterPoint`, `RoadSegment`, `RiverReach`, `Catchment`, `RiskTile`, `HabitatPatch`, `DiseaseSignal`, `VectorOccurrence`, `HostOccurrence`, `FieldObservation`, `Intervention`, `OperationalTask`, `Report`, `ModelRun`, `SourceAsset`, `User`, `Organization`.

Relationships should include:

- `RiskTile overlaps Admin2`
- `RiskTile contains HabitatPatch`
- `HabitatPatch near Settlement`
- `HabitatPatch near HealthFacility`
- `HabitatPatch intersects RiverReach`
- `DiseaseSignal reported_in Admin2`
- `FieldObservation validates HabitatPatch`
- `OperationalTask assigned_to FieldTeam`
- `Report summarizes RiskTiles`
- `ModelRun produced RiskTile`
- `SourceAsset used_by ModelRun`

The ontology lets users navigate from maps to people, facilities, evidence, tasks, and reports without losing context.

### 11.4 Evidence cards

Every high-risk output should have evidence cards. Example:

```text
Evidence Card: Persistent vegetated water near settlement
Disease module: Mosquito / Anopheles
Finding: 3 candidate standing-water patches within 2 km of populated settlement
Satellite evidence: NDWI positive, NDMI elevated, Sentinel-1 wetness elevated
Climate evidence: 21-day rainfall above 80th percentile
Exposure evidence: 5,100 estimated people within 2 km; 1 health facility within 3.2 km
Limitations: no recent entomological observation; optical imagery has 7.5% cloud cover
Recommended next step: field inspection and local surveillance review
```

### 11.5 Reports

Reports should be generated from structured data and then reviewed by humans.

Report types:

- **District weekly report**: high-risk areas, changes, suggested field checks.
- **Outbreak support report**: case-signal + environmental risk context.
- **Field brief**: route, sites, evidence, field form.
- **Ministry summary**: national/provincial risk and data quality.
- **Donor/partner summary**: program progress, coverage, validation results.
- **Validation report**: model performance by district, season, and disease module.

A good report should include:

- plain-English summary,
- map snapshot,
- top priority areas,
- evidence and limitations,
- suggested operational tasks requiring approval,
- data freshness and sources,
- model version and audit trail.

### 11.6 Field validation workflow

Field validation should be a first-class product loop.

1. Model identifies high-risk or uncertain patches.
2. System drafts field tasks.
3. Supervisor approves tasks.
4. Field team receives offline-capable mobile form.
5. Field team records observation, photo, GPS, habitat type, vector/host evidence if officially collected, and intervention status.
6. Data syncs back to VectorOS.
7. Observation updates validation status and training set.
8. Model performance dashboard updates.

Field observations should support GPS fuzzing or access control where sensitive locations are involved.

### 11.7 Copilot chat interface

The copilot should be a **tool-grounded analyst**, not a free-form chatbot. It should answer only from VectorOS data, source metadata, and approved public-health knowledge bases.

Core capabilities:

- “Show me why District A is high-risk this week.”
- “Compare rainfall and habitat risk over the past six weeks.”
- “Which high-risk villages lack field validation?”
- “Draft an English weekly malaria habitat report for Admin2 X.”
- “List all Sentinel-1-confirmed wetness anomalies near schools.”
- “Which outputs are low-confidence because of cloud cover?”
- “Create field tasks for the top 10 unvalidated patches, pending supervisor approval.”
- “What data sources contributed to this score?”

Copilot safety rules:

- Do not diagnose patients.
- Do not provide treatment decisions.
- Do not provide pathogen handling, culture, or manipulation instructions.
- Do not expose personal health data.
- Do not pretend model outputs are confirmed field truth.
- Always state uncertainty and source recency for operational answers.
- Escalate sensitive operational recommendations to authorized users.

### 11.8 Data health dashboard

Public-health teams need to know whether the system is reliable today.

Show:

- last successful ingestion by source,
- cloud cover by AOI,
- missing imagery windows,
- delayed health signals,
- broken API connectors,
- label coverage,
- field validation coverage,
- model drift,
- calibration error,
- source license and sharing restrictions.

### 11.9 Admin and governance console

Enterprise/ministry deployments need:

- user and role management,
- admin-boundary permissions,
- data-source approvals,
- disease-module enable/disable controls,
- report approval workflows,
- export controls,
- audit logs,
- model version pinning,
- retention policies,
- incident review.

---

## 12. User Roles and Permissions

| Role | Capabilities | Restrictions |
|---|---|---|
| **National administrator** | Configure country deployment, data sources, roles, reports, model versions | Cannot bypass audit logs |
| **Epidemiologist** | Analyze disease signals, model outputs, reports, validation metrics | Cannot edit raw source records without permission |
| **Entomologist / malacologist / vector specialist** | Review habitat classifications, annotate field evidence, improve labels | Cannot publish ministry reports unless authorized |
| **District health officer** | View local risk, approve tasks, generate reports, track field work | Limited to assigned geography |
| **Field team lead** | Manage tasks, submit observations, review route plans | Limited data access and offline sync |
| **Field worker** | Complete assigned forms, upload observations | No broad case-data access |
| **Partner / donor viewer** | View approved summary dashboards and reports | No sensitive or unapproved data |
| **Public viewer** | Optional aggregated public risk and education maps | No sensitive operational or health data |

---

## 13. Integrations and APIs

### 13.1 Satellite and Earth-observation APIs

| API/source | Use |
|---|---|
| **DPhi SimSat** | Hackathon core imagery: Sentinel-2 and Mapbox imagery for fine-tuning/inference demo. |
| **Copernicus Data Space / Sentinel Hub / Element84 Earth Search** | Sentinel-1/Sentinel-2 production ingestion. |
| **NASA Earthdata / LP DAAC** | HLS, MODIS, VIIRS, SMAP, Landsat-adjacent data. |
| **Google Earth Engine / Microsoft Planetary Computer** | Prototyping, bulk processing, historical backfills where terms permit. |
| **NOAA / UCSB CHIRPS / NASA GPM** | Rainfall and anomalies. |
| **ECMWF CDS** | ERA5-Land climate variables. |

### 13.2 Health and surveillance APIs

| API/source | Use |
|---|---|
| **WHO GHO OData / Athena** | Global health indicators, burden, country context. |
| **PAHO Dengue/Arbo portal** | Americas dengue and arboviral signals. |
| **OpenDengue downloads/GitHub/Figshare** | Global standardized dengue case counts. |
| **DHIS2 API** | Ministry HMIS and disease surveillance integration. |
| **DHS/MIS downloads** | Survey-based validation and covariates with spatial-displacement handling. |
| **GBIF API/downloads** | Species occurrences for mosquitoes, snails, ticks, sandflies, tsetse, reservoirs. |
| **Mosquito Alert / citizen-science feeds** | User-generated mosquito observations and photos, with bias/validation flags. |

### 13.3 Exposure and operations APIs

| API/source | Use |
|---|---|
| **WorldPop** | Population exposure. |
| **GHSL** | Built-up and settlement structure. |
| **OpenStreetMap / Overpass** | Roads, waterways, buildings, amenities, water points. |
| **Healthsites.io** | Health-facility locations. |
| **Humanitarian Data Exchange (HDX)** | Boundaries, WASH, facilities, schools, crisis data where available. |
| **National data systems** | Admin boundaries, schools, water points, facilities, livestock, interventions. |

---

## 14. Frontend UX Specification

### 14.1 Core screens

1. **Mission Control**: risk overview, alerts, data freshness, task status.
2. **Map Workspace**: layer stack, risk tiles, habitat patches, evidence cards, date slider.
3. **AOI Investigation**: deep-dive into one district/tile/patch with lineage and signals.
4. **Report Builder**: generate, edit, approve, export reports.
5. **Tasking Board**: approve, assign, track field tasks.
6. **Field Validation**: submitted observations, photos, validation status.
7. **Copilot**: grounded chat with map-aware tool calls.
8. **Data Health**: ingestion status, source quality, model drift, missingness.
9. **Model & Validation**: performance, calibration, spatial/temporal holdouts.
10. **Admin/Governance**: roles, data policies, exports, audit logs.

### 14.2 Map interaction model

- Left panel: disease module, time window, layer controls.
- Center: map canvas with raster/vector overlays.
- Right panel: clicked object details, evidence, tasks, reports.
- Bottom timeline: rainfall, case signal, risk trend, imagery availability.
- Top command bar: global search and copilot prompt.

### 14.3 Visual design principles

- Risk colors should be colorblind-safe and printable.
- Uncertainty should be visually distinct from risk.
- Every generated output should have a provenance icon.
- Reports should be clean enough for ministry communication.
- Avoid visual overload: default to three active layers, with deeper evidence available on click.
- Every map screenshot in a report should include date, data source, legend, scale, and model version.

---

## 15. Deployment Architecture

### 15.1 Cloud environments

Use three environments:

- **Development**: synthetic or public open data, no sensitive partner data.
- **Staging**: realistic data with access controls, test model runs, validation.
- **Production**: ministry/partner deployment, full audit, backups, incident response.

### 15.2 Infrastructure components

```text
Cloud account
  ├── VPC / private networking
  ├── object storage buckets
  ├── Postgres + PostGIS
  ├── Redis / queue
  ├── workflow orchestrator
  ├── tile server
  ├── API service
  ├── frontend app
  ├── Modal GPU functions
  ├── observability stack
  ├── secrets manager
  └── backup/replication
```

### 15.3 Security baseline

- SSO/OIDC and MFA for privileged users.
- Role-based and attribute-based access control.
- Encryption at rest and in transit.
- Private buckets for sensitive outputs.
- Signed URLs for temporary raster access.
- Full audit log for report exports and data downloads.
- Aggregation thresholds for health data.
- Data-retention policies per deployment.
- Formal data-processing agreements for ministry data.

---

## 16. Validation and Evaluation

### 16.1 Model metrics

Use disease-module-specific metrics.

| Output | Metrics |
|---|---|
| Habitat patch detection | precision, recall, F1, IoU, false-positive habitat categories |
| Risk tile classification | AUROC, AUPRC, Brier score, calibration error, top-k hit rate |
| Change detection | precision/recall for newly emerged water/wetness anomalies |
| Report generation | schema-validity, factual-grounding score, expert review, unsafe-claim rate |
| Copilot | answer-grounding, tool-call accuracy, refusal correctness, source recency |
| Operational value | field-confirmation rate, time-to-detection, task completion, cases/context correlation |

### 16.2 Validation hierarchy

1. **Remote-sensing validation**: compare water masks, land cover, and wetness outputs against known remote-sensing products and human annotation.
2. **Ecological validation**: compare habitat suitability against vector/snail/tick/tsetse/sandfly occurrence and abundance data.
3. **Epidemiological validation**: compare risk trends against reported cases at appropriate spatial and temporal aggregation.
4. **Operational validation**: measure whether field teams confirm model-prioritized sites more often than baseline selection.
5. **Governance validation**: ensure reports are useful, understandable, and safe for public-health users.

### 16.3 Spatial and temporal bias audits

Run audits by:

- country,
- climate zone,
- rural/urban class,
- land-cover class,
- season,
- cloudiness,
- sensor availability,
- data-rich vs data-poor districts,
- disease module,
- field-validation coverage.

### 16.4 Ground-truth strategy

Do not wait for perfect labels. Use a tiered label system:

- **Tier 0**: weak labels from ecological rules and open occurrence data.
- **Tier 1**: expert remote annotation of image packets.
- **Tier 2**: field team validation of habitat/host/vector evidence.
- **Tier 3**: paired environmental + health surveillance validation.
- **Tier 4**: prospective operational trials with ministries/partners.

---

## 17. Safety, Ethics, and Policy Compliance

### 17.1 Health-data privacy

- Avoid patient-level data unless a deployment has explicit legal basis, governance, and technical safeguards.
- Prefer aggregated case signals at admin2/admin1 or facility catchment with minimum count thresholds.
- Store source-specific spatial precision and displacement metadata.
- Never reverse-engineer DHS or displaced survey coordinates.
- Protect field team identities and exact sensitive locations where required.

### 17.2 Avoiding misuse and overclaiming

VectorOS should use careful language:

- “habitat-suitable” rather than “infected.”
- “surveillance priority” rather than “confirmed outbreak.”
- “field validation recommended” rather than “intervention required.”
- “case signal increased in available reporting” rather than “cases are definitely increasing.”

### 17.3 Human approval

AI-generated reports and tasks should be drafts until approved. High-impact recommendations should be explicitly marked as requiring authorized review.

### 17.4 Community and equity considerations

- Avoid stigmatizing villages or communities.
- Provide data-quality notes so low-surveillance areas are not ignored.
- Track whether resource allocation is biased toward data-rich regions.
- Build local-language support later, but begin with clear English for quality and development speed.
- Include local public-health experts in label guidelines and model evaluation.

---

## 18. Build Plan

### 18.1 Hackathon-grade end-to-end demo

Build a focused version that proves the core thesis.

**Target demo:** mosquito habitat surveillance for one to three geographies, plus a schistosomiasis preview layer if time permits.

Minimum demo path:

1. User selects AOI and disease module.
2. App fetches DPhi Sentinel-2 and Mapbox imagery.
3. Pipeline computes NDWI, NDMI, NDVI/red-edge, simple water persistence proxy, rainfall lag from open data, and population exposure.
4. Fine-tuned or instruction-adapted LFM2.5-VL-450M analyzes image packet and emits `RiskTile` JSON.
5. App displays risk map, habitat patches, evidence cards, and an English district report.
6. Copilot answers grounded questions about the AOI.
7. Demo shows how limited-downlink/onboard triage would send only patch metadata and cropped evidence.

### 18.2 Production-grade phased roadmap

| Phase | Goal | Deliverables |
|---|---|---|
| **Phase 0: Foundations** | Data contracts, schemas, ontology, demo AOIs | RiskTile schema, STAC layout, DPhi ingestion, basic map UI |
| **Phase 1: Mosquito MVP** | Operational mosquito habitat atlas | Sentinel-2/Sentinel-1/CHIRPS/IMERG/WorldPop/OSM stack, mosquito adapter, reports, tasks |
| **Phase 2: Validation loop** | Field validation and model improvement | mobile forms, validation dashboard, active learning, expert annotation |
| **Phase 3: Schisto flagship** | Freshwater/snail/contact-site risk | hydrology, water-contact exposure, aquatic vegetation, school/village exposure |
| **Phase 4: Ministry integration** | DHIS2/HMIS and official workflows | API connectors, RBAC, audit, report approvals, deployment governance |
| **Phase 5: Multi-disease expansion** | Oncho, tsetse, leish, CCHF | disease-specific adapters, label pipelines, One Health layers |
| **Phase 6: Edge/onboard triage** | Low-bandwidth satellite intelligence | patch-selection model, compact VLM outputs, downlink simulation |
| **Phase 7: Global public-health primitive** | Open, low-cost surveillance infrastructure | country templates, open layers, partner network, validation benchmarks |

### 18.3 Team structure

- **Geospatial ML lead**: remote sensing, feature pipelines, model evaluation.
- **Public-health/domain lead**: disease modules, validation, report language.
- **Data engineer**: ingestion, lakehouse, STAC, feature store.
- **Full-stack/product engineer**: map UI, APIs, report builder, auth.
- **ML engineer**: LFM2.5-VL fine-tuning, Modal inference, model registry.
- **Field operations designer**: mobile workflows, validation forms, tasking.
- **Security/governance lead**: privacy, access control, audit, data agreements.

---

## 19. Key Risks and Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Satellite signal is indirect for some diseases | Aedes containers, sandflies, and ticks may not be visible directly | Use EO as ecological/exposure context, not sole truth; combine with case, field, and occurrence data |
| Label bias | Occurrence/case data reflect surveillance effort, not true distribution | Bias correction, uncertainty, active field validation, spatial holdouts |
| Cloud cover | Optical imagery fails during rainy periods | Sentinel-1 SAR, HLS, temporal composites, data-quality flags |
| Overclaiming | Public-health users may overtrust maps | Human approval, uncertainty, cautious language, provenance |
| Privacy | Health data and field observations may be sensitive | Aggregation, RBAC, audit, legal agreements, no patient-level defaults |
| Operational mismatch | Maps may not match field team capacity | Task prioritization with capacity, logistics, roads, deadlines |
| Model drift | Climate, urbanization, and vector adaptation change risk patterns | Drift monitoring, periodic recalibration, field-feedback loop |
| Licensing | Mapbox/commercial imagery may limit redistribution | License-aware data registry and export controls |
| Political sensitivity | Risk maps can affect tourism, trade, and local reputation | Approved reporting workflows and public/private layer separation |

---

## 20. Recommended Technical Defaults

### 20.1 Initial disease modules

1. `mosquito_anopheles_malaria`
2. `mosquito_aedes_arbovirus`
3. `schistosomiasis`

### 20.2 Initial geographies

Choose geographies with:

- strong mosquito/schisto public-health relevance,
- open health or proxy labels,
- seasonal rainfall variability,
- Sentinel-2/1 coverage,
- available population and OSM context,
- plausible field-validation partners or literature labels.

### 20.3 Initial model outputs

- `RiskTile`
- `HabitatPatch`
- `EvidenceCard`
- `OfficerReport`
- `OperationalTask`

### 20.4 Initial dashboards

- Map workspace.
- AOI investigation.
- Report builder.
- Copilot.
- Data health.
- Validation.

### 20.5 Initial engineering stack

- **Frontend**: Next.js, MapLibre GL, deck.gl, Tailwind or shadcn/ui.
- **Backend**: FastAPI, Postgres/PostGIS, Redis, object storage.
- **Geospatial**: rasterio, rioxarray, xarray, geopandas, shapely, pyproj, rio-tiler/TiTiler, STAC tooling.
- **ML**: PyTorch, Hugging Face Transformers where supported, PEFT/LoRA, MLflow/W&B, Modal GPU functions.
- **Pipelines**: Dagster or Prefect.
- **Reports**: HTML/PDF generation from structured JSON templates.
- **Observability**: OpenTelemetry, Prometheus/Grafana, Sentry.

---

## 21. Example User Stories

### 21.1 District malaria officer

“As a district malaria officer, I want to see which villages have newly emerged habitat suitability after rainfall so that I can prioritize field checks and surveillance follow-up.”

Acceptance criteria:

- displays high-risk tiles and habitat patches,
- shows rainfall lag and water/wetness evidence,
- estimates exposed population within configured buffer,
- creates supervisor-approved field tasks,
- exports weekly report.

### 21.2 Schistosomiasis program manager

“As a schistosomiasis program manager, I want to identify water-contact sites near schools and settlements with persistent aquatic vegetation so that I can prioritize snail/water-contact surveys.”

Acceptance criteria:

- maps freshwater persistence and vegetation,
- overlays schools/settlements,
- distinguishes slow/stagnant water from major fast-flowing rivers where possible,
- generates field survey tasks,
- records validation outcomes.

### 21.3 National surveillance analyst

“As a national surveillance analyst, I want to compare case signals and environmental risk across districts so that I can identify where environmental suitability is rising before reported cases increase.”

Acceptance criteria:

- time-series view for risk, rainfall, and cases,
- anomaly detection,
- report generation,
- data-quality warning when case data is delayed or coarse.

### 21.4 Field team lead

“As a field team lead, I want offline tasks with map context and simple forms so that my team can validate the highest-priority sites without needing continuous internet.”

Acceptance criteria:

- mobile/offline task list,
- map snapshot and coordinates,
- structured observation form,
- photo upload,
- sync and validation status.

---

## 22. Example Copilot Interactions

### Query: “Why is this area high-risk this week?”

Expected behavior:

1. Retrieve selected `RiskTile`.
2. Retrieve evidence cards, climate lags, imagery source timestamps, exposure estimates.
3. Produce short English explanation.
4. State limitations.
5. Offer approved next actions.

Example answer:

```text
This tile is high-risk because three evidence streams agree: recent rainfall is above the local 80th percentile, Sentinel-2/Sentinel-1 features show persistent wetness and vegetated standing-water candidates, and approximately 5,100 people are estimated within the configured 2 km exposure buffer. Confidence is moderate-high because imagery quality is good and the wetness signal is present in both optical and SAR layers. The main limitation is that no recent field validation or entomology observation is available. Recommended next step: approve a field inspection task for the two largest habitat patches.
```

### Query: “Draft a weekly report for District X.”

Expected behavior:

- generate report from `OfficerReport` template,
- cite source layers and model run IDs,
- include risk map references,
- mark as draft until approved.

---

## 23. Open Research Questions

1. How well can 10 m Sentinel-2 distinguish actionable larval habitat from irrelevant water across ecological zones?
2. How much does Sentinel-1 improve habitat detection during cloudy rainy seasons?
3. Which lags best align rainfall, soil moisture, habitat, vector abundance, and cases by disease and ecology?
4. How can presence-only occurrence data be bias-corrected for operational risk maps?
5. Can VLM-generated evidence cards improve expert trust and annotation speed compared with pure raster models?
6. Which field-validation sampling strategy maximizes model improvement under limited field capacity?
7. How should uncertainty be communicated so that users act appropriately without ignoring risk?
8. How well can onboard triage reduce downlink while preserving public-health utility?

---

## 24. Practical Hackathon Demo Script

1. Open VectorOS mission control.
2. Select `mosquito_anopheles_malaria` and a demo AOI.
3. Show DPhi Sentinel-2 and Mapbox imagery layers.
4. Toggle NDWI, NDMI, Sentinel-1 wetness, rainfall lag, and population exposure.
5. Run inference.
6. Show LFM2.5-VL structured output: risk class, habitat patch, evidence layers, uncertainty, report.
7. Click a high-risk tile and show evidence cards.
8. Ask Copilot: “Why is this high-risk?”
9. Generate a district report.
10. Create a field-validation task.
11. Show the onboard/edge slide: instead of downlinking all imagery, a compact model identifies habitat candidates and sends only metadata and cropped patches.

---

## 25. References and Links

1. Uploaded hackathon brief from the user: Liquid AI x DPhi Space hackathon notes, DPhi/SimSat imagery, tracks, judging criteria, and data guidance.
2. Liquid AI, “LFM2.5-VL-450M: Structured Visual Intelligence, Edge to Cloud”: <https://www.liquid.ai/blog/lfm2-5-vl-450m>
3. Liquid Docs, LFM2.5-VL-450M model page: <https://docs.liquid.ai/lfm/models/lfm25-vl-450m>
4. Hugging Face model card, `LiquidAI/LFM2.5-VL-450M`: <https://huggingface.co/LiquidAI/LFM2.5-VL-450M>
5. WHO, Vector-borne diseases fact sheet: <https://www.who.int/news-room/fact-sheets/detail/vector-borne-diseases>
6. WHO, Malaria fact sheet: <https://www.who.int/news-room/fact-sheets/detail/malaria>
7. WHO, Dengue and severe dengue fact sheet: <https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue>
8. WHO, Oropouche virus disease fact sheet: <https://www.who.int/news-room/fact-sheets/detail/oropouche-virus-disease>
9. WHO, Schistosomiasis fact sheet: <https://www.who.int/news-room/fact-sheets/detail/schistosomiasis>
10. WHO, Onchocerciasis fact sheet: <https://www.who.int/news-room/fact-sheets/detail/onchocerciasis>
11. WHO, Human African trypanosomiasis fact sheet: <https://www.who.int/news-room/fact-sheets/detail/trypanosomiasis-human-african-%28sleeping-sickness%29>
12. WHO, Leishmaniasis health topic: <https://www.who.int/health-topics/leishmaniasis>
13. WHO, Leishmaniasis fact sheet: <https://www.who.int/en/news-room/fact-sheets/detail/leishmaniasis>
14. WHO, Crimean-Congo haemorrhagic fever fact sheet: <https://www.who.int/en/news-room/fact-sheets/detail/crimean-congo-haemorrhagic-fever>
15. ESA, Sentinel-2 mission: <https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2>
16. ESA, Sentinel-1 mission: <https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1>
17. NASA Earthdata, Harmonized Landsat-Sentinel: <https://www.earthdata.nasa.gov/esds/harmonized-landsat-sentinel-2>
18. UCSB Climate Hazards Center, CHIRPS: <https://www.chc.ucsb.edu/data/chirps>
19. UCSB Climate Hazards Center, data sets and CHIRPS v3: <https://www.chc.ucsb.edu/data>
20. NASA GPM, IMERG: <https://gpm.nasa.gov/data/imerg>
21. ECMWF, ERA5-Land: <https://www.ecmwf.int/en/era5-land>
22. NASA Earthdata, SMAP platform: <https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/smap>
23. Google Earth Engine catalog, JRC Global Surface Water v1.4: <https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater>
24. ESA WorldCover: <https://esa-worldcover.org/en>
25. HydroSHEDS, HydroRIVERS: <https://www.hydrosheds.org/products/hydrorivers>
26. HydroSHEDS, HydroBASINS: <https://www.hydrosheds.org/products/hydrobasins>
27. SoilGrids250m paper: <https://pmc.ncbi.nlm.nih.gov/articles/PMC5313206/>
28. WorldPop: <https://www.worldpop.org/>
29. European Commission, Global Human Settlement Layer: <https://knowledge4policy.ec.europa.eu/projects-activities/ghsl-global-human-settlement-layer_en>
30. OpenStreetMap Wiki, Overpass API: <https://wiki.openstreetmap.org/wiki/Overpass_API>
31. Healthsites.io: <https://healthsites.io/>
32. WHO GHO OData API: <https://www.who.int/data/gho/info/gho-odata-api>
33. PAHO, Dengue data and analysis: <https://www.paho.org/en/arbo-portal/dengue-data-and-analysis>
34. OpenDengue: <https://opendengue.org/>
35. Clarke et al., “A global dataset of publicly available dengue case count data,” Scientific Data, 2024: <https://www.nature.com/articles/s41597-024-03120-7>
36. Malaria Atlas Project, Vector Atlas project resources: <https://malariaatlas.org/project-resources/vector-distribution-modelling-vector-atlas/>
37. DHS Program, GPS data displacement methodology: <https://www.dhsprogram.com/Methodology/GPS-Data.cfm>
38. GBIF API reference: <https://techdocs.gbif.org/en/openapi/>
39. DHIS2 disease surveillance: <https://dhis2.org/disease-surveillance/>
40. DHIS2 health platform: <https://dhis2.org/health/>
41. OGC, SpatioTemporal Asset Catalog standard: <https://www.ogc.org/standards/stac/>
42. Modal Docs, GPU acceleration: <https://modal.com/docs/reference/modal.gpu>
43. DPhi Space SimSat GitHub repository: <https://github.com/DPhi-Space/SimSat>
44. STAC specification site: <https://stacspec.org/en/>
45. GBIF occurrence download API: <https://techdocs.gbif.org/en/data-use/api-downloads>
46. NASA Earthdata, STAC convention: <https://www.earthdata.nasa.gov/esdis/esco/standards-and-practices/stac>
47. Copernicus Data Space Ecosystem, Copernicus DEM: <https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM>
48. FAO, Gridded Livestock of the World / global livestock distributions: <https://www.fao.org/livestock-systems/global-distributions/en/>

---

## Appendix A: Disease Module Configuration Template

```yaml
disease_module: mosquito_anopheles_malaria
disease_targets:
  - malaria
vector_or_host: Anopheles mosquitoes
primary_ecological_hypothesis: >
  Suitable larval habitats are associated with shallow or vegetated standing water,
  rainfall and soil-moisture lags, irrigation, wetland/riverine fringes, and proximity
  to exposed settlements.
primary_layers:
  satellite:
    - sentinel2_rgb
    - sentinel2_false_color
    - ndwi
    - mndwi
    - ndmi
    - ndvi
    - ndre
    - sentinel1_vv_vh_wetness
  climate:
    - chirps_rain_7d
    - chirps_rain_21d
    - imerg_recent_rain
    - era5_land_temperature
    - era5_land_humidity
    - smap_soil_moisture
  hydrology:
    - jrc_water_occurrence
    - hydrorivers
    - dem_slope
  exposure:
    - worldpop
    - ghsl_builtup
    - healthsites
    - osm_roads_buildings_waterways
labels:
  positive:
    - field_validated_habitat
    - entomology_observation
    - malaria_case_signal_admin2
    - vector_atlas_occurrence
  weak_positive:
    - persistent_vegetated_standing_water_near_settlement
  hard_negative:
    - deep_lake
    - fast_flowing_river
    - water_far_from_population
    - cloud_shadow_false_water
outputs:
  - RiskTile
  - HabitatPatch
  - EvidenceCard
  - OfficerReport
  - OperationalTask
safety_language:
  - habitat_suitability_not_confirmed_transmission
  - field_validation_recommended
  - public_health_authority_approval_required
```

## Appendix B: Model Evaluation Checklist

- [ ] JSON schema validity >= 99%.
- [ ] No patient-level claims.
- [ ] No clinical treatment recommendations.
- [ ] No pathogen-handling content.
- [ ] Spatial holdout performance reported.
- [ ] Temporal holdout performance reported.
- [ ] Calibration metrics reported.
- [ ] Uncertainty layer displayed.
- [ ] Source recency displayed.
- [ ] Data limitations included in reports.
- [ ] Human approval workflow enabled.
- [ ] Field validation feedback loop enabled.


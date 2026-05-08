from __future__ import annotations

import json
import os
import csv
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


def _default_workspace_root() -> Path:
    if root := os.environ.get("VECTOROS_WORKSPACE_ROOT"):
        return Path(root).expanduser().resolve()

    base_dir = Path(settings.BASE_DIR).resolve()
    dataset_names = ("vector-100k-demo", "vector-100k-smoke")
    for candidate in (base_dir, *base_dir.parents):
        for dataset_name in dataset_names:
            if (candidate / "data" / "processed" / dataset_name / "manifest.json").exists():
                return candidate
    return base_dir


WORKSPACE_ROOT = _default_workspace_root()
DATASET_ROOT = Path(
    os.environ.get("VECTOROS_DATASET_ROOT")
    or WORKSPACE_ROOT / "data" / "processed" / "vector-100k-demo"
).expanduser().resolve()
SIMSAT_API_BASE_URL = os.environ.get("SIMSAT_API_BASE_URL", "http://localhost:9005").rstrip("/")

RISK_ORDER = {"very_high": 4, "high": 3, "moderate": 2, "low": 1}


class VectorOSDataError(RuntimeError):
    pass


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_workspace_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = WORKSPACE_ROOT / path
    resolved = path.resolve()
    if not _is_relative_to(resolved, WORKSPACE_ROOT):
        raise VectorOSDataError("Path escapes the VectorOS workspace")
    return resolved


@lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    path = DATASET_ROOT / "manifest.json"
    if not path.exists():
        raise VectorOSDataError(f"VectorOS dataset manifest not found at {path}")
    return _read_json(path)


@lru_cache(maxsize=1)
def chip_index() -> list[dict[str, Any]]:
    path = DATASET_ROOT / "chip_index.json"
    if not path.exists():
        raise VectorOSDataError(f"VectorOS chip index not found at {path}")
    return _read_json(path)


@lru_cache(maxsize=1)
def chip_lookup() -> dict[str, dict[str, Any]]:
    return {item["chip_id"]: item for item in chip_index()}


def load_chip_assets(chip_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    chip = chip_lookup().get(chip_id)
    if chip is None:
        raise KeyError(chip_id)
    sidecar = _read_json(resolve_workspace_path(chip["sidecar"]))
    target = _read_json(resolve_workspace_path(chip["target"]))
    return chip, sidecar, target


def image_url_for(chip: dict[str, Any]) -> str:
    image_path = resolve_workspace_path(chip["image_packet"])
    rel = image_path.relative_to(DATASET_ROOT)
    return f"/api/vectoros/images/{rel.as_posix()}"


def dataset_file_url(raw_path: str | Path) -> str:
    file_path = resolve_workspace_path(raw_path)
    rel = file_path.relative_to(DATASET_ROOT)
    return f"/api/vectoros/images/{rel.as_posix()}"


def _bbox_polygon(bbox: list[float]) -> list[list[list[float]]]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return [
        [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]
    ]


def _point_feature(lon: float, lat: float, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def _polygon_feature(bbox: list[float], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": _bbox_polygon(bbox)},
        "properties": properties,
    }


def _clean_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if value is not None}


def _fmt_metric(value: Any, digits: int = 1, suffix: str = "") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    text = f"{number:.{digits}f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def _context_properties(
    *,
    kind: str,
    layer: str,
    source: str,
    title: str,
    summary: str,
    metrics: dict[str, Any],
    name: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "layer": layer,
        "source": source,
        "name": name or title,
        "title": title,
        "summary": summary,
        "metrics": _clean_metrics(metrics),
        **extra,
    }


def _osm_context(layer: str, tags: dict[str, Any], element: dict[str, Any]) -> dict[str, Any]:
    label = tags.get("name") or tags.get("amenity") or tags.get("highway") or tags.get("waterway") or layer
    titles = {
        "roads": "Road access context",
        "urban": "Mapped urban land-use context",
        "schools_waterpoints": "Community exposure context",
        "water": "OpenStreetMap water context",
    }
    summaries = {
        "roads": f"OSM maps {label} near this chip. Roads help reviewers understand access and settlement connectivity.",
        "urban": f"OSM maps {label} as urban or built context. This supports exposure review, not disease confirmation.",
        "schools_waterpoints": f"OSM maps {label} as a school, waterpoint, or community facility context feature.",
        "water": f"OSM maps {label} as nearby water context. Use this with CHIRPS and JRC layers before prioritizing field checks.",
    }
    return _context_properties(
        kind="osm_context",
        layer=layer,
        source="OpenStreetMap",
        title=titles.get(layer, "OpenStreetMap context"),
        name=label,
        summary=summaries.get(layer, f"OSM context feature: {label}."),
        metrics={
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "amenity": tags.get("amenity"),
            "waterway": tags.get("waterway"),
            "landuse": tags.get("landuse"),
        },
    )


def _label_context(layer: str, row: dict[str, Any]) -> dict[str, Any]:
    label = row.get("scientific_name") or row.get("species_query") or layer
    if "intermediate" in layer:
        title = "Intermediate-host weak label"
        summary = (
            f"{label} is an intermediate-host occurrence label used as schistosomiasis ecological context. "
            "It is presence-biased and does not confirm current local transmission."
        )
    elif "vector" in layer:
        title = "Vector occurrence weak label"
        summary = (
            f"{label} is a vector occurrence label used as dengue or malaria ecological context. "
            "It is presence-biased and does not confirm current local transmission."
        )
    elif "disease" in layer:
        title = "Disease occurrence weak label"
        summary = (
            f"{label} is an aggregate disease-context label. Treat it as surveillance evidence, not field confirmation."
        )
    else:
        title = "Weak label context"
        summary = f"{label} is a weak geospatial label used for surveillance context only."
    return _context_properties(
        kind="label_context",
        layer=layer,
        source="GBIF / OpenDengue / MAP",
        title=title,
        name=label,
        summary=summary,
        metrics={
            "year": row.get("year"),
            "basis": row.get("basisOfRecord") or row.get("basis_of_record"),
            "source": row.get("datasetName") or row.get("source"),
        },
    )


def _read_osm_points(path: str | Path, layer: str, limit: int = 1400) -> list[dict[str, Any]]:
    resolved = resolve_workspace_path(path)
    if not resolved.exists():
        return []
    try:
        data = _read_json(resolved)
    except Exception:
        return []
    features = []
    for element in data.get("elements", []):
        location = _osm_element_location(element)
        if location is None:
            continue
        lon, lat = location
        tags = element.get("tags", {})
        features.append(
            _point_feature(
                float(lon),
                float(lat),
                _osm_context(layer, tags, element),
            )
        )
        if len(features) >= limit:
            break
    return features


def _osm_element_location(element: dict[str, Any]) -> tuple[float, float] | None:
    center = element.get("center")
    if center and center.get("lon") is not None and center.get("lat") is not None:
        return float(center["lon"]), float(center["lat"])
    if element.get("lon") is not None and element.get("lat") is not None:
        return float(element["lon"]), float(element["lat"])
    bounds = element.get("bounds")
    if bounds:
        return (
            (float(bounds["minlon"]) + float(bounds["maxlon"])) / 2,
            (float(bounds["minlat"]) + float(bounds["maxlat"])) / 2,
        )
    geometry = element.get("geometry") or []
    lons = [float(point["lon"]) for point in geometry if point.get("lon") is not None]
    lats = [float(point["lat"]) for point in geometry if point.get("lat") is not None]
    if lons and lats:
        return sum(lons) / len(lons), sum(lats) / len(lats)
    return None


def _read_label_points(paths: list[str] | str | None, layer: str, limit: int = 1200) -> list[dict[str, Any]]:
    if paths is None:
        return []
    if isinstance(paths, str):
        paths = [paths]
    features: list[dict[str, Any]] = []
    for path in paths:
        resolved = resolve_workspace_path(path)
        if not resolved.exists() or resolved.suffix.lower() != ".csv":
            continue
        try:
            with resolved.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    lat = row.get("decimalLatitude") or row.get("latitude")
                    lon = row.get("decimalLongitude") or row.get("longitude")
                    if not lat or not lon:
                        continue
                    features.append(
                        _point_feature(
                            float(lon),
                            float(lat),
                            _label_context(layer, row),
                        )
                    )
                    if len(features) >= limit:
                        return features
        except Exception:
            continue
    return features


def aoi_map_layers(aoi_id: str, chip_id: str | None = None) -> dict[str, Any]:
    if chip_id is None:
        candidates = [item for item in chip_index() if item["aoi_id"] == aoi_id]
        if not candidates:
            raise KeyError(aoi_id)
        chip_id = sorted(
            candidates,
            key=lambda c: (RISK_ORDER.get(c.get("risk_class", "low"), 0), _safe_num(c.get("risk_score"))),
            reverse=True,
        )[0]["chip_id"]
    chip, sidecar, target = load_chip_assets(chip_id)
    aoi = target.get("aoi", {})
    bbox = aoi.get("bbox") or sidecar.get("bbox")
    center = aoi.get("centroid") or sidecar.get("center")
    source_assets = sidecar.get("source_assets", {})
    source_layers = source_assets.get("source_layers", {})
    aoi_name = aoi.get("name") or sidecar.get("name")
    features = [
        _polygon_feature(
            bbox,
            _context_properties(
                kind="aoi_boundary",
                layer="aoi",
                source="VectorOS",
                title=f"{aoi_name} AOI",
                summary="Current area of interest selected for population-level vector surveillance review.",
                metrics={
                    "disease_module": target.get("disease_module") or sidecar.get("disease_module"),
                    "chip_id": chip_id,
                },
            ),
        )
    ]

    sentinel_metadata_path = source_assets.get("sentinel_metadata")
    if sentinel_metadata_path:
        try:
            sentinel_metadata = _read_json(resolve_workspace_path(sentinel_metadata_path))
            footprint = sentinel_metadata.get("footprint") or bbox
            features.append(
                _polygon_feature(
                    footprint,
                    _context_properties(
                        kind="sentinel_footprint",
                        layer="sentinel2",
                        source=sentinel_metadata.get("source", "Sentinel-2"),
                        title="Sentinel-2 acquisition footprint",
                        name=sentinel_metadata.get("item_id") or "Sentinel-2 footprint",
                        summary=(
                            "SimSat Sentinel-2 imagery footprint used in the model evidence packet. "
                            "Cloud cover affects visual reliability."
                        ),
                        metrics={
                            "item_id": sentinel_metadata.get("item_id"),
                            "cloud_cover_percent": sentinel_metadata.get("cloud_cover"),
                            "datetime": sentinel_metadata.get("datetime"),
                        },
                    ),
                )
            )
        except Exception:
            pass

    raster = sidecar.get("numeric_features", {}).get("raster_stats", {})
    osm_counts = sidecar.get("numeric_features", {}).get("osm_counts", {})
    label_counts = sidecar.get("numeric_features", {}).get("label_counts", {})
    exposure = target.get("exposure", {})
    signals = target.get("signals", {})
    rain = raster.get("rainfall_chirps", {})
    population = raster.get("population_worldpop", {})
    rainfall_mean = rain.get("mean")
    rainfall_summary = (
        f"CHIRPS reports mean rainfall { _fmt_metric(rainfall_mean, 1, ' mm') } and p90 "
        f"{ _fmt_metric(rain.get('p90'), 1, ' mm') } across this chip."
    )
    if _safe_num(rainfall_mean) < 0:
        rainfall_summary += " Negative rainfall values usually indicate nodata contamination, so reviewers should lean on p90 and neighboring context."
    features.extend(
        [
            _point_feature(
                center["lon"],
                center["lat"],
                _context_properties(
                    kind="rainfall_signal",
                    layer="chirps",
                    source="CHIRPS",
                    title="Rainfall context",
                    summary=rainfall_summary,
                    metrics={
                        "mean_mm": rain.get("mean"),
                        "p90_mm": rain.get("p90"),
                        "median_mm": rain.get("median"),
                        "valid_pixels": rain.get("valid_pixels"),
                    },
                ),
            ),
            _point_feature(
                center["lon"],
                center["lat"],
                _context_properties(
                    kind="population_signal",
                    layer="worldpop",
                    source="WorldPop",
                    title="Population exposure",
                    summary=(
                        f"WorldPop p90 population signal is { _fmt_metric(exposure.get('population_signal_p90'), 1) }. "
                        "Higher values mean more people may be near the environmental signal if field validation confirms relevance."
                    ),
                    metrics={
                        "p90_signal": exposure.get("population_signal_p90"),
                        "mean": population.get("mean"),
                        "median": population.get("median"),
                        "valid_pixels": population.get("valid_pixels"),
                    },
                ),
            ),
            _point_feature(
                center["lon"],
                center["lat"],
                _context_properties(
                    kind="landcover_signal",
                    layer="worldcover",
                    source="ESA WorldCover",
                    title="Land-cover context",
                    summary=(
                        "ESA WorldCover and OSM built-context signals describe whether the chip is urban, rural, vegetated, or water-adjacent. "
                        "This affects habitat and exposure interpretation."
                    ),
                    metrics={
                        "urban_signal": exposure.get("urban_signal"),
                        "urban_or_building_features": exposure.get("urban_or_building_features_in_chip"),
                        "osm_urban_features": osm_counts.get("urban_landuse"),
                    },
                ),
            ),
            _point_feature(
                center["lon"],
                center["lat"],
                _context_properties(
                    kind="jrc_signal",
                    layer="jrc_water",
                    source="JRC Global Surface Water",
                    title="Surface-water context",
                    summary=(
                        f"JRC water occurrence mean is { _fmt_metric(signals.get('hydrology', {}).get('jrc_occurrence_mean_percent'), 1, '%') }. "
                        f"OSM adds {int(_safe_num(osm_counts.get('water_surface')))} mapped water surfaces and "
                        f"{int(_safe_num(osm_counts.get('waterways')))} waterways in this chip."
                    ),
                    metrics={
                        "jrc_occurrence_mean_percent": signals.get("hydrology", {}).get("jrc_occurrence_mean_percent"),
                        "seasonality_months": signals.get("hydrology", {}).get("jrc_seasonality_mean_months"),
                        "osm_water_surfaces": osm_counts.get("water_surface"),
                        "osm_waterways": osm_counts.get("waterways"),
                    },
                ),
            ),
        ]
    )

    osm_layers = source_layers.get("osm", {})
    osm_layer_map = {
        "major_roads": "roads",
        "urban_landuse": "urban",
        "schools_waterpoints": "schools_waterpoints",
        "water_surface": "water",
        "waterways": "water",
    }
    for raw_key, mapped_layer in osm_layer_map.items():
        raw_path = osm_layers.get(raw_key)
        if raw_path:
            features.extend(_read_osm_points(raw_path, mapped_layer))

    labels = source_layers.get("labels", {})
    for label_key, label_paths in labels.items():
        features.extend(_read_label_points(label_paths, label_key))

    context_patch_path = source_assets.get("context_patch_geojson")
    if context_patch_path:
        try:
            context_patch = _read_json(resolve_workspace_path(context_patch_path))
            for feature in context_patch.get("features", []):
                if feature.get("type") == "Feature" and feature.get("geometry") and feature.get("properties"):
                    features.append(feature)
        except Exception:
            pass

    risk_candidates = [
        item for item in chip_index()
        if item.get("aoi_id") == aoi_id and (not target.get("disease_module") or item.get("disease_module") == target.get("disease_module"))
    ]
    risk_candidates = sorted(
        risk_candidates,
        key=lambda c: (
            c.get("chip_id") == chip_id,
            RISK_ORDER.get(c.get("risk_class", "low"), 0),
            _safe_num(c.get("risk_score")),
            _safe_num(c.get("confidence")),
        ),
        reverse=True,
    )[:160]
    for risk_chip in risk_candidates:
        try:
            _, risk_sidecar, risk_target = load_chip_assets(risk_chip["chip_id"])
        except Exception:
            continue
        risk_aoi = risk_target.get("aoi", {})
        risk_center = risk_aoi.get("centroid") or risk_sidecar.get("center")
        if not risk_center:
            continue
        risk = risk_target.get("risk", {})
        risk_exposure = risk_target.get("exposure", {})
        rationale = risk_target.get("rationale", [])
        primary_claim = next((item.get("claim") for item in rationale if item.get("claim")), "")
        features.append(
            _point_feature(
                risk_center["lon"],
                risk_center["lat"],
                _context_properties(
                    kind="risk_tile",
                    layer="risk_tiles",
                    source="VectorOS calibrated weak-rule seed",
                    title=f"Risk tile {int(_safe_num(risk.get('score')))} / {str(risk.get('class', 'unknown')).replace('_', ' ')}",
                    name=f"{risk_chip['chip_id']} risk tile",
                    summary=primary_claim
                    or (
                        "VectorOS risk tile summarizing imagery, rainfall, water, population, OSM context, and weak labels. "
                        "Use as a prioritization cue, not field confirmation."
                    ),
                    metrics={
                        "chip_id": risk_chip["chip_id"],
                        "risk_score": risk.get("score", risk_chip.get("risk_score")),
                        "risk_class": risk.get("class", risk_chip.get("risk_class")),
                        "confidence": risk.get("confidence", risk_chip.get("confidence")),
                        "sample_type": risk_chip.get("sample_type"),
                        "label_count": risk_chip.get("label_count"),
                        "population_p90": risk_exposure.get("population_signal_p90"),
                        "waterway_features": risk_exposure.get("waterway_features_in_chip"),
                        "urban_or_building_features": risk_exposure.get("urban_or_building_features_in_chip"),
                    },
                    chip_id=risk_chip["chip_id"],
                    risk_class=risk.get("class", risk_chip.get("risk_class")),
                    risk_score=risk.get("score", risk_chip.get("risk_score")),
                    selected=risk_chip["chip_id"] == chip_id,
                ),
            )
        )

    overlays = []
    if source_assets.get("mapbox_satellite"):
        overlays.append(
            {
                "id": "mapbox_satellite",
                "label": "Mapbox satellite crop",
                "layer": "Mapbox",
                "url": dataset_file_url(source_assets["mapbox_satellite"]),
                "bbox": bbox,
                "opacity": 0.94,
            }
        )

    return {
        "aoi_id": aoi_id,
        "chip_id": chip_id,
        "name": aoi.get("name") or sidecar.get("name"),
        "bbox": bbox,
        "center": center,
        "image_overlays": overlays,
        "feature_collection": {"type": "FeatureCollection", "features": features},
        "feature_counts": dict(Counter(feature["properties"].get("layer", "unknown") for feature in features)),
    }


def _risk_distribution(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(item["risk_class"] for item in items)
    return {risk: counts.get(risk, 0) for risk in ("low", "moderate", "high", "very_high")}


def _safe_num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _aoi_sort_key(item: tuple[str, list[dict[str, Any]]]) -> tuple[int, str]:
    _, items = item
    max_risk = max((RISK_ORDER.get(chip.get("risk_class", "low"), 0) for chip in items), default=0)
    avg_score = mean(_safe_num(chip.get("risk_score")) for chip in items)
    return (-max_risk, f"{-avg_score:08.3f}")


@lru_cache(maxsize=1)
def aoi_summaries() -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chip in chip_index():
        grouped[chip["aoi_id"]].append(chip)

    summaries: list[dict[str, Any]] = []
    for aoi_id, items in sorted(grouped.items(), key=_aoi_sort_key):
        representative = sorted(
            items,
            key=lambda c: (RISK_ORDER.get(c.get("risk_class", "low"), 0), _safe_num(c.get("risk_score"))),
            reverse=True,
        )[0]
        _, sidecar, target = load_chip_assets(representative["chip_id"])
        aoi = target.get("aoi", {})
        scores = [_safe_num(item.get("risk_score")) for item in items]
        labels = [int(_safe_num(item.get("label_count"))) for item in items]
        summaries.append(
            {
                "aoi_id": aoi_id,
                "name": aoi.get("name") or sidecar.get("name") or aoi_id.replace("_", " ").title(),
                "country": aoi.get("admin0") or sidecar.get("country"),
                "disease_module": representative["disease_module"],
                "primary_disease": sidecar.get("primary_disease"),
                "chip_count": len(items),
                "split_counts": dict(Counter(item["split"] for item in items)),
                "sample_type_counts": dict(Counter(item["sample_type"] for item in items)),
                "risk_class_counts": _risk_distribution(items),
                "risk_score_mean": round(mean(scores), 2) if scores else 0,
                "risk_score_max": max(scores) if scores else 0,
                "label_count_total": sum(labels),
                "center": aoi.get("centroid") or sidecar.get("center"),
                "bbox": aoi.get("bbox") or sidecar.get("bbox"),
                "representative_chip_id": representative["chip_id"],
                "representative_image_url": image_url_for(representative),
            }
        )
    return summaries


def product_summary() -> dict[str, Any]:
    data_manifest = manifest()
    counts = data_manifest.get("counts", {})
    aois = aoi_summaries()
    return {
        "product": "VectorOS",
        "mode": "open_demo_live_model_inference",
        "model": {
            "base": "LiquidAI/LFM2.5-VL-450M",
            "fine_tuned": "Alfaxad/Vector-LFM2.5-VL-450M",
            "runtime": os.environ.get("VECTOROS_INFERENCE_MODE", "local_transformers"),
            "zero_cost_inference_note": (
                "The product path uses local Transformers live inference first, with browser WebGPU/ONNX "
                "planned as the zero-cost public scaling path."
            ),
        },
        "dataset": {
            "dataset_id": data_manifest.get("dataset_id"),
            "schema_version": data_manifest.get("schema_version"),
            "created_at": data_manifest.get("created_at"),
            "chips": counts.get("chips"),
            "examples_total": counts.get("examples_total"),
            "examples_by_split": counts.get("examples_by_split"),
            "examples_by_task": counts.get("examples_by_task"),
            "risk_class_counts": counts.get("risk_class_counts"),
            "module_chip_counts": counts.get("module_chip_counts"),
            "aoi_count": len(aois),
        },
        "safety_scope": {
            "surveillance_only": True,
            "no_individual_diagnosis": True,
            "no_treatment_guidance": True,
            "human_review_required_for_field_action": True,
        },
    }


def filter_aois(module: str | None = None) -> list[dict[str, Any]]:
    items = aoi_summaries()
    if module:
        items = [item for item in items if item["disease_module"] == module]
    return items


def list_risk_tiles(
    *,
    aoi_id: str | None = None,
    module: str | None = None,
    risk_class: str | None = None,
    sample_type: str | None = None,
    split: str | None = None,
    limit: int = 120,
    offset: int = 0,
) -> dict[str, Any]:
    items = chip_index()
    if aoi_id:
        items = [item for item in items if item["aoi_id"] == aoi_id]
    if module:
        items = [item for item in items if item["disease_module"] == module]
    if risk_class and risk_class != "all":
        items = [item for item in items if item["risk_class"] == risk_class]
    if sample_type and sample_type != "all":
        items = [item for item in items if item["sample_type"] == sample_type]
    if split and split != "all":
        items = [item for item in items if item["split"] == split]

    items = sorted(
        items,
        key=lambda c: (
            RISK_ORDER.get(c.get("risk_class", "low"), 0),
            _safe_num(c.get("risk_score")),
            _safe_num(c.get("confidence")),
        ),
        reverse=True,
    )
    total = len(items)
    page = items[max(offset, 0) : max(offset, 0) + max(min(limit, 500), 1)]
    tiles = []
    for chip in page:
        _, sidecar, target = load_chip_assets(chip["chip_id"])
        aoi = target.get("aoi", {})
        exposure = target.get("exposure", {})
        risk = target.get("risk", {})
        tiles.append(
            {
                "chip_id": chip["chip_id"],
                "aoi_id": chip["aoi_id"],
                "disease_module": chip["disease_module"],
                "sample_type": chip["sample_type"],
                "split": chip["split"],
                "risk": {
                    "score": risk.get("score", chip.get("risk_score")),
                    "class": risk.get("class", chip.get("risk_class")),
                    "confidence": risk.get("confidence", chip.get("confidence")),
                    "uncertainty_interval": risk.get("uncertainty_interval"),
                },
                "label_count": chip.get("label_count"),
                "center": aoi.get("centroid") or sidecar.get("center"),
                "bbox": aoi.get("bbox") or sidecar.get("bbox"),
                "image_url": image_url_for(chip),
                "exposure": exposure,
                "quality": {
                    "sentinel_cloud_cover_percent": chip.get("sentinel_cloud_cover_percent"),
                    "mapbox_available": chip.get("mapbox_available"),
                    "sentinel_available": sidecar.get("quality", {}).get("sentinel_available"),
                },
            }
        )
    return {"total": total, "limit": limit, "offset": offset, "tiles": tiles}


def risk_tile_detail(chip_id: str) -> dict[str, Any]:
    chip, sidecar, target = load_chip_assets(chip_id)
    related = [
        item["chip_id"]
        for item in chip_index()
        if item["aoi_id"] == chip["aoi_id"] and item["chip_id"] != chip_id
    ][:8]
    return {
        "chip": chip,
        "image_url": image_url_for(chip),
        "sidecar": sidecar,
        "target": target,
        "evidence_cards": build_evidence_cards(sidecar, target),
        "report": build_report(target, sidecar),
        "field_task": build_field_task(target, sidecar),
        "related_chip_ids": related,
    }


def build_evidence_cards(sidecar: dict[str, Any], target: dict[str, Any]) -> list[dict[str, Any]]:
    numeric = sidecar.get("numeric_features", {})
    raster = numeric.get("raster_stats", {})
    osm = numeric.get("osm_counts", {})
    labels = numeric.get("label_counts", {})
    exposure = target.get("exposure", {})
    signals = target.get("signals", {})
    return [
        {
            "title": "Imagery Packet",
            "kind": "SimSat + Mapbox",
            "status": "available" if sidecar.get("quality", {}).get("evidence_packet_available") else "partial",
            "body": "Sentinel-2 RGB, Sentinel-2 NIR false color, Mapbox satellite context, and aligned evidence overlay.",
            "metrics": {
                "cloud_cover_percent": sidecar.get("quality", {}).get("sentinel_cloud_cover_percent"),
                "sentinel_datetime": sidecar.get("quality", {}).get("sentinel_datetime"),
                "mapbox_available": sidecar.get("quality", {}).get("mapbox_available"),
            },
        },
        {
            "title": "Climate And Water",
            "kind": "CHIRPS + JRC GSW",
            "status": "observed",
            "body": "Rainfall and surface-water recurrence are used as ecological context, not as disease confirmation.",
            "metrics": {
                "rainfall_mean_mm": raster.get("rainfall_chirps", {}).get("mean"),
                "rainfall_p90_mm": raster.get("rainfall_chirps", {}).get("p90"),
                "jrc_occurrence_mean_percent": signals.get("hydrology", {}).get("jrc_occurrence_mean_percent"),
                "jrc_seasonality_months": signals.get("hydrology", {}).get("jrc_seasonality_mean_months"),
            },
        },
        {
            "title": "Exposure",
            "kind": "WorldPop + OSM",
            "status": "observed",
            "body": "Population and nearby facilities/sites are summarized to prioritize review and field validation.",
            "metrics": {
                "population_signal_p90": exposure.get("population_signal_p90"),
                "health_facilities": exposure.get("health_facilities_in_chip") or osm.get("health_facilities"),
                "schools_or_waterpoints": exposure.get("schools_or_waterpoints_in_chip") or osm.get("schools_waterpoints"),
                "waterway_features": exposure.get("waterway_features_in_chip") or osm.get("waterways"),
            },
        },
        {
            "title": "Weak Labels",
            "kind": "GBIF / OpenDengue / MAP",
            "status": "presence-biased",
            "body": "Labels are training and surveillance context only. They do not prove current local transmission or absence.",
            "metrics": {
                "vector_labels": labels.get("vector_label"),
                "disease_labels": labels.get("disease_label"),
                "intermediate_host_labels": labels.get("intermediate_host_label"),
                "label_source": target.get("signals", {}).get("entomology_or_host", {}).get("source"),
            },
        },
    ]


def build_report(target: dict[str, Any], sidecar: dict[str, Any]) -> dict[str, Any]:
    risk = target.get("risk", {})
    aoi = target.get("aoi", {})
    actions = target.get("recommended_actions", [])
    limitations = target.get("limitations", [])
    rationale = target.get("rationale", [])
    name = aoi.get("name") or sidecar.get("name")
    module = target.get("disease_module", sidecar.get("disease_module"))
    summary = (
        f"{name} is currently classified as {risk.get('class')} environmental surveillance priority "
        f"for {module}, with score {risk.get('score')} and confidence {risk.get('confidence')}. "
        "This reflects geospatial habitat, exposure, and weak-label evidence, not field-confirmed disease presence."
    )
    return {
        "title": f"VectorOS Surveillance Brief: {name}",
        "summary": summary,
        "key_findings": [item.get("claim") for item in rationale if item.get("claim")],
        "recommended_actions": actions,
        "limitations": limitations,
        "audit": target.get("audit", {}),
        "generated_from": "VectorOS evidence packet, sidecar context, and fine-tuning target schema",
    }


def build_field_task(target: dict[str, Any], sidecar: dict[str, Any]) -> dict[str, Any]:
    risk = target.get("risk", {})
    aoi = target.get("aoi", {})
    exposure = target.get("exposure", {})
    module = target.get("disease_module", sidecar.get("disease_module"))
    priority = "normal"
    if risk.get("class") in {"high", "very_high"}:
        priority = "urgent"
    elif risk.get("class") == "moderate":
        priority = "elevated"
    return {
        "task_id": f"task-{target.get('risk_tile_id')}",
        "title": f"Review {module} evidence in {aoi.get('name') or sidecar.get('name')}",
        "priority": priority,
        "requires_human_approval": True,
        "geometry": {"bbox": aoi.get("bbox"), "center": aoi.get("centroid")},
        "checklist": [
            "Review surface-water and rainfall context against local field knowledge.",
            "Check whether exposed schools, waterpoints, facilities, or settlements need outreach.",
            "Record field validation outcome as present, absent, inaccessible, or uncertain.",
        ],
        "context": {
            "risk_class": risk.get("class"),
            "risk_score": risk.get("score"),
            "health_facilities": exposure.get("health_facilities_in_chip"),
            "schools_or_waterpoints": exposure.get("schools_or_waterpoints_in_chip"),
        },
    }


def connector_status() -> dict[str, Any]:
    data_manifest = manifest()
    env = {
        "mapbox_token": bool(os.environ.get("MAPBOX_ACCESS_TOKEN")),
        "healthsites_key": bool(os.environ.get("HEALTHSITES_API_KEY")),
        "simsat_api_base_url": SIMSAT_API_BASE_URL,
    }
    return {
        "mode": os.environ.get("VECTOROS_CONNECTOR_MODE", "local_cache_plus_optional_live"),
        "secrets": {
            "mapbox_server_side_configured": env["mapbox_token"],
            "healthsites_server_side_configured": env["healthsites_key"],
        },
        "sources": [
            {
                "id": "simsat_sentinel2",
                "name": "SimSat Sentinel-2",
                "status": "cached_and_live_optional",
                "live_endpoint": f"{SIMSAT_API_BASE_URL}/data/image/sentinel",
                "role": "core multispectral imagery",
            },
            {
                "id": "simsat_mapbox",
                "name": "SimSat Mapbox satellite",
                "status": "cached_and_live_optional" if env["mapbox_token"] else "cached_only_missing_server_token",
                "live_endpoint": f"{SIMSAT_API_BASE_URL}/data/image/mapbox",
                "role": "high-resolution visual context",
            },
            {
                "id": "chirps",
                "name": "CHIRPS rainfall",
                "status": "local_aoi_cache",
                "role": "rainfall and lag context",
            },
            {
                "id": "jrc_gsw",
                "name": "JRC Global Surface Water",
                "status": "local_aoi_cache",
                "role": "water occurrence and seasonality",
            },
            {
                "id": "esa_worldcover",
                "name": "ESA WorldCover",
                "status": "local_aoi_cache",
                "role": "10 m land cover",
            },
            {
                "id": "worldpop",
                "name": "WorldPop",
                "status": "local_aoi_cache",
                "role": "population exposure",
            },
            {
                "id": "osm_overpass",
                "name": "OpenStreetMap / Overpass",
                "status": "local_aoi_cache_live_optional",
                "role": "roads, waterways, facilities, schools, urban features",
            },
            {
                "id": "healthsites",
                "name": "Healthsites.io",
                "status": "live_optional" if env["healthsites_key"] else "local_osm_facility_cache_only",
                "role": "health facility reference layer",
            },
            {
                "id": "labels",
                "name": "OpenDengue / MAP / GBIF",
                "status": "local_aoi_cache",
                "role": "weak disease, vector, and intermediate-host label context",
            },
        ],
        "public_release_flags": data_manifest.get("public_release_flags", {}),
    }


def _query_json(url: str, timeout: float = 8.0) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "VectorOS-demo/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_healthsites_bbox(bbox: list[float]) -> dict[str, Any]:
    api_key = os.environ.get("HEALTHSITES_API_KEY")
    if not api_key:
        return {
            "status": "missing_api_key",
            "features": [],
            "message": "Healthsites live lookup is disabled until HEALTHSITES_API_KEY is configured server-side.",
        }
    params = urlencode(
        {
            "api-key": api_key,
            "page": 1,
            "extent": ",".join(str(value) for value in bbox),
            "output": "json",
        }
    )
    url = f"https://healthsites.io/api/v3/facilities/?{params}"
    try:
        data = _query_json(url)
    except Exception as exc:  # pragma: no cover - live connector can fail independently
        return {"status": "error", "features": [], "message": str(exc)}
    features = data.get("features") if isinstance(data, dict) else []
    return {
        "status": "ok",
        "feature_count": len(features or []),
        "features": (features or [])[:100],
    }


def copilot_answer(chip_id: str | None, question: str) -> dict[str, Any]:
    if chip_id and chip_id in chip_lookup():
        _, sidecar, target = load_chip_assets(chip_id)
    else:
        first = chip_index()[0]
        _, sidecar, target = load_chip_assets(first["chip_id"])

    report = build_report(target, sidecar)
    risk = target.get("risk", {})
    aoi = target.get("aoi", {})
    question_lower = question.lower()
    if any(token in question_lower for token in ("why", "reason", "evidence")):
        answer = " ".join(report["key_findings"][:3])
    elif any(token in question_lower for token in ("action", "task", "do next", "recommend")):
        actions = target.get("recommended_actions", [])
        answer = " ".join(action.get("description", "") for action in actions[:3]).strip()
    else:
        answer = report["summary"]
    if not answer:
        answer = report["summary"]
    return {
        "answer": answer,
        "scope": "population-level surveillance intelligence only",
        "selected_tile": {
            "chip_id": target.get("risk_tile_id"),
            "aoi": aoi.get("name"),
            "risk_class": risk.get("class"),
            "risk_score": risk.get("score"),
        },
        "citations": [
            "SimSat Sentinel-2 and Mapbox packet",
            "CHIRPS, JRC GSW, ESA WorldCover, WorldPop, OSM, Healthsites/labels where available",
            "VectorOS evidence schema and live Vector-LFM2.5-VL target format",
        ],
        "safety_note": "VectorOS does not diagnose individuals, confirm local transmission, or provide clinical guidance.",
    }


def zero_cost_inference_options() -> list[dict[str, str]]:
    return [
        {
            "path": "Local Django inference worker",
            "runtime": "local_transformers",
            "fit": "first live zero-external-GPU path",
            "notes": "Loads Alfaxad/Vector-LFM2.5-VL-450M from Hugging Face with Transformers and runs real generation on CUDA, MPS, or CPU.",
        },
        {
            "path": "Liquid ONNX / WebGPU",
            "runtime": "browser or edge ONNX/WebGPU export",
            "fit": "long-term free public demo path",
            "notes": "The merged fine-tuned model must be exported, quantized, and validated with its image-token preprocessing before this becomes the default.",
        },
        {
            "path": "Ollama / llama.cpp / GGUF",
            "runtime": "local quantized model",
            "fit": "experimental bring-your-own local inference",
            "notes": "Only useful if the fine-tuned multimodal model converts cleanly and preserves image conditioning.",
        },
        {
            "path": "Liquid LEAP / Edge SDK",
            "runtime": "edge deployment toolchain",
            "fit": "mobile/edge partner deployment",
            "notes": "Promising for optimized deployment, but it still needs validation against the merged VectorOS model.",
        },
    ]

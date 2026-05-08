#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


RISK_ORDER = {"very_high": 4, "high": 3, "moderate": 2, "low": 1}
OSM_LAYER_MAP = {
    "urban_landuse": "urban",
    "schools_waterpoints": "schools_waterpoints",
    "water_surface": "water",
    "waterways": "water",
}
CONTEXT_LIMITS = {
    "urban": 350,
    "schools_waterpoints": 250,
    "water": 600,
    "label_context": 700,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def path_under(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def rewrite_paths(value: Any, source_name: str, target_name: str) -> Any:
    if isinstance(value, dict):
        return {key: rewrite_paths(item, source_name, target_name) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_paths(item, source_name, target_name) for item in value]
    if isinstance(value, str):
        return value.replace(f"data/processed/{source_name}/", f"data/processed/{target_name}/")
    return value


def iter_string_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            paths.extend(iter_string_paths(item))
    elif isinstance(value, list):
        for item in value:
            paths.extend(iter_string_paths(item))
    elif isinstance(value, str) and value.startswith("data/"):
        paths.append(value)
    return paths


def bbox_contains(bbox: list[float], lon: float, lat: float) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def bbox_intersects(a: list[float], b: list[float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def element_bbox(element: dict[str, Any]) -> list[float] | None:
    bounds = element.get("bounds")
    if bounds:
        return [
            float(bounds["minlon"]),
            float(bounds["minlat"]),
            float(bounds["maxlon"]),
            float(bounds["maxlat"]),
        ]
    geometry = element.get("geometry") or []
    if geometry:
        lons = [float(point["lon"]) for point in geometry if point.get("lon") is not None]
        lats = [float(point["lat"]) for point in geometry if point.get("lat") is not None]
        if lons and lats:
            return [min(lons), min(lats), max(lons), max(lats)]
    if element.get("lon") is not None and element.get("lat") is not None:
        lon = float(element["lon"])
        lat = float(element["lat"])
        return [lon, lat, lon, lat]
    if element.get("center"):
        lon = float(element["center"]["lon"])
        lat = float(element["center"]["lat"])
        return [lon, lat, lon, lat]
    return None


def element_center(element: dict[str, Any]) -> tuple[float, float] | None:
    center = element.get("center")
    if center and center.get("lon") is not None and center.get("lat") is not None:
        return float(center["lon"]), float(center["lat"])
    if element.get("lon") is not None and element.get("lat") is not None:
        return float(element["lon"]), float(element["lat"])
    bounds = element_bbox(element)
    if bounds:
        return (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
    return None


def clean_metric(value: Any) -> Any:
    if value in ("", None):
        return None
    return value


def context_properties(
    *,
    kind: str,
    layer: str,
    source: str,
    title: str,
    summary: str,
    metrics: dict[str, Any],
    name: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "layer": layer,
        "source": source,
        "name": name or title,
        "title": title,
        "summary": summary,
        "metrics": {key: value for key, value in metrics.items() if clean_metric(value) is not None},
    }


def osm_context(layer: str, element: dict[str, Any]) -> dict[str, Any]:
    tags = element.get("tags") or {}
    label = tags.get("name") or tags.get("amenity") or tags.get("highway") or tags.get("waterway") or tags.get("landuse") or layer
    titles = {
        "urban": "Mapped urban land-use context",
        "schools_waterpoints": "Community exposure context",
        "water": "OpenStreetMap water context",
    }
    summaries = {
        "urban": f"OSM maps {label} as built or urban context inside this selected chip.",
        "schools_waterpoints": f"OSM maps {label} as school, waterpoint, or community exposure context inside this selected chip.",
        "water": f"OSM maps {label} as water context inside this selected chip. Use with CHIRPS and JRC before prioritizing review.",
    }
    return context_properties(
        kind="osm_context",
        layer=layer,
        source="OpenStreetMap",
        title=titles.get(layer, "OpenStreetMap context"),
        name=str(label),
        summary=summaries.get(layer, f"OSM context feature: {label}."),
        metrics={
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "amenity": tags.get("amenity"),
            "waterway": tags.get("waterway"),
            "landuse": tags.get("landuse"),
            "highway": tags.get("highway"),
            "natural": tags.get("natural"),
        },
    )


def label_context(layer: str, row: dict[str, Any]) -> dict[str, Any]:
    label = row.get("scientificName") or row.get("scientific_name") or row.get("species") or row.get("species_query") or layer
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
        summary = f"{label} is an aggregate disease-context label. Treat it as surveillance evidence, not field confirmation."
    else:
        title = "Weak label context"
        summary = f"{label} is a weak geospatial label used for surveillance context only."
    return context_properties(
        kind="label_context",
        layer=layer,
        source="GBIF / OpenDengue / MAP",
        title=title,
        name=str(label),
        summary=summary,
        metrics={
            "year": row.get("year"),
            "basis": row.get("basisOfRecord") or row.get("basis_of_record"),
            "source": row.get("datasetName") or row.get("source") or row.get("datasetKey"),
            "license": row.get("license"),
        },
    )


def copy_file(source_workspace: Path, target_workspace: Path, raw_path: str, *, source_name: str, target_name: str) -> str:
    mapped = raw_path.replace(f"data/processed/{source_name}/", f"data/processed/{target_name}/")
    src = path_under(source_workspace, raw_path)
    dst = path_under(target_workspace, mapped)
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return mapped


def copy_tree(source_workspace: Path, target_workspace: Path, raw_path: str, *, source_name: str, target_name: str) -> str:
    mapped = raw_path.replace(f"data/processed/{source_name}/", f"data/processed/{target_name}/")
    src = path_under(source_workspace, raw_path)
    dst = path_under(target_workspace, mapped)
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    return mapped


def add_feature(
    patches: dict[str, list[dict[str, Any]]],
    counts: dict[tuple[str, str], int],
    chip_id: str,
    feature: dict[str, Any],
    limit_key: str,
) -> None:
    key = (chip_id, limit_key)
    if counts.get(key, 0) >= CONTEXT_LIMITS.get(limit_key, 500):
        return
    patches[chip_id].append(feature)
    counts[key] = counts.get(key, 0) + 1


def build_context_patches(
    *,
    source_workspace: Path,
    selected_specs: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    patches: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts: dict[tuple[str, str], int] = {}
    osm_tasks: dict[str, list[tuple[str, list[float], str]]] = defaultdict(list)
    label_tasks: dict[str, list[tuple[str, list[float], str]]] = defaultdict(list)

    for chip_id, spec in selected_specs.items():
        sidecar = spec["sidecar"]
        bbox = sidecar.get("bbox") or spec["target"].get("aoi", {}).get("bbox")
        if not bbox:
            continue
        source_layers = sidecar.get("source_assets", {}).get("source_layers", {})
        for raw_key, layer in OSM_LAYER_MAP.items():
            raw_path = source_layers.get("osm", {}).get(raw_key)
            if raw_path:
                osm_tasks[raw_path].append((chip_id, bbox, layer))
        for label_key, raw_paths in source_layers.get("labels", {}).items():
            if isinstance(raw_paths, str):
                raw_paths = [raw_paths]
            for raw_path in raw_paths or []:
                label_tasks[raw_path].append((chip_id, bbox, label_key))

    parsed_files = 0
    for raw_path, tasks in sorted(osm_tasks.items()):
        src = path_under(source_workspace, raw_path)
        if not src.exists():
            continue
        try:
            data = read_json(src)
        except Exception:
            continue
        parsed_files += 1
        for element in data.get("elements", []):
            bbox = element_bbox(element)
            center = element_center(element)
            if not bbox or not center:
                continue
            lon, lat = center
            for chip_id, chip_bbox, layer in tasks:
                if counts.get((chip_id, layer), 0) >= CONTEXT_LIMITS.get(layer, 500):
                    continue
                if not (bbox_intersects(bbox, chip_bbox) or bbox_contains(chip_bbox, lon, lat)):
                    continue
                add_feature(
                    patches,
                    counts,
                    chip_id,
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": osm_context(layer, element),
                    },
                    layer,
                )

    for raw_path, tasks in sorted(label_tasks.items()):
        src = path_under(source_workspace, raw_path)
        if not src.exists() or src.suffix.lower() != ".csv":
            continue
        parsed_files += 1
        try:
            with src.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    lat = row.get("decimalLatitude") or row.get("latitude")
                    lon = row.get("decimalLongitude") or row.get("longitude")
                    if not lat or not lon:
                        continue
                    try:
                        lon_f = float(lon)
                        lat_f = float(lat)
                    except ValueError:
                        continue
                    for chip_id, chip_bbox, layer in tasks:
                        if counts.get((chip_id, "label_context"), 0) >= CONTEXT_LIMITS["label_context"]:
                            continue
                        if not bbox_contains(chip_bbox, lon_f, lat_f):
                            continue
                        add_feature(
                            patches,
                            counts,
                            chip_id,
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
                                "properties": label_context(layer, row),
                            },
                            "label_context",
                        )
        except Exception:
            continue

    return patches, parsed_files


def choose_chips(chips: list[dict[str, Any]], per_aoi: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chip in chips:
        grouped[chip["aoi_id"]].append(chip)

    selected: list[dict[str, Any]] = []
    for aoi_id in sorted(grouped):
        items = grouped[aoi_id]
        picks: list[dict[str, Any]] = []

        def add_best(candidates: list[dict[str, Any]], reverse: bool = True) -> None:
            candidates = [item for item in candidates if item["chip_id"] not in {p["chip_id"] for p in picks}]
            if not candidates:
                return
            picks.append(
                sorted(
                    candidates,
                    key=lambda item: (
                        RISK_ORDER.get(str(item.get("risk_class", "low")), 0),
                        float(item.get("risk_score") or 0),
                        float(item.get("confidence") or 0),
                        int(item.get("label_count") or 0),
                    ),
                    reverse=reverse,
                )[0]
            )

        add_best(items, reverse=True)
        add_best([item for item in items if "label_positive" in str(item.get("sample_type", ""))], reverse=True)
        add_best(
            [
                item
                for item in items
                if any(token in str(item.get("sample_type", "")) for token in ("hard_negative", "random_ecological", "uncertain"))
            ],
            reverse=False,
        )

        for sample_type in sorted({str(item.get("sample_type", "")) for item in items}):
            if len(picks) >= per_aoi:
                break
            add_best([item for item in items if item.get("sample_type") == sample_type], reverse=True)

        if len(picks) < per_aoi:
            for item in sorted(items, key=lambda x: x["chip_id"]):
                if len(picks) >= per_aoi:
                    break
                if item["chip_id"] not in {p["chip_id"] for p in picks}:
                    picks.append(item)

        selected.extend(picks[:per_aoi])
    return selected


def filter_records(source_file: Path, target_file: Path, selected_ids: set[str], source_name: str, target_name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not source_file.exists():
        target_file.write_text("", encoding="utf-8")
        return records
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with source_file.open("r", encoding="utf-8") as src, target_file.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("chip_id") not in selected_ids:
                continue
            record = rewrite_paths(record, source_name, target_name)
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")
            records.append(record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compact all-AOI VectorOS demo dataset.")
    parser.add_argument("--source", default="../data/processed/vector-100k", help="Full VectorOS dataset root.")
    parser.add_argument("--target", default="data/processed/vector-100k-demo", help="Demo dataset root.")
    parser.add_argument("--per-aoi", type=int, default=3, help="Number of chips to bundle for each AOI.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    source_root = Path(args.source).expanduser().resolve()
    target_root = Path(args.target).expanduser().resolve()
    source_name = source_root.name
    target_name = target_root.name
    source_workspace = source_root.parents[2]
    target_workspace = repo_root

    if not (source_root / "chip_index.json").exists():
        raise SystemExit(f"Missing source chip index: {source_root / 'chip_index.json'}")

    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    chips = read_json(source_root / "chip_index.json")
    selected = choose_chips(chips, args.per_aoi)
    selected_ids = {chip["chip_id"] for chip in selected}

    selected_specs: dict[str, dict[str, Any]] = {}
    rewritten_chips: list[dict[str, Any]] = []
    for chip in selected:
        chip = rewrite_paths(chip, source_name, target_name)
        original_sidecar = read_json(path_under(source_workspace, chip["sidecar"].replace(target_name, source_name)))
        original_target = read_json(path_under(source_workspace, chip["target"].replace(target_name, source_name)))

        copy_file(source_workspace, target_workspace, chip["image_packet"].replace(target_name, source_name), source_name=source_name, target_name=target_name)
        copy_file(source_workspace, target_workspace, chip["target"].replace(target_name, source_name), source_name=source_name, target_name=target_name)

        source_assets = original_sidecar.get("source_assets", {})
        if source_assets.get("simsat_raw_dir"):
            copy_tree(
                source_workspace,
                target_workspace,
                source_assets["simsat_raw_dir"],
                source_name=source_name,
                target_name=target_name,
            )

        sidecar = rewrite_paths(original_sidecar, source_name, target_name)
        sidecar.setdefault("source_assets", {})["context_patch_geojson"] = (
            f"data/processed/{target_name}/context_patches/{chip['aoi_id']}/{chip['chip_id']}_context.geojson"
        )
        target = rewrite_paths(original_target, source_name, target_name)
        write_json(path_under(target_workspace, chip["sidecar"]), sidecar)
        write_json(path_under(target_workspace, chip["target"]), target)
        selected_specs[chip["chip_id"]] = {
            "chip": chip,
            "sidecar": original_sidecar,
            "target": original_target,
        }
        rewritten_chips.append(chip)

    context_patches, parsed_context_files = build_context_patches(
        source_workspace=source_workspace,
        selected_specs=selected_specs,
    )
    for chip in rewritten_chips:
        patch_path = target_root / "context_patches" / chip["aoi_id"] / f"{chip['chip_id']}_context.geojson"
        features = context_patches.get(chip["chip_id"], [])
        write_json(
            patch_path,
            {
                "type": "FeatureCollection",
                "metadata": {
                    "chip_id": chip["chip_id"],
                    "aoi_id": chip["aoi_id"],
                    "source": "compacted OSM and weak-label context from VectorOS source AOI files",
                    "feature_counts": dict(Counter(feature["properties"].get("layer", "unknown") for feature in features)),
                },
                "features": features,
            },
        )

    rewritten_chips.sort(key=lambda item: (item["disease_module"], item["aoi_id"], item["chip_id"]))
    write_json(target_root / "chip_index.json", rewritten_chips)

    with (target_root / "chip_index.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(rewritten_chips[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rewritten_chips)

    for schema in (source_root / "schemas").glob("*"):
        if schema.is_file():
            copy_file(source_workspace, target_workspace, str(schema.relative_to(source_workspace)), source_name=source_name, target_name=target_name)

    records_by_split: dict[str, list[dict[str, Any]]] = {}
    for name in ("train", "validation", "test", "all_examples"):
        records_by_split[name] = filter_records(
            source_root / f"{name}.jsonl",
            target_root / f"{name}.jsonl",
            selected_ids,
            source_name,
            target_name,
        )

    all_records = records_by_split["all_examples"] or [
        item for split_name, records in records_by_split.items() if split_name != "all_examples" for item in records
    ]
    counts_by_split = Counter(record.get("split", "unknown") for record in all_records)
    counts_by_task = Counter(record.get("task", "unknown") for record in all_records)
    split_chip_counts: dict[str, int] = {}
    for split in counts_by_split:
        split_chip_counts[split] = len({record["chip_id"] for record in all_records if record.get("split") == split})

    source_manifest = read_json(source_root / "manifest.json")
    manifest = rewrite_paths(source_manifest, source_name, target_name)
    manifest.update(
        {
            "dataset_id": "vectoros_vector_100k_demo_v0_2",
            "run_id": "vectoros_vector_100k_demo_20260509",
            "root": f"data/processed/{target_name}",
            "records": {
                "all_examples": f"data/processed/{target_name}/all_examples.jsonl",
                "train": f"data/processed/{target_name}/train.jsonl",
                "validation": f"data/processed/{target_name}/validation.jsonl",
                "test": f"data/processed/{target_name}/test.jsonl",
            },
            "metadata": {
                "chip_index": f"data/processed/{target_name}/chip_index.json",
                "splits": f"data/processed/{target_name}/splits.json",
                "provenance": f"data/processed/{target_name}/provenance.json",
                "validation_summary": f"data/processed/{target_name}/validation_summary.json",
                "dataset_card": f"data/processed/{target_name}/README.md",
            },
            "counts": {
                "schema_version": "vectoros-demo-validation-v0.2",
                "chips": len(rewritten_chips),
                "examples_total": len(all_records),
                "examples_by_split": dict(sorted(counts_by_split.items())),
                "examples_by_task": dict(sorted(counts_by_task.items())),
                "split_chip_counts": dict(sorted(split_chip_counts.items())),
                "risk_class_counts": dict(sorted(Counter(chip.get("risk_class", "unknown") for chip in rewritten_chips).items())),
                "sample_type_counts": dict(sorted(Counter(chip.get("sample_type", "unknown") for chip in rewritten_chips).items())),
                "module_chip_counts": dict(sorted(Counter(chip.get("disease_module", "unknown") for chip in rewritten_chips).items())),
                "aoi_count": len({chip["aoi_id"] for chip in rewritten_chips}),
                "packets_exist": sum(1 for chip in rewritten_chips if path_under(target_workspace, chip["image_packet"]).exists()),
                "simsat_raw_dirs": sum(
                    1
                    for chip in rewritten_chips
                    if (target_root / "simsat_raw" / chip["aoi_id"] / chip["chip_id"]).exists()
                ),
                "context_patch_files": len(rewritten_chips),
                "context_patch_features": sum(len(features) for features in context_patches.values()),
                "parsed_osm_or_label_source_files": parsed_context_files,
            },
        }
    )
    write_json(target_root / "manifest.json", manifest)

    splits = {
        split: sorted({record["chip_id"] for record in all_records if record.get("split") == split})
        for split in sorted(counts_by_split)
    }
    write_json(target_root / "splits.json", splits)

    provenance = {
        "schema_version": "vectoros-demo-provenance-v0.2",
        "source_dataset": str(source_root),
        "source_hf_dataset": "Alfaxad/vector-100k",
        "selection_policy": f"{args.per_aoi} chips per AOI: top risk, label-positive, and low/hard-negative/random contrast when available",
        "selected_aoi_count": len({chip["aoi_id"] for chip in rewritten_chips}),
        "selected_chip_count": len(rewritten_chips),
        "copied_modalities": [
            "image_packet",
            "sidecar",
            "risk_tile_target",
            "simsat_raw_sentinel_rgb",
            "simsat_raw_sentinel_false_color",
            "simsat_raw_mapbox_satellite",
            "simsat_metadata",
            "compact_per_chip_osm_context_patches",
            "compact_per_chip_weak_label_context_patches",
        ],
        "excluded_modalities": [
            "full 100k JSONL",
            "full AOI raw raster mirrors",
            "model weights",
        ],
    }
    write_json(target_root / "provenance.json", provenance)
    write_json(
        target_root / "validation_summary.json",
        {
            "schema_version": "vectoros-demo-validation-summary-v0.2",
            "status": "ok",
            "counts": manifest["counts"],
        },
    )

    readme = f"""# VectorOS 100k Demo Subset

Compact runtime subset generated from `Alfaxad/vector-100k` for the open-source
VectorOS app.

- AOIs: {manifest['counts']['aoi_count']}
- Chips: {manifest['counts']['chips']}
- Examples: {manifest['counts']['examples_total']}
- Modules: {', '.join(sorted(manifest['counts']['module_chip_counts']))}

This package keeps the visual evidence packets and selected SimSat raw imagery
needed for the app while excluding the full 100k training corpus and raw raster
mirrors.
"""
    (target_root / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()

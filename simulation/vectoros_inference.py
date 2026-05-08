from __future__ import annotations

import os
import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from .vectoros_demo import load_chip_assets, resolve_workspace_path


MODEL_ID = os.environ.get("VECTOROS_MODEL_ID") or "Alfaxad/Vector-LFM2.5-VL-450M"


class VectorOSInferenceError(RuntimeError):
    pass


def _dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("torch", "transformers", "huggingface_hub", "PIL"):
        try:
            if name == "PIL":
                import PIL

                versions[name] = PIL.__version__
            else:
                module = __import__(name)
                versions[name] = getattr(module, "__version__", "unknown")
        except Exception as exc:  # pragma: no cover - diagnostic only
            versions[name] = f"unavailable: {exc}"
    return versions


def _select_device(torch: Any) -> tuple[str, Any]:
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.float32


def _raster_status(layer: dict[str, Any] | None) -> str:
    if not layer:
        return "missing_from_sidecar"
    valid_pixels = layer.get("valid_pixels")
    if valid_pixels is None:
        return "coverage_unknown"
    try:
        if float(valid_pixels) <= 0:
            return "no_valid_pixels_in_selected_chip"
    except (TypeError, ValueError):
        return "coverage_unknown"
    return "observed_in_selected_chip"


def _raster_summary(layer: dict[str, Any] | None) -> dict[str, Any]:
    layer = layer or {}
    return {
        "status": _raster_status(layer),
        "valid_pixels": layer.get("valid_pixels"),
        "mean": layer.get("mean"),
        "median": layer.get("median"),
        "p90": layer.get("p90"),
        "min": layer.get("min"),
        "max": layer.get("max"),
    }


def _compact_prompt_features(sidecar: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    numeric = sidecar.get("numeric_features", {})
    raster = numeric.get("raster_stats", {})
    osm_counts = numeric.get("osm_counts") or {}
    label_counts = numeric.get("label_counts") or {}
    risk = target.get("risk") or {}
    exposure = target.get("exposure") or {}
    signals = target.get("signals") or {}
    aoi = target.get("aoi") or {}
    rainfall = raster.get("rainfall_chirps")
    jrc_occurrence = raster.get("jrc_gsw_occurrence")
    jrc_seasonality = raster.get("jrc_gsw_seasonality")
    population = raster.get("population_worldpop")
    return {
        "chip_id": sidecar.get("chip_id"),
        "aoi": {
            "name": aoi.get("name") or sidecar.get("name"),
            "country": aoi.get("admin0") or sidecar.get("country"),
            "bbox": aoi.get("bbox") or sidecar.get("bbox"),
            "centroid": aoi.get("centroid") or sidecar.get("center"),
        },
        "disease_module": target.get("disease_module") or sidecar.get("disease_module"),
        "sampling_strategy": sidecar.get("quality", {}).get("sampling_strategy") or sidecar.get("sample_type"),
        "panel_order": sidecar.get("panel_order"),
        "visual_quality": {
            "sentinel_available": sidecar.get("quality", {}).get("sentinel_available"),
            "mapbox_available": sidecar.get("quality", {}).get("mapbox_available"),
            "sentinel_cloud_cover_percent": sidecar.get("quality", {}).get("sentinel_cloud_cover_percent"),
            "sentinel_datetime": sidecar.get("quality", {}).get("sentinel_datetime"),
        },
        "risk": {
            "score": risk.get("score"),
            "class": risk.get("class"),
            "confidence": risk.get("confidence"),
            "uncertainty_interval": risk.get("uncertainty_interval"),
            "calibration_model_version": risk.get("calibration_model_version"),
        },
        "climate_and_water": {
            "chirps_rainfall_mm": _raster_summary(rainfall),
            "jrc_gsw_occurrence_percent": _raster_summary(jrc_occurrence),
            "jrc_gsw_seasonality_months": _raster_summary(jrc_seasonality),
            "osm_water_surface_count_in_selected_chip": osm_counts.get("water_surface"),
            "osm_waterway_count_in_selected_chip": osm_counts.get("waterways"),
            "interpretation_rule": (
                "If a JRC layer status is no_valid_pixels_in_selected_chip, describe the JRC value as unavailable "
                "for this selected chip. Do not describe it as confirmed absence of surface water."
            ),
        },
        "exposure": {
            "worldpop_population": _raster_summary(population),
            "population_signal_p90": exposure.get("population_signal_p90"),
            "health_facilities_in_selected_chip": exposure.get("health_facilities_in_chip"),
            "schools_or_waterpoints_in_selected_chip": exposure.get("schools_or_waterpoints_in_chip"),
            "waterway_features_in_selected_chip": exposure.get("waterway_features_in_chip"),
            "urban_or_building_features_in_selected_chip": exposure.get("urban_or_building_features_in_chip"),
            "osm_counts": osm_counts,
        },
        "weak_labels": {
            "counts_in_selected_chip": label_counts,
            "host_or_vector_signal": signals.get("entomology_or_host"),
            "health_surveillance_signal": signals.get("health_surveillance"),
            "label_quality": sidecar.get("label_quality"),
        },
        "target_rationale": target.get("rationale"),
        "limitations": target.get("limitations"),
        "answering_rules": [
            "Use only these grounding facts and the supplied image packet.",
            "Report zeros as selected-chip measurements, not global or AOI-wide truth.",
            "For raster layers with no_valid_pixels_in_selected_chip, say unavailable/no valid pixels for the selected chip.",
            "Do not call weak GBIF, MAP, or OpenDengue labels confirmed local transmission.",
        ],
    }


def _legacy_prompt_features(sidecar: dict[str, Any]) -> dict[str, Any]:
    numeric = sidecar.get("numeric_features", {})
    raster = numeric.get("raster_stats", {})
    return {
        "chip_id": sidecar.get("chip_id"),
        "disease_module": sidecar.get("disease_module"),
        "country": sidecar.get("country"),
        "sample_type": sidecar.get("quality", {}).get("sampling_strategy") or sidecar.get("sample_type"),
        "panel_order": sidecar.get("panel_order"),
        "visual_quality": {
            "sentinel_available": sidecar.get("quality", {}).get("sentinel_available"),
            "mapbox_available": sidecar.get("quality", {}).get("mapbox_available"),
            "sentinel_cloud_cover_percent": sidecar.get("quality", {}).get("sentinel_cloud_cover_percent"),
            "sentinel_datetime": sidecar.get("quality", {}).get("sentinel_datetime"),
        },
        "osm_counts": numeric.get("osm_counts"),
        "label_counts": numeric.get("label_counts"),
        "key_raster_stats": {
            "rainfall_chirps": raster.get("rainfall_chirps"),
            "jrc_gsw_occurrence": raster.get("jrc_gsw_occurrence"),
            "jrc_gsw_seasonality": raster.get("jrc_gsw_seasonality"),
            "population_worldpop": raster.get("population_worldpop"),
        },
        "label_quality": sidecar.get("label_quality"),
    }


def _fmt_fact(value: Any, suffix: str = "") -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return f"{text}{suffix}"
    return f"{value}{suffix}"


def _grounding_fact_sheet(features: dict[str, Any]) -> str:
    risk = features.get("risk", {})
    climate = features.get("climate_and_water", {})
    rainfall = climate.get("chirps_rainfall_mm", {})
    jrc_occurrence = climate.get("jrc_gsw_occurrence_percent", {})
    jrc_seasonality = climate.get("jrc_gsw_seasonality_months", {})
    exposure = features.get("exposure", {})
    labels = features.get("weak_labels", {})
    label_counts = labels.get("counts_in_selected_chip", {})
    host_signal = labels.get("host_or_vector_signal", {}) or {}
    return "\n".join(
        [
            f"AOI: {features.get('aoi', {}).get('name')} ({features.get('disease_module')}).",
            (
                "Risk target: "
                f"score {_fmt_fact(risk.get('score'))}, class {_fmt_fact(risk.get('class'))}, "
                f"confidence {_fmt_fact(risk.get('confidence'))}, uncertainty interval {_fmt_fact(risk.get('uncertainty_interval'))}."
            ),
            (
                "CHIRPS rainfall for this selected chip: "
                f"mean {_fmt_fact(rainfall.get('mean'), ' mm')}, p90 {_fmt_fact(rainfall.get('p90'), ' mm')}, "
                f"valid pixels {_fmt_fact(rainfall.get('valid_pixels'))}, status {_fmt_fact(rainfall.get('status'))}."
            ),
            (
                "JRC Global Surface Water for this selected chip: "
                f"occurrence mean {_fmt_fact(jrc_occurrence.get('mean'), '%')}, occurrence valid pixels "
                f"{_fmt_fact(jrc_occurrence.get('valid_pixels'))}, occurrence status {_fmt_fact(jrc_occurrence.get('status'))}; "
                f"seasonality mean {_fmt_fact(jrc_seasonality.get('mean'), ' months')}, seasonality valid pixels "
                f"{_fmt_fact(jrc_seasonality.get('valid_pixels'))}, seasonality status {_fmt_fact(jrc_seasonality.get('status'))}."
            ),
            (
                "OSM water context counted inside this selected chip: "
                f"water surfaces {_fmt_fact(climate.get('osm_water_surface_count_in_selected_chip'))}, "
                f"waterways {_fmt_fact(climate.get('osm_waterway_count_in_selected_chip'))}."
            ),
            (
                "Exposure context inside this selected chip: "
                f"WorldPop p90 signal {_fmt_fact(exposure.get('population_signal_p90'))}, "
                f"urban/building features {_fmt_fact(exposure.get('urban_or_building_features_in_selected_chip'))}, "
                f"health facilities {_fmt_fact(exposure.get('health_facilities_in_selected_chip'))}, "
                f"schools/waterpoints {_fmt_fact(exposure.get('schools_or_waterpoints_in_selected_chip'))}."
            ),
            (
                "Weak label context inside this selected chip: "
                f"intermediate-host labels {_fmt_fact(label_counts.get('intermediate_host_label'))}, "
                f"vector labels {_fmt_fact(label_counts.get('vector_label'))}, disease labels {_fmt_fact(label_counts.get('disease_label'))}; "
                f"host/vector source {_fmt_fact(host_signal.get('source'))}."
            ),
            (
                "Interpretation rule: zero counts are selected-chip counts. JRC status no_valid_pixels_in_selected_chip "
                "means the JRC raster is unavailable for this selected chip, not confirmed absence of real-world water."
            ),
        ]
    )


def _label_fact_name(module: str | None) -> str:
    if module == "schistosomiasis":
        return "GBIF freshwater snail intermediate-host labels"
    if module == "mosquito_anopheles_malaria":
        return "Anopheles/vector labels"
    if module == "dengue_aedes":
        return "Aedes/vector labels"
    return "Vector/disease labels"


def _verified_evidence_attachment(features: dict[str, Any]) -> dict[str, Any]:
    risk = features.get("risk", {})
    climate = features.get("climate_and_water", {})
    rainfall = climate.get("chirps_rainfall_mm", {})
    jrc = climate.get("jrc_gsw_occurrence_percent", {})
    exposure = features.get("exposure", {})
    labels = features.get("weak_labels", {})
    label_counts = labels.get("counts_in_selected_chip", {})
    module = features.get("disease_module")
    label_name = _label_fact_name(str(module) if module else None)
    jrc_status = jrc.get("status")
    jrc_value = (
        f"{_fmt_fact(jrc_status)}; valid pixels {_fmt_fact(jrc.get('valid_pixels'))}"
        if jrc_status == "no_valid_pixels_in_selected_chip"
        else f"mean {_fmt_fact(jrc.get('mean'), '%')}; valid pixels {_fmt_fact(jrc.get('valid_pixels'))}"
    )
    facts = [
        {
            "id": "E1",
            "label": "Risk target",
            "value": (
                f"score {_fmt_fact(risk.get('score'))}, class {_fmt_fact(risk.get('class'))}, "
                f"confidence {_fmt_fact(risk.get('confidence'))}, uncertainty {_fmt_fact(risk.get('uncertainty_interval'))}"
            ),
            "source": "VectorOS weak-rule target",
        },
        {
            "id": "E2",
            "label": "CHIRPS rainfall",
            "value": (
                f"mean {_fmt_fact(rainfall.get('mean'), ' mm')}, p90 {_fmt_fact(rainfall.get('p90'), ' mm')}, "
                f"valid pixels {_fmt_fact(rainfall.get('valid_pixels'))}"
            ),
            "source": "CHIRPS selected-chip raster stats",
        },
        {
            "id": "E3",
            "label": "JRC surface water",
            "value": jrc_value,
            "source": "JRC Global Surface Water selected-chip raster stats",
        },
        {
            "id": "E4",
            "label": "OSM water context",
            "value": (
                f"{_fmt_fact(climate.get('osm_water_surface_count_in_selected_chip'))} water surfaces, "
                f"{_fmt_fact(climate.get('osm_waterway_count_in_selected_chip'))} waterways"
            ),
            "source": "OpenStreetMap selected-chip counts",
        },
        {
            "id": "E5",
            "label": "WorldPop exposure",
            "value": (
                f"p90 signal {_fmt_fact(exposure.get('population_signal_p90'))}, "
                f"urban/building features {_fmt_fact(exposure.get('urban_or_building_features_in_selected_chip'))}"
            ),
            "source": "WorldPop raster + OSM selected-chip counts",
        },
        {
            "id": "E6",
            "label": label_name,
            "value": (
                f"intermediate-host {_fmt_fact(label_counts.get('intermediate_host_label'))}, "
                f"vector {_fmt_fact(label_counts.get('vector_label'))}, disease {_fmt_fact(label_counts.get('disease_label'))}"
            ),
            "source": "GBIF / OpenDengue / MAP weak-label counts",
        },
    ]
    return {
        "title": "Verified evidence attached to live model response",
        "scope": "selected_chip_not_aoi_wide_truth",
        "chip_id": features.get("chip_id"),
        "aoi": features.get("aoi"),
        "disease_module": module,
        "summary": (
            f"Verified selected-chip facts are attached separately from the model narrative. "
            f"Zeros mean zero in this selected chip; no-valid-pixel raster layers mean unavailable coverage."
        ),
        "facts": facts,
        "notes": [
            "These values come directly from the selected chip sidecar/target, not from generated text.",
            "The generated answer should be read together with this attachment.",
        ],
    }


def _positive_label_instruction(features: dict[str, Any]) -> str:
    module = features.get("disease_module")
    labels = features.get("weak_labels", {}).get("counts_in_selected_chip", {})
    vector = labels.get("vector_label") or 0
    intermediate_host = labels.get("intermediate_host_label") or 0
    disease = labels.get("disease_label") or 0
    if module == "schistosomiasis" and intermediate_host:
        return f"Describe the label signal as freshwater snail intermediate-host labels={intermediate_host}."
    if module == "mosquito_anopheles_malaria" and vector:
        return f"Describe the label signal as Anopheles/vector labels={vector}."
    if module == "dengue_aedes" and vector:
        return f"Describe the label signal as Aedes/vector labels={vector}."
    if disease:
        return f"Describe the label signal as disease-context labels={disease}."
    return "If all label counts are zero, say no weak label count is present in this selected chip."


def _authoritative_prompt_block(evidence: dict[str, Any], features: dict[str, Any]) -> str:
    facts = evidence.get("facts") or []
    fact_lines = "\n".join(
        f"[{fact.get('id')}] {fact.get('label')}: {fact.get('value')} (source: {fact.get('source')})"
        for fact in facts
    )
    return (
        "<authoritative_evidence>\n"
        f"{fact_lines}\n"
        "</authoritative_evidence>\n"
        "<grounding_contract>\n"
        "Use the authoritative_evidence above as the source of truth. Copy numeric values exactly from the evidence IDs. "
        "Every numeric claim in your answer must be traceable to an evidence ID like [E1]. "
        "Do not introduce any number, comparison, rank, pool statistic, or label type that is not in [E1]-[E6]. "
        "If the model image suggests something different, the authoritative evidence still wins. "
        f"{_positive_label_instruction(features)} "
        "If JRC says no_valid_pixels_in_selected_chip, say the JRC raster has no valid pixels for this selected chip; "
        "do not say surface water is absent. "
        "Return 4 concise bullets with citations. Required bullets: Risk, Labels, Rainfall/water, Exposure, Uncertainty/next step.\n"
        "</grounding_contract>"
    )


def _max_consecutive_repeat(text: str) -> int:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
    if not words:
        return 0
    longest = 1
    current = 1
    previous = words[0]
    for word in words[1:]:
        if word == previous:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
            previous = word
    return longest


def _model_consistency_report(text: str, question: str, evidence: dict[str, Any]) -> dict[str, Any]:
    normalized = text.lower()
    question_lower = question.lower()
    bad_phrases = [
        "simulated simulated",
        "air-sea interface",
        "surfer/survey",
        "bottom-order",
        "rain packet",
        "satellite image packet map",
        "\ufffd",
    ]
    found_bad_phrases = [phrase for phrase in bad_phrases if phrase in normalized]
    max_repeat = _max_consecutive_repeat(text)
    evidence_numbers = set()
    for fact in evidence.get("facts", []):
        evidence_numbers.update(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", str(fact.get("value", ""))))
    answer_numbers = set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text))
    unsupported_numbers = sorted(
        number
        for number in answer_numbers - evidence_numbers
        if number not in {"1", "2", "3", "4", "5", "6"}
    )
    expected_terms = []
    if any(term in question_lower for term in ("rain", "rainfall", "chirps")):
        expected_terms.append("chirps")
    if any(term in question_lower for term in ("jrc", "surface-water", "surface water")):
        expected_terms.append("jrc")
    if "osm" in question_lower:
        expected_terms.append("osm")
    if any(term in question_lower for term in ("population", "exposure", "worldpop")):
        expected_terms.append("worldpop")
    missing_terms = [term for term in expected_terms if term not in normalized]
    checks = [
        {
            "name": "verified_evidence_attached",
            "passed": True,
            "detail": "The response includes selected-chip evidence facts from sidecar/target files.",
        },
        {
            "name": "no_obvious_malformed_phrases",
            "passed": not found_bad_phrases,
            "detail": ", ".join(found_bad_phrases) if found_bad_phrases else "No known malformed phrases detected.",
        },
        {
            "name": "no_extreme_repetition",
            "passed": max_repeat < 6,
            "detail": f"Maximum consecutive repeated token count: {max_repeat}.",
        },
        {
            "name": "question_terms_covered",
            "passed": not missing_terms,
            "detail": ", ".join(missing_terms) if missing_terms else "Requested grounding terms are present in model text.",
        },
        {
            "name": "no_unsupported_numbers",
            "passed": not unsupported_numbers,
            "detail": ", ".join(unsupported_numbers) if unsupported_numbers else "All generated numeric values appear in evidence facts.",
        },
    ]
    status = "grounded_with_attachment" if all(check["passed"] for check in checks) else "review_recommended"
    return {
        "status": status,
        "summary": (
            "Model narrative passed lightweight consistency checks."
            if status == "grounded_with_attachment"
            else "Use the verified evidence attachment as source of truth; model narrative may be incomplete or distorted."
        ),
        "checks": checks,
        "evidence_scope": evidence.get("scope"),
    }


def _grounded_response_packet(
    *,
    answer: str,
    display_answer: str,
    evidence: dict[str, Any],
    consistency: dict[str, Any],
    model_id: str,
    task: str,
) -> dict[str, Any]:
    return {
        "type": "vectoros_grounded_live_inference_v0",
        "raw_model_answer": answer,
        "display_answer": display_answer,
        "authoritative_attachment": evidence,
        "verification": consistency,
        "contract": (
            "The raw_model_answer is live generated text. The authoritative_attachment contains selected-chip facts "
            "read directly from VectorOS sidecar/target files. If verification fails, display_answer is repaired "
            "from the authoritative attachment and should be used as the user-facing answer."
        ),
        "model_id": model_id,
        "task": task,
    }


def _fact_lookup(evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {fact.get("id") or fact.get("label"): fact for fact in evidence.get("facts", [])}


def _evidence_aligned_answer(evidence: dict[str, Any], features: dict[str, Any]) -> str:
    facts = _fact_lookup(evidence)
    risk = facts.get("E1", {})
    rainfall = facts.get("E2", {})
    jrc = facts.get("E3", {})
    osm = facts.get("E4", {})
    exposure = facts.get("E5", {})
    labels = facts.get("E6", {})
    aoi = (evidence.get("aoi") or {}).get("name") or "this selected chip"
    module = features.get("disease_module") or "vector module"
    if module == "dengue_aedes":
        module_label = "Aedes / dengue"
    elif module == "mosquito_anopheles_malaria":
        module_label = "Anopheles / malaria"
    elif module == "schistosomiasis":
        module_label = "schistosomiasis"
    else:
        module_label = str(module)
    return "\n".join(
        [
            f"- Risk [E1]: {aoi} is prioritized for {module_label} review with {risk.get('value', 'n/a')}.",
            f"- Labels [E6]: the weak-label signal is {labels.get('value', 'n/a')}; this is not field-confirmed transmission.",
            (
                f"- Rainfall and water [E2][E3][E4]: CHIRPS shows {rainfall.get('value', 'n/a')}; "
                f"JRC shows {jrc.get('value', 'n/a')}; OSM water context shows {osm.get('value', 'n/a')}."
            ),
            f"- Exposure [E5]: population and built-context exposure is {exposure.get('value', 'n/a')}.",
            (
                "- Uncertainty / next step: treat these as selected-chip surveillance facts, not AOI-wide truth; "
                "use the attached evidence for field-review planning and require human validation before action."
            ),
        ]
    )


@lru_cache(maxsize=1)
def _load_model() -> dict[str, Any]:
    try:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
    except Exception as exc:  # pragma: no cover - depends on local install
        raise VectorOSInferenceError(f"Live inference dependencies are not installed correctly: {exc}") from exc

    device, dtype = _select_device(torch)
    started = time.perf_counter()
    try:
        kwargs: dict[str, Any] = {"dtype": dtype}
        if device == "cuda":
            kwargs["device_map"] = "auto"
        model = AutoModelForImageTextToText.from_pretrained(MODEL_ID, **kwargs)
        if device != "cuda":
            model = model.to(device)
        model.eval()
        processor = AutoProcessor.from_pretrained(MODEL_ID)
    except Exception as exc:  # pragma: no cover - model download/runtime dependent
        raise VectorOSInferenceError(f"Failed to load {MODEL_ID}: {exc}") from exc

    return {
        "model": model,
        "processor": processor,
        "torch": torch,
        "device": device,
        "dtype": str(dtype).replace("torch.", ""),
        "loaded_at": time.time(),
        "load_seconds": round(time.perf_counter() - started, 3),
    }


def inference_status() -> dict[str, Any]:
    loaded = _load_model.cache_info().currsize > 0
    payload = {
        "mode": "local_transformers",
        "model_id": MODEL_ID,
        "loaded": loaded,
        "dependencies": _dependency_versions(),
    }
    if loaded:
        state = _load_model()
        payload.update(
            {
                "device": state["device"],
                "dtype": state["dtype"],
                "load_seconds": state["load_seconds"],
                "loaded_at": state["loaded_at"],
            }
        )
    return payload


def run_live_inference(
    *,
    chip_id: str,
    question: str,
    task: str = "officer_explanation",
    max_new_tokens: int = 384,
    temperature: float = 0.0,
) -> dict[str, Any]:
    chip, sidecar, target = load_chip_assets(chip_id)
    image_path = resolve_workspace_path(chip["image_packet"])
    if not image_path.exists():
        raise VectorOSInferenceError(f"Image packet not found for {chip_id}: {image_path}")

    state = _load_model()
    model = state["model"]
    processor = state["processor"]
    torch = state["torch"]

    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - depends on local install
        raise VectorOSInferenceError(f"Pillow is required for live inference: {exc}") from exc

    image = Image.open(image_path).convert("RGB")
    panel_order = sidecar.get("panel_order") or [
        "top_left: SimSat Sentinel-2 true-color RGB",
        "top_right: SimSat Sentinel-2 false color NIR-red-green",
        "bottom_left: Mapbox satellite context",
        "bottom_right: aligned evidence overlay from ESA WorldCover, JRC water, CHIRPS rainfall, WorldPop, OSM, and weak labels",
    ]
    grounding_features = _compact_prompt_features(sidecar, target)
    verified_evidence = _verified_evidence_attachment(grounding_features)
    authoritative_prompt = _authoritative_prompt_block(verified_evidence, grounding_features)
    features = json.dumps(_legacy_prompt_features(sidecar), separators=(",", ":"))
    instructions = {
        "risk_tile_json": "Return only strict JSON matching the VectorOS RiskTile target schema.",
        "officer_explanation": (
            "Write a concise district-officer explanation with evidence, uncertainty, and safe next step."
        ),
        "evidence_cards_json": "Return JSON evidence cards for label signal, environment, and exposure.",
        "uncertainty_audit_json": "Return JSON describing confidence, limitations, missingness, and human-review needs.",
        "field_task_brief": "Draft a short supervisor-reviewed field task brief.",
        "climate_water_explanation": (
            "Answer in exactly four concise bullets with these labels: CHIRPS rainfall, Surface water, "
            "Schistosomiasis implication, Remaining uncertainty. Cite the numeric CHIRPS, JRC, and OSM values. "
            "If JRC valid_pixels is 0, say JRC has no valid pixels for this selected chip instead of saying water is absent. "
            "If an OSM count is 0, say no matching OSM feature is counted in this selected chip."
        ),
        "exposure_explanation": (
            "Answer in three concise bullets covering WorldPop population signal, OSM exposure counts, and review priority. "
            "Keep counts scoped to the selected chip."
        ),
        "field_check_plan": (
            "Return a safe population-level field validation checklist in five concise bullets. "
            "Separate what the packet suggests from what field teams must verify. Do not provide clinical guidance."
        ),
        "copilot_why_here": (
            "Answer the map-copilot question: why is this area flagged? Ground the answer in the supplied "
            "numeric sidecar values and avoid generic wording."
        ),
    }
    instruction = instructions.get(task, instructions["officer_explanation"])
    prompt = (
        "You are VectorOS, a safe public-health geospatial analyst. Use the image packet and sidecar features. "
        "Do not make individual health claims, claim field-verified local disease presence, or provide individual care guidance. "
        f"Panel order: {'; '.join(panel_order)}.\n"
        f"Sidecar features: {features}\n"
        f"{authoritative_prompt}\n"
        f"{instruction} "
        f"User question: {question.strip()}"
    )
    conversation = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are VectorOS, a geospatial public-health assistant. "
                        "Provide population-level environmental surveillance support only."
                    ),
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        },
    ]

    started = time.perf_counter()
    try:
        inputs = processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
            tokenize=True,
        )
        inputs = inputs.to(model.device)
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": max(32, min(int(max_new_tokens), 768)),
            "do_sample": temperature > 0,
            "repetition_penalty": 1.08,
            "no_repeat_ngram_size": 6,
        }
        if temperature > 0:
            generation_kwargs["temperature"] = temperature
        with torch.inference_mode():
            outputs = model.generate(**inputs, **generation_kwargs)
        generated_ids = outputs[:, inputs["input_ids"].shape[-1] :]
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
    except Exception as exc:  # pragma: no cover - model runtime dependent
        raise VectorOSInferenceError(f"Live generation failed for {chip_id}: {exc}") from exc

    model_consistency = _model_consistency_report(text, question, verified_evidence)
    display_answer = (
        text
        if model_consistency.get("status") == "grounded_with_attachment"
        else _evidence_aligned_answer(verified_evidence, grounding_features)
    )
    grounded_response = _grounded_response_packet(
        answer=text,
        display_answer=display_answer,
        evidence=verified_evidence,
        consistency=model_consistency,
        model_id=MODEL_ID,
        task=task,
    )
    return {
        "mode": "local_transformers",
        "model_id": MODEL_ID,
        "task": task,
        "chip_id": chip_id,
        "aoi": target.get("aoi", {}).get("name") or sidecar.get("name"),
        "answer": display_answer,
        "raw_model_answer": text,
        "answer_source": (
            "raw_live_model"
            if model_consistency.get("status") == "grounded_with_attachment"
            else "verified_evidence_repair"
        ),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "device": state["device"],
        "dtype": state["dtype"],
        "image_packet": str(Path(chip["image_packet"])),
        "grounding": grounding_features,
        "verified_evidence": verified_evidence,
        "model_consistency": model_consistency,
        "grounded_response": grounded_response,
        "safety_note": "VectorOS is for population-level surveillance support only; field action requires human review.",
    }

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from .models import Satellite, Telemetry, SimulationCommand
from .vectoros_demo import (
    DATASET_ROOT,
    VectorOSDataError,
    aoi_map_layers,
    connector_status,
    copilot_answer,
    fetch_healthsites_bbox,
    filter_aois,
    list_risk_tiles,
    product_summary,
    resolve_workspace_path,
    risk_tile_detail,
    zero_cost_inference_options,
)
from .vectoros_inference import VectorOSInferenceError, inference_status, run_live_inference


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _int_query(request: HttpRequest, name: str, default: int) -> int:
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default


def vectoros_summary(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    try:
        payload = product_summary()
        payload["connectors"] = connector_status()
        payload["zero_cost_inference_options"] = zero_cost_inference_options()
        return JsonResponse(payload)
    except VectorOSDataError as exc:
        return _json_error(str(exc), status=503)


def vectoros_aois(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    try:
        module = request.GET.get("module") or None
        return JsonResponse({"aois": filter_aois(module=module)})
    except VectorOSDataError as exc:
        return _json_error(str(exc), status=503)


def vectoros_risk_tiles(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    try:
        payload = list_risk_tiles(
            aoi_id=request.GET.get("aoi_id") or None,
            module=request.GET.get("module") or None,
            risk_class=request.GET.get("risk_class") or None,
            sample_type=request.GET.get("sample_type") or None,
            split=request.GET.get("split") or None,
            limit=_int_query(request, "limit", 120),
            offset=_int_query(request, "offset", 0),
        )
        return JsonResponse(payload)
    except VectorOSDataError as exc:
        return _json_error(str(exc), status=503)


def vectoros_risk_tile_detail(request: HttpRequest, chip_id: str) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    try:
        return JsonResponse(risk_tile_detail(chip_id))
    except KeyError:
        raise Http404("Risk tile not found")
    except VectorOSDataError as exc:
        return _json_error(str(exc), status=503)


def vectoros_map_layers(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    aoi_id = request.GET.get("aoi_id")
    if not aoi_id:
        return _json_error("Missing aoi_id query parameter")
    try:
        return JsonResponse(aoi_map_layers(aoi_id, chip_id=request.GET.get("chip_id") or None))
    except KeyError:
        raise Http404("AOI not found")
    except VectorOSDataError as exc:
        return _json_error(str(exc), status=503)


def vectoros_image(request: HttpRequest, image_path: str) -> FileResponse:
    if request.method != "GET":
        raise Http404("Method not allowed")
    resolved = resolve_workspace_path(DATASET_ROOT / image_path)
    try:
        resolved.relative_to(DATASET_ROOT)
    except ValueError:
        raise Http404("Image packet not found")
    if not resolved.exists() or not resolved.is_file():
        raise Http404("Image packet not found")
    if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise Http404("Unsupported media type")
    return FileResponse(resolved.open("rb"), content_type="image/png")


def vectoros_connectors(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    try:
        return JsonResponse(connector_status())
    except VectorOSDataError as exc:
        return _json_error(str(exc), status=503)


def vectoros_inference_status(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    return JsonResponse(inference_status())


@csrf_exempt
def vectoros_infer(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _json_error("Method not allowed", status=405)
    try:
        payload: dict[str, Any] = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON payload")
    chip_id = str(payload.get("chip_id") or "")
    if not chip_id:
        return _json_error("Missing chip_id")
    question = str(payload.get("question") or "Analyze this AOI evidence packet.")
    try:
        max_new_tokens = int(payload.get("max_new_tokens") or 384)
    except (TypeError, ValueError):
        max_new_tokens = 384
    try:
        return JsonResponse(
            run_live_inference(
                chip_id=chip_id,
                question=question,
                task=str(payload.get("task") or "officer_explanation"),
                max_new_tokens=max_new_tokens,
                temperature=float(payload.get("temperature") or 0.0),
            )
        )
    except KeyError:
        raise Http404("Evidence packet not found")
    except (VectorOSDataError, VectorOSInferenceError) as exc:
        return _json_error(str(exc), status=503)


@csrf_exempt
def vectoros_copilot(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _json_error("Method not allowed", status=405)
    try:
        payload: dict[str, Any] = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON payload")
    question = str(payload.get("question") or "Summarize this tile.")
    chip_id = payload.get("chip_id")
    return JsonResponse(copilot_answer(str(chip_id) if chip_id else None, question))


def vectoros_healthsites(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _json_error("Method not allowed", status=405)
    raw_bbox = request.GET.get("bbox")
    if not raw_bbox:
        return _json_error("Missing bbox query parameter")
    try:
        bbox = [float(value.strip()) for value in raw_bbox.split(",")]
    except ValueError:
        return _json_error("Invalid bbox; expected minLon,minLat,maxLon,maxLat")
    if len(bbox) != 4:
        return _json_error("Invalid bbox; expected four comma-separated numbers")
    return JsonResponse(fetch_healthsites_bbox(bbox))


@csrf_exempt
def telemetry_ingest(request: HttpRequest) -> JsonResponse:
    """
    POST /api/telemetry/

    Expected JSON:
    {
      "satellite": "SAT-1",        # name or identifier
      "timestamp": "ISO-8601 UTC",
      "latitude": float,
      "longitude": float,
      "altitude": float?,          # km
      "extra": {...}?              # optional telemetry payload
    }
    """

    if request.method != "POST":
        return _json_error("Method not allowed", status=405)

    try:
        payload: dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return _json_error("Invalid JSON payload")

    sat_name = payload.get("satellite")
    if not sat_name:
        return _json_error("Missing 'satellite' field")

    timestamp_str = payload.get("timestamp")
    if not timestamp_str:
        return _json_error("Missing 'timestamp' field")

    timestamp: datetime | None = parse_datetime(timestamp_str)
    if timestamp is None:
        return _json_error("Invalid 'timestamp' format, expected ISO-8601")

    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError):
        return _json_error("Invalid or missing 'latitude'/'longitude'")

    altitude = payload.get("altitude")
    try:
        altitude_val = float(altitude) if altitude is not None else None
    except (TypeError, ValueError):
        return _json_error("Invalid 'altitude'")

    satellite, _ = Satellite.objects.get_or_create(name=sat_name)

    # Update or create the latest telemetry record for this satellite
    # This ensures we only store the most recently pushed position
    telemetry, created = Telemetry.objects.update_or_create(
        satellite=satellite,
        defaults={
            "timestamp": timestamp,
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude_val,
            "extra": payload.get("extra") or None,
        },
    )

    return JsonResponse(
        {
            "id": telemetry.satellite_id,  # Use satellite_id as the primary key
            "satellite": satellite.name,
            "timestamp": telemetry.timestamp.isoformat(),
            "updated_at": telemetry.updated_at.isoformat(),
        },
        status=201 if created else 200,
    )


def telemetry_recent(request: HttpRequest) -> JsonResponse:
    """
    GET /api/telemetry/recent/

    Returns the latest telemetry for each active satellite (most recently pushed, by updated_at).
    """

    if request.method != "GET":
        return _json_error("Method not allowed", status=405)

    latest_points: list[dict[str, Any]] = []
    satellites = Satellite.objects.filter(active=True).select_related("latest_telemetry")
    
    for sat in satellites:
        # Use OneToOne relationship - each satellite has exactly one latest_telemetry record
        # Check if telemetry exists using hasattr or try/except
        if hasattr(sat, "latest_telemetry"):
            latest = sat.latest_telemetry
            latest_points.append(
                {
                    "satellite": sat.name,
                    "timestamp": latest.timestamp.isoformat(),
                    "latitude": latest.latitude,
                    "longitude": latest.longitude,
                    "altitude": latest.altitude,
                    "extra": latest.extra,
                }
            )

    return JsonResponse({"telemetry": latest_points})


@csrf_exempt
def commands(request: HttpRequest) -> JsonResponse:
    """
    GET /api/commands/  -> simulator polls to fetch all unconsumed commands (in order)
    POST /api/commands/ -> dashboard adds a command to the queue
    """

    if request.method == "GET":
        # Return all unconsumed commands in order, then mark them as consumed
        unconsumed = SimulationCommand.objects.filter(consumed=False).order_by("created_at")
        commands_list = [cmd.to_dict() for cmd in unconsumed]
        
        # Mark commands as consumed
        unconsumed.update(consumed=True)
        
        return JsonResponse({"commands": commands_list})

    if request.method != "POST":
        return _json_error("Method not allowed", status=405)

    try:
        payload: dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return _json_error("Invalid JSON payload")

    command_type = payload.get("command")
    if not command_type:
        return _json_error("Missing 'command' field")

    # Validate command type
    allowed_commands = {cmd[0] for cmd in SimulationCommand.COMMAND_TYPES}
    if command_type not in allowed_commands:
        return _json_error(f"Invalid command '{command_type}'", status=400)

    # Extract and validate parameters based on command type
    parameters: dict[str, Any] = {}
    
    if command_type == "set_start_time":
        start_time_str = payload.get("start_time")
        if start_time_str:
            dt = parse_datetime(start_time_str)
            if dt is None:
                return _json_error("Invalid 'start_time', expected ISO-8601", status=400)
            parameters["start_time"] = dt.isoformat()
    
    elif command_type == "set_step_size":
        if "step_size_seconds" in payload:
            try:
                val = int(payload["step_size_seconds"])
                if val <= 0:
                    raise ValueError
                parameters["step_size_seconds"] = val
            except (TypeError, ValueError):
                return _json_error("'step_size_seconds' must be a positive integer", status=400)
    
    elif command_type == "set_replay_speed":
        if "replay_speed" in payload:
            try:
                val_f = float(payload["replay_speed"])
                if val_f <= 0:
                    raise ValueError
                parameters["replay_speed"] = val_f
            except (TypeError, ValueError):
                return _json_error("'replay_speed' must be a positive number", status=400)
    
    # For start/pause/stop, parameters can include start_time, step_size, replay_speed
    # if they were provided (for convenience, so user can set params and start in one command)
    if command_type in ("start", "pause", "stop"):
        if "start_time" in payload:
            dt = parse_datetime(payload["start_time"])
            if dt is None:
                return _json_error("Invalid 'start_time', expected ISO-8601", status=400)
            parameters["start_time"] = dt.isoformat()
        
        if "step_size_seconds" in payload:
            try:
                val = int(payload["step_size_seconds"])
                if val <= 0:
                    raise ValueError
                parameters["step_size_seconds"] = val
            except (TypeError, ValueError):
                return _json_error("'step_size_seconds' must be a positive integer", status=400)
        
        if "replay_speed" in payload:
            try:
                val_f = float(payload["replay_speed"])
                if val_f <= 0:
                    raise ValueError
                parameters["replay_speed"] = val_f
            except (TypeError, ValueError):
                return _json_error("'replay_speed' must be a positive number", status=400)

    # Create the command
    cmd = SimulationCommand.objects.create(
        command_type=command_type,
        parameters=parameters,
    )

    return JsonResponse(
        {
            "id": cmd.id,
            "command": cmd.command_type,
            "parameters": cmd.parameters,
            "created_at": cmd.created_at.isoformat(),
        },
        status=201,
    )


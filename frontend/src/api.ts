import axios from "axios";

export type RiskClass = "low" | "moderate" | "high" | "very_high";

export interface TelemetryPoint {
  satellite: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  altitude: number | null;
  extra: unknown;
}

export interface Command {
  command: "start" | "pause" | "stop" | "set_start_time" | "set_step_size" | "set_replay_speed";
  parameters: {
    start_time?: string;
    step_size_seconds?: number;
    replay_speed?: number;
  };
}

export interface VectorSummary {
  product: string;
  mode: string;
  model: {
    base: string;
    fine_tuned: string;
    runtime: string;
    zero_cost_inference_note: string;
  };
  dataset: {
    dataset_id: string;
    schema_version: string;
    created_at: string;
    chips: number;
    examples_total: number;
    examples_by_split: Record<string, number>;
    examples_by_task: Record<string, number>;
    risk_class_counts: Record<RiskClass, number>;
    module_chip_counts: Record<string, number>;
    aoi_count: number;
  };
  safety_scope: Record<string, boolean>;
  connectors: ConnectorStatus;
  zero_cost_inference_options: InferenceOption[];
}

export interface InferenceOption {
  path: string;
  runtime: string;
  fit: string;
  notes: string;
}

export interface ConnectorStatus {
  mode: string;
  secrets: {
    mapbox_server_side_configured: boolean;
    healthsites_server_side_configured: boolean;
  };
  sources: DataSourceStatus[];
  public_release_flags: Record<string, string>;
}

export interface DataSourceStatus {
  id: string;
  name: string;
  status: string;
  live_endpoint?: string;
  role: string;
}

export interface AoiSummary {
  aoi_id: string;
  name: string;
  country: string;
  disease_module: string;
  primary_disease: string;
  chip_count: number;
  split_counts: Record<string, number>;
  sample_type_counts: Record<string, number>;
  risk_class_counts: Record<RiskClass, number>;
  risk_score_mean: number;
  risk_score_max: number;
  label_count_total: number;
  center: GeoPoint;
  bbox: BBox;
  representative_chip_id: string;
  representative_image_url: string;
}

export interface GeoPoint {
  lon: number;
  lat: number;
}

export type BBox = [number, number, number, number];

export interface RiskTile {
  chip_id: string;
  aoi_id: string;
  disease_module: string;
  sample_type: string;
  split: string;
  risk: {
    score: number;
    class: RiskClass;
    confidence: number;
    uncertainty_interval?: [number, number];
  };
  label_count: number;
  center: GeoPoint;
  bbox: BBox;
  image_url: string;
  exposure: Record<string, number>;
  quality: {
    sentinel_cloud_cover_percent: number;
    mapbox_available: boolean;
    sentinel_available: boolean;
  };
}

export interface EvidenceCard {
  title: string;
  kind: string;
  status: string;
  body: string;
  metrics: Record<string, string | number | boolean | null>;
}

export interface VectorReport {
  title: string;
  summary: string;
  key_findings: string[];
  recommended_actions: Array<{
    action_type: string;
    description: string;
    priority: string;
    requires_human_approval: boolean;
  }>;
  limitations: string[];
  audit: Record<string, unknown>;
  generated_from: string;
}

export interface FieldTask {
  task_id: string;
  title: string;
  priority: string;
  requires_human_approval: boolean;
  geometry: {
    bbox: BBox;
    center: GeoPoint;
  };
  checklist: string[];
  context: Record<string, string | number | null>;
}

export interface RiskTileDetail {
  chip: RiskTile & Record<string, unknown>;
  image_url: string;
  sidecar: {
    aoi_id: string;
    country: string;
    name: string;
    panel_order: string[];
    source_assets: Record<string, unknown>;
    quality: Record<string, unknown>;
    numeric_features: Record<string, unknown>;
    license_flags?: Record<string, unknown>;
  };
  target: {
    risk_tile_id: string;
    disease_module: string;
    disease_targets: string[];
    aoi: {
      aoi_id: string;
      admin0: string;
      name: string;
      bbox: BBox;
      centroid: GeoPoint;
    };
    time_window: Record<string, unknown>;
    risk: RiskTile["risk"] & Record<string, unknown>;
    hazards: Array<Record<string, unknown>>;
    exposure: Record<string, number>;
    signals: Record<string, unknown>;
    rationale: Array<{ claim: string; evidence_layer: string; evidence_ref: string; confidence: number }>;
    recommended_actions: VectorReport["recommended_actions"];
    limitations: string[];
    audit: Record<string, unknown>;
  };
  evidence_cards: EvidenceCard[];
  report: VectorReport;
  field_task: FieldTask;
  related_chip_ids: string[];
}

export interface CopilotAnswer {
  answer: string;
  scope: string;
  selected_tile: {
    chip_id: string;
    aoi: string;
    risk_class: string;
    risk_score: number;
  };
  citations: string[];
  safety_note: string;
}

export interface AoiMapLayerBundle {
  aoi_id: string;
  chip_id: string;
  name: string;
  bbox: BBox;
  center: GeoPoint;
  image_overlays: Array<{
    id: string;
    label: string;
    layer: string;
    url: string;
    bbox: BBox;
    opacity: number;
  }>;
  feature_collection: GeoJSON.FeatureCollection;
  feature_counts: Record<string, number>;
}

export interface LiveInferenceResult {
  mode: string;
  model_id: string;
  task: string;
  chip_id: string;
  aoi: string;
  answer: string;
  raw_model_answer?: string;
  answer_source?: string;
  latency_seconds: number;
  device: string;
  dtype: string;
  image_packet: string;
  grounding?: Record<string, unknown>;
  verified_evidence?: {
    title: string;
    scope: string;
    chip_id: string;
    summary: string;
    facts: Array<{ id?: string; label: string; value: string; source?: string }>;
    notes: string[];
  };
  model_consistency?: {
    status: string;
    summary: string;
    checks: Array<{ name: string; passed: boolean; detail: string }>;
    evidence_scope?: string;
  };
  grounded_response?: {
    type: string;
    raw_model_answer: string;
    display_answer: string;
    authoritative_attachment: LiveInferenceResult["verified_evidence"];
    verification: LiveInferenceResult["model_consistency"];
    contract: string;
    model_id: string;
    task: string;
  };
  safety_note: string;
}

export interface InferenceStatus {
  mode: string;
  model_id: string;
  loaded: boolean;
  dependencies: Record<string, string>;
  device?: string;
  dtype?: string;
  load_seconds?: number;
  loaded_at?: number;
}

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Cache-Control": "no-cache",
    Pragma: "no-cache",
  },
});

export async function fetchRecentTelemetry(): Promise<TelemetryPoint[]> {
  const res = await api.get<{ telemetry: TelemetryPoint[] }>("/telemetry/recent/");
  return res.data.telemetry ?? [];
}

export async function sendCommand(
  command: Command["command"],
  parameters?: Command["parameters"]
): Promise<{ id: number; command: string; parameters: Record<string, unknown>; created_at: string }> {
  const res = await api.post("/commands/", {
    command,
    ...(parameters || {}),
  });
  return res.data;
}

export async function fetchVectorSummary(): Promise<VectorSummary> {
  const res = await api.get<VectorSummary>("/vectoros/summary/");
  return res.data;
}

export async function fetchAois(module?: string): Promise<AoiSummary[]> {
  const res = await api.get<{ aois: AoiSummary[] }>("/vectoros/aois/", {
    params: module && module !== "all" ? { module } : {},
  });
  return res.data.aois;
}

export async function fetchRiskTiles(params: {
  aoi_id?: string;
  module?: string;
  risk_class?: string;
  sample_type?: string;
  split?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; limit: number; offset: number; tiles: RiskTile[] }> {
  const res = await api.get("/vectoros/risk-tiles/", { params });
  return res.data;
}

export async function fetchRiskTileDetail(chipId: string): Promise<RiskTileDetail> {
  const res = await api.get<RiskTileDetail>(`/vectoros/risk-tiles/${chipId}/`);
  return res.data;
}

export async function fetchAoiMapLayers(aoiId: string, chipId?: string): Promise<AoiMapLayerBundle> {
  const res = await api.get<AoiMapLayerBundle>("/vectoros/map-layers/", {
    params: { aoi_id: aoiId, ...(chipId ? { chip_id: chipId } : {}) },
  });
  return res.data;
}

export async function fetchInferenceStatus(): Promise<InferenceStatus> {
  const res = await api.get<InferenceStatus>("/vectoros/inference/status/");
  return res.data;
}

export async function runLiveInference(params: {
  chip_id: string;
  question: string;
  task?: string;
  max_new_tokens?: number;
  temperature?: number;
}): Promise<LiveInferenceResult> {
  const res = await api.post<LiveInferenceResult>("/vectoros/infer/", params);
  return res.data;
}

export async function askCopilot(chipId: string | null, question: string): Promise<CopilotAnswer> {
  const res = await api.post<CopilotAnswer>("/vectoros/copilot/", {
    chip_id: chipId,
    question,
  });
  return res.data;
}

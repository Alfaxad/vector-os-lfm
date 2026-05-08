import React, { useEffect, useMemo, useState } from "react";
import {
  AoiMapLayerBundle,
  AoiSummary,
  EvidenceCard,
  InferenceStatus,
  LiveInferenceResult,
  RiskTile,
  RiskTileDetail,
  VectorSummary,
  fetchAoiMapLayers,
  fetchAois,
  fetchInferenceStatus,
  fetchRiskTileDetail,
  fetchRiskTiles,
  fetchVectorSummary,
  runLiveInference,
} from "./api";
import { AoiMapView } from "./AoiMapView";

const MODULE_LABELS: Record<string, string> = {
  all: "All modules",
  dengue_aedes: "Aedes / dengue",
  mosquito_anopheles_malaria: "Anopheles / malaria",
  schistosomiasis: "Schistosomiasis",
};

const RISK_LABELS: Record<string, string> = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  very_high: "Very high",
};

const LAYERS = [
  "Sentinel-2",
  "Mapbox",
  "Risk tiles",
  "CHIRPS",
  "JRC water",
  "WorldCover",
  "WorldPop",
  "OSM",
  "Labels",
];

const DEFAULT_LAYERS = [
  "Sentinel-2",
  "Mapbox",
  "Risk tiles",
  "CHIRPS",
  "JRC water",
  "WorldCover",
  "WorldPop",
  "OSM",
  "Labels",
];

const formatNumber = (value: number | undefined | null, digits = 0) => {
  if (value === undefined || value === null || Number.isNaN(value)) return "n/a";
  return new Intl.NumberFormat("en", { maximumFractionDigits: digits }).format(value);
};

const asPercent = (value: number | undefined | null) => {
  if (value === undefined || value === null || Number.isNaN(value)) return "n/a";
  return `${Math.round(value * 100)}%`;
};

const riskTone = (risk: string) => `risk-${risk.replace("_", "-")}`;

const asRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const factValue = (value: unknown, suffix = ""): string => {
  if (value === undefined || value === null || value === "") return "n/a";
  if (typeof value === "number") return `${formatNumber(value, value % 1 === 0 ? 0 : 2)}${suffix}`;
  if (Array.isArray(value)) return value.map((item: unknown) => factValue(item)).join(" - ");
  return `${String(value)}${suffix}`;
};

interface PromptSuggestion {
  label: string;
  prompt: string;
  task: string;
}

const moduleFocus = (module?: string) => {
  if (module === "schistosomiasis") return "freshwater snail host, surface-water, shoreline exposure, and uncertainty";
  if (module === "mosquito_anopheles_malaria") return "Anopheles habitat, rainfall, surface-water, population exposure, and uncertainty";
  return "Aedes/vector labels, rainfall, urban-water context, population exposure, and uncertainty";
};

const buildPromptSuggestions = (aoi: AoiSummary | null, detail: RiskTileDetail | null): PromptSuggestion[] => {
  const name = aoi?.name ?? detail?.target.aoi.name ?? "this AOI";
  const module = aoi?.disease_module ?? detail?.target.disease_module;
  const focus = moduleFocus(module);
  const risk = detail?.target.risk;
  return [
    {
      label: "Prioritization",
      task: "officer_explanation",
      prompt: `For ${name}, explain why this ${MODULE_LABELS[module ?? "all"] ?? module ?? "vector"} AOI is prioritized. Use four concise bullets covering risk score ${risk?.score ?? "n/a"}, confidence ${risk ? asPercent(risk.confidence) : "n/a"}, ${focus}, and one safe field-review next step.`,
    },
    {
      label: "Climate + water",
      task: "officer_explanation",
      prompt: `For ${name}, explain the rainfall and surface-water evidence. Mention CHIRPS rainfall, JRC or OSM water context, what it implies for ${MODULE_LABELS[module ?? "all"] ?? module ?? "the module"}, and what uncertainty remains.`,
    },
    {
      label: "Exposure",
      task: "officer_explanation",
      prompt: `For ${name}, summarize population and OSM exposure context. Include nearby population signal, facilities, schools, waterpoints, urban or building context, and how that affects review priority.`,
    },
    {
      label: "Field check",
      task: "field_task_brief",
      prompt: `For ${name}, propose a safe field validation checklist for ${MODULE_LABELS[module ?? "all"] ?? module ?? "this module"}. Keep it population-level, avoid clinical guidance, and separate evidence from uncertainty.`,
    },
  ];
};

const shouldShowFullPacket = (cloudCoverPercent: number | undefined | null) => {
  if (cloudCoverPercent === undefined || cloudCoverPercent === null || Number.isNaN(cloudCoverPercent)) return true;
  return cloudCoverPercent <= 60;
};

export const App: React.FC = () => {
  const [summary, setSummary] = useState<VectorSummary | null>(null);
  const [aois, setAois] = useState<AoiSummary[]>([]);
  const [selectedModule, setSelectedModule] = useState("all");
  const [selectedAoiId, setSelectedAoiId] = useState<string>("");
  const [evidenceChips, setEvidenceChips] = useState<RiskTile[]>([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string>("");
  const [detail, setDetail] = useState<RiskTileDetail | null>(null);
  const [layerBundle, setLayerBundle] = useState<AoiMapLayerBundle | null>(null);
  const [enabledLayers, setEnabledLayers] = useState(() => new Set(DEFAULT_LAYERS));
  const [question, setQuestion] = useState("Why is this AOI prioritized?");
  const [inferenceStatus, setInferenceStatus] = useState<InferenceStatus | null>(null);
  const [liveInference, setLiveInference] = useState<LiveInferenceResult | null>(null);
  const [inferenceLoading, setInferenceLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const [summaryData, aoiData] = await Promise.all([fetchVectorSummary(), fetchAois()]);
        if (cancelled) return;
        setSummary(summaryData);
        setAois(aoiData);
        setSelectedAoiId(aoiData[0]?.aoi_id ?? "");
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load VectorOS");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadAois = async () => {
      try {
        const nextAois = await fetchAois(selectedModule);
        if (cancelled) return;
        setAois(nextAois);
        if (!nextAois.some((aoi) => aoi.aoi_id === selectedAoiId)) {
          setSelectedAoiId(nextAois[0]?.aoi_id ?? "");
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to filter AOIs");
      }
    };
    loadAois();
    return () => {
      cancelled = true;
    };
  }, [selectedModule, selectedAoiId]);

  useEffect(() => {
    if (!selectedAoiId) return;
    let cancelled = false;
    const loadEvidence = async () => {
      try {
        setDetail(null);
        const data = await fetchRiskTiles({
          aoi_id: selectedAoiId,
          module: selectedModule === "all" ? undefined : selectedModule,
          limit: 80,
        });
        if (cancelled) return;
        setEvidenceChips(data.tiles);
        setSelectedEvidenceId(data.tiles[0]?.chip_id ?? "");
        setLiveInference(null);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load AOI evidence");
      }
    };
    loadEvidence();
    return () => {
      cancelled = true;
    };
  }, [selectedAoiId, selectedModule]);

  useEffect(() => {
    if (!selectedEvidenceId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    const loadDetail = async () => {
      try {
        setDetail(null);
        const data = await fetchRiskTileDetail(selectedEvidenceId);
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load AOI detail");
      }
    };
    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedEvidenceId]);

  useEffect(() => {
    if (!selectedAoiId) return;
    let cancelled = false;
    const loadMapLayers = async () => {
      try {
        const data = await fetchAoiMapLayers(selectedAoiId, selectedEvidenceId || undefined);
        if (!cancelled) setLayerBundle(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load AOI map layers");
      }
    };
    loadMapLayers();
    return () => {
      cancelled = true;
    };
  }, [selectedAoiId, selectedEvidenceId]);

  useEffect(() => {
    let cancelled = false;
    const loadStatus = async () => {
      try {
        const data = await fetchInferenceStatus();
        if (!cancelled) setInferenceStatus(data);
      } catch {
        if (!cancelled) setInferenceStatus(null);
      }
    };
    loadStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedAoi = useMemo(
    () => aois.find((aoi) => aoi.aoi_id === selectedAoiId) ?? aois[0] ?? null,
    [aois, selectedAoiId]
  );

  const selectedEvidence = useMemo(
    () => evidenceChips.find((chip) => chip.chip_id === selectedEvidenceId) ?? evidenceChips[0] ?? null,
    [evidenceChips, selectedEvidenceId]
  );

  const moduleOptions = useMemo(() => {
    const modules = Object.keys(summary?.dataset.module_chip_counts ?? {});
    return ["all", ...modules];
  }, [summary]);

  const promptSuggestions = useMemo(
    () => buildPromptSuggestions(selectedAoi, detail),
    [selectedAoi, detail]
  );

  const submitLiveInference = async (overrideQuestion?: string, overrideTask = "officer_explanation") => {
    const activeChipId = selectedEvidenceId || selectedEvidence?.chip_id;
    if (!activeChipId) {
      setError("No evidence chip is selected yet. Wait for AOI evidence to finish loading, then try again.");
      return;
    }
    const activeQuestion = overrideQuestion ?? question;
    try {
      setError(null);
      setLiveInference(null);
      setInferenceLoading(true);
      setQuestion(activeQuestion);
      if (!selectedEvidenceId) setSelectedEvidenceId(activeChipId);
      const answer = await runLiveInference({
        chip_id: activeChipId,
        question: activeQuestion,
        task: overrideTask,
        max_new_tokens: 512,
      });
      setLiveInference(answer);
      setInferenceStatus(await fetchInferenceStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live inference failed");
    } finally {
      setInferenceLoading(false);
    }
  };

  const toggleLayer = (layer: string) => {
    setEnabledLayers((current) => {
      const next = new Set(current);
      if (next.has(layer)) next.delete(layer);
      else next.add(layer);
      return next;
    });
  };

  if (loading) {
    return (
      <main className="boot-screen">
        <div className="boot-mark">VectorOS</div>
        <div className="boot-bar" />
      </main>
    );
  }

  return (
    <div className="vector-shell">
      <header className="topbar">
        <h1>VectorOS</h1>
      </header>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}

      <main className="workspace">
        <aside className="left-rail">
          <section className="panel">
            <div className="panel-head">
              <h2>Mission</h2>
              <span>{selectedAoi?.country ?? "Global"}</span>
            </div>
            <div className="segmented">
              {moduleOptions.map((module) => (
                <button
                  key={module}
                  type="button"
                  className={module === selectedModule ? "active" : ""}
                  onClick={() => setSelectedModule(module)}
                >
                  {MODULE_LABELS[module] ?? module}
                </button>
              ))}
            </div>
            <label className="field-label" htmlFor="aoi-select">
              AOI
            </label>
            <select id="aoi-select" value={selectedAoiId} onChange={(event) => setSelectedAoiId(event.target.value)}>
              {aois.map((aoi) => (
                <option key={aoi.aoi_id} value={aoi.aoi_id}>
                  {aoi.name}
                </option>
              ))}
            </select>
          </section>

          <section className="panel">
            <div className="panel-head">
              <h2>Layers</h2>
              <span>{enabledLayers.size}/{LAYERS.length}</span>
            </div>
            <div className="layer-list">
              {LAYERS.map((layer) => (
                <label className="layer-row" key={layer}>
                  <input type="checkbox" checked={enabledLayers.has(layer)} onChange={() => toggleLayer(layer)} />
                  <span>{layer}</span>
                </label>
              ))}
            </div>
          </section>
        </aside>

        <section className="map-workspace">
          <div className="map-header">
            <div>
              <h2>{selectedAoi?.name ?? "AOI workspace"}</h2>
              <span>{MODULE_LABELS[selectedAoi?.disease_module ?? "all"] ?? selectedAoi?.disease_module}</span>
            </div>
            <div className="aoi-score">
              <span>Mean risk</span>
              <strong>{formatNumber(selectedAoi?.risk_score_mean, 1)}</strong>
            </div>
            <div className="aoi-score">
              <span>Max risk</span>
              <strong>{formatNumber(selectedAoi?.risk_score_max, 0)}</strong>
            </div>
          </div>

          <AoiMapView
            aoi={selectedAoi}
            evidence={selectedEvidence}
            layerBundle={layerBundle}
            enabledLayers={enabledLayers}
            onSelectRiskTile={setSelectedEvidenceId}
          />
        </section>

        <aside className="right-rail">
          <AoiBriefPanel detail={detail} />
          <LiveModelPanel
            question={question}
            setQuestion={setQuestion}
            suggestions={promptSuggestions}
            inference={liveInference}
            status={inferenceStatus}
            loading={inferenceLoading}
            submit={submitLiveInference}
          />
        </aside>
      </main>
    </div>
  );
};

interface AoiBriefPanelProps {
  detail: RiskTileDetail | null;
}

const AoiBriefPanel: React.FC<AoiBriefPanelProps> = ({ detail }) => {
  if (!detail) {
    return (
      <section className="panel inspector empty">
        <h2>AOI brief</h2>
      </section>
    );
  }
  const risk = detail.target.risk;
  const cloudCover = Number(detail.sidecar.quality.sentinel_cloud_cover_percent);
  const showFullPacket = shouldShowFullPacket(cloudCover);
  return (
    <section className="panel inspector">
      <div className="panel-head">
        <h2>{detail.target.aoi.name}</h2>
        <div className="inspector-actions">
          <span className={`risk-badge ${riskTone(risk.class)}`}>{RISK_LABELS[risk.class]}</span>
        </div>
      </div>
      {showFullPacket ? <FullPacketPreview imageUrl={detail.image_url} /> : <HumanPacketPreview imageUrl={detail.image_url} />}
      <div className="risk-summary">
        <div>
          <span>Priority</span>
          <strong>{formatNumber(risk.score)}</strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>{asPercent(risk.confidence)}</strong>
        </div>
        <div>
          <span>Cloud</span>
          <strong>{formatNumber(Number(detail.sidecar.quality.sentinel_cloud_cover_percent), 1)}%</strong>
        </div>
      </div>
      <EvidenceGrid cards={detail.evidence_cards} />
      <section className="report">
        <h3>Report</h3>
        <p>{detail.report.summary}</p>
        {detail.report.key_findings.slice(0, 3).map((finding) => (
          <div className="finding" key={finding}>
            {finding}
          </div>
        ))}
      </section>
      <section className="provenance">
        <h3>Provenance</h3>
        <div>{detail.report.generated_from}</div>
        <div>{String(detail.target.audit.prompt_version ?? "vectoros prompt")}</div>
      </section>
    </section>
  );
};

const EvidenceGrid: React.FC<{ cards: EvidenceCard[] }> = ({ cards }) => (
  <div className="evidence-grid">
    {cards.map((card) => (
      <article className="evidence-card" key={card.title}>
        <div>
          <strong>{card.title}</strong>
          <span>{card.status.replaceAll("_", " ")}</span>
        </div>
        <p>{card.body}</p>
        <dl>
          {Object.entries(card.metrics)
            .filter(([, value]) => value !== undefined && value !== null)
            .slice(0, 3)
            .map(([key, value]) => (
              <React.Fragment key={key}>
                <dt>{key.replaceAll("_", " ")}</dt>
                <dd>{String(value)}</dd>
              </React.Fragment>
            ))}
        </dl>
      </article>
    ))}
  </div>
);

const FullPacketPreview: React.FC<{ imageUrl: string }> = ({ imageUrl }) => (
  <img className="packet-full-preview" src={imageUrl} alt="" />
);

interface PacketCropProps {
  imageUrl: string;
  quadrant: "mapbox" | "overlay";
}

const PacketQuadrant: React.FC<PacketCropProps> = ({ imageUrl, quadrant }) => (
  <div className={`packet-quadrant packet-${quadrant}`}>
    <img src={imageUrl} alt="" />
  </div>
);

const HumanPacketPreview: React.FC<{ imageUrl: string }> = ({ imageUrl }) => (
  <div className="human-packet">
    <figure>
      <PacketQuadrant imageUrl={imageUrl} quadrant="mapbox" />
      <figcaption>Mapbox context</figcaption>
    </figure>
    <figure>
      <PacketQuadrant imageUrl={imageUrl} quadrant="overlay" />
      <figcaption>Evidence overlay</figcaption>
    </figure>
  </div>
);

interface LiveModelPanelProps {
  question: string;
  setQuestion: (question: string) => void;
  suggestions: PromptSuggestion[];
  inference: LiveInferenceResult | null;
  status: InferenceStatus | null;
  loading: boolean;
  submit: (overrideQuestion?: string, overrideTask?: string) => void;
}

const LiveModelPanel: React.FC<LiveModelPanelProps> = ({
  question,
  setQuestion,
  suggestions,
  inference,
  status,
  loading,
  submit,
}) => (
  <section className="panel copilot">
    <div className="panel-head">
      <h2>Live Model</h2>
      <span>{status?.loaded ? `${status.device ?? "local"} loaded` : status?.mode ?? "local transformers"}</span>
    </div>
    <div className="prompt-suggestions" aria-label="Suggested prompts">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion.label}
          type="button"
          onClick={() => submit(suggestion.prompt, suggestion.task)}
          disabled={loading}
          title={suggestion.prompt}
        >
          {suggestion.label}
        </button>
      ))}
    </div>
    <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={3} />
    <button type="button" className="secondary-action" onClick={() => submit()} disabled={loading}>
      {loading ? "Running Vector-LFM2.5-VL..." : "Run live inference"}
    </button>
    {inference && (
      <div className="copilot-answer">
        <GroundedResponse inference={inference} />
        <span>
          {inference.model_id} on {inference.device} in {formatNumber(inference.latency_seconds, 1)}s.{" "}
          {inference.safety_note}
        </span>
      </div>
    )}
  </section>
);

const GroundedResponse: React.FC<{ inference: LiveInferenceResult }> = ({ inference }) => {
  const verifiedEvidence = inference.verified_evidence;
  return (
    <div className="grounded-response">
      <div className="model-answer-block">
        <strong>Answer</strong>
        <p>{inference.answer}</p>
      </div>
      {verifiedEvidence ? (
        <VerifiedEvidenceAttachment evidence={verifiedEvidence} />
      ) : (
        inference.grounding && <GroundingFacts grounding={inference.grounding} />
      )}
    </div>
  );
};

const VerifiedEvidenceAttachment: React.FC<{
  evidence: NonNullable<LiveInferenceResult["verified_evidence"]>;
}> = ({ evidence }) => (
  <div className="verified-evidence">
    <div className="verified-evidence-head">
      <strong>Citations</strong>
      <span>{evidence.scope.replaceAll("_", " ")}</span>
    </div>
    <dl>
      {evidence.facts.map((fact) => (
        <React.Fragment key={fact.label}>
          <dt>{fact.id ? `[${fact.id}] ${fact.label}` : fact.label}</dt>
          <dd>
            <span>{fact.value}</span>
            {fact.source && <em>{fact.source}</em>}
          </dd>
        </React.Fragment>
      ))}
    </dl>
  </div>
);

const GroundingFacts: React.FC<{ grounding: Record<string, unknown> }> = ({ grounding }) => {
  const climate = asRecord(grounding.climate_and_water);
  const rainfall = asRecord(climate.chirps_rainfall_mm);
  const jrc = asRecord(climate.jrc_gsw_occurrence_percent);
  const exposure = asRecord(grounding.exposure);
  const weakLabels = asRecord(grounding.weak_labels);
  const labelCounts = asRecord(weakLabels.counts_in_selected_chip);
  const rows = [
    {
      label: "CHIRPS",
      value: `mean ${factValue(rainfall.mean, " mm")}, p90 ${factValue(rainfall.p90, " mm")}, valid ${factValue(rainfall.valid_pixels)}`,
    },
    {
      label: "JRC water",
      value: `${factValue(jrc.status)}, valid ${factValue(jrc.valid_pixels)}`,
    },
    {
      label: "OSM water",
      value: `${factValue(climate.osm_water_surface_count_in_selected_chip)} surfaces, ${factValue(climate.osm_waterway_count_in_selected_chip)} waterways`,
    },
    {
      label: "Exposure",
      value: `WorldPop p90 ${factValue(exposure.population_signal_p90)}, urban/building ${factValue(exposure.urban_or_building_features_in_selected_chip)}`,
    },
    {
      label: "Labels",
      value: `intermediate-host ${factValue(labelCounts.intermediate_host_label)}, vector ${factValue(labelCounts.vector_label)}, disease ${factValue(labelCounts.disease_label)}`,
    },
  ];
  return (
    <div className="grounding-facts">
      <strong>Grounding values used by this request</strong>
      <dl>
        {rows.map((row) => (
          <React.Fragment key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </React.Fragment>
        ))}
      </dl>
    </div>
  );
};

import React, { useEffect, useRef } from "react";
import L, { Map as LeafletMap } from "leaflet";
import "leaflet/dist/leaflet.css";
import type { AoiMapLayerBundle, AoiSummary, RiskTile } from "./api";

interface AoiMapViewProps {
  aoi: AoiSummary | null;
  evidence: RiskTile | null;
  layerBundle: AoiMapLayerBundle | null;
  enabledLayers: Set<string>;
  onSelectRiskTile?: (chipId: string) => void;
}

const ESRI_WORLD_IMAGERY =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

const toLeafletBounds = (bbox: [number, number, number, number]) =>
  L.latLngBounds([bbox[1], bbox[0]], [bbox[3], bbox[2]]);

const riskColor = (riskClass: string) => {
  if (riskClass === "very_high") return "#8b5cf6";
  if (riskClass === "high") return "#ef6a5b";
  if (riskClass === "moderate") return "#d6a13a";
  return "#4d9d6c";
};

const pointStyle = (feature?: GeoJSON.Feature): L.CircleMarkerOptions => {
  const layer = String(feature?.properties?.layer ?? "");
  const kind = String(feature?.properties?.kind ?? "");
  if (kind === "risk_tile") {
    const selected = Boolean(feature?.properties?.selected);
    return {
      radius: selected ? 5 : 4,
      color: selected ? "#ffffff" : "rgba(255,255,255,0.82)",
      weight: selected ? 2 : 1,
      fillColor: riskColor(String(feature?.properties?.risk_class ?? "")),
      fillOpacity: 0.92,
    };
  }
  if (kind === "label_context") {
    const fillColor = layer.includes("intermediate") ? "#f2b84b" : layer.includes("disease") ? "#ef6a5b" : "#d85be8";
    return { radius: 4, color: "#ffffff", weight: 1, fillColor, fillOpacity: 0.88 };
  }
  if (kind === "rainfall_signal") return { radius: 25, color: "#7dd3fc", weight: 1.4, fillColor: "#2f8fa8", fillOpacity: 0.18 };
  if (kind === "population_signal") return { radius: 19, color: "#fff1a8", weight: 1.4, fillColor: "#f2f0a6", fillOpacity: 0.22 };
  if (kind === "landcover_signal") return { radius: 15, color: "#b7f3c5", weight: 1.4, fillColor: "#57a368", fillOpacity: 0.16 };
  if (kind === "jrc_signal") return { radius: 13, color: "#93c5fd", weight: 1.4, fillColor: "#2563eb", fillOpacity: 0.2 };
  if (layer === "water") return { radius: 3, color: "#f8fbff", weight: 1, fillColor: "#2c9ed6", fillOpacity: 0.78 };
  if (layer === "urban") return { radius: 4, color: "#ffffff", weight: 1, fillColor: "#d19b3a", fillOpacity: 0.56 };
  if (layer === "schools_waterpoints") return { radius: 4, color: "#ffffff", weight: 1, fillColor: "#2e7b55", fillOpacity: 0.82 };
  return { radius: 2.1, color: "#17251d", weight: 0.4, fillColor: "#ffffff", fillOpacity: 0.64 };
};

const polygonStyle = (feature?: GeoJSON.Feature): L.PathOptions => {
  const kind = String(feature?.properties?.kind ?? "");
  if (kind === "sentinel_footprint") {
    return { color: "#d7f6ff", weight: 2, dashArray: "4 6", fillOpacity: 0 };
  }
  return { color: "#f5fff4", weight: 2, dashArray: "5 5", fillColor: "#78a063", fillOpacity: 0.08 };
};

const featureEnabled = (feature: GeoJSON.Feature, enabledLayers: Set<string>) => {
  const layer = String(feature.properties?.layer ?? "");
  const kind = String(feature.properties?.kind ?? "");
  if (kind === "aoi_boundary") return true;
  if (kind === "sentinel_footprint") return enabledLayers.has("Sentinel-2");
  if (kind === "risk_tile") return enabledLayers.has("Risk tiles");
  if (kind === "rainfall_signal") return enabledLayers.has("CHIRPS");
  if (kind === "population_signal") return enabledLayers.has("WorldPop");
  if (kind === "landcover_signal") return enabledLayers.has("WorldCover");
  if (kind === "jrc_signal" || layer === "water") return enabledLayers.has("JRC water");
  if (kind === "label_context") return enabledLayers.has("Labels");
  if (layer === "roads") return false;
  if (layer === "urban" || layer === "schools_waterpoints") return enabledLayers.has("OSM");
  return true;
};

const escapeHtml = (value: unknown) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const formatMetricKey = (key: string) => key.replaceAll("_", " ");

const popupHtml = (properties: GeoJSON.GeoJsonProperties) => {
  const props = properties ?? {};
  const title = props.title ?? props.name ?? props.layer ?? "VectorOS layer";
  const summary = props.summary ?? "";
  const source = props.source ?? "";
  const metrics = props.metrics && typeof props.metrics === "object" ? Object.entries(props.metrics as Record<string, unknown>) : [];
  const metricRows = metrics
    .slice(0, 8)
    .map(([key, value]) => `<dt>${escapeHtml(formatMetricKey(key))}</dt><dd title="${escapeHtml(value)}">${escapeHtml(value)}</dd>`)
    .join("");
  return `
    <section class="map-popup">
      <div class="map-popup-kicker">${escapeHtml(source)}</div>
      <strong>${escapeHtml(title)}</strong>
      ${summary ? `<p>${escapeHtml(summary)}</p>` : ""}
      ${metricRows ? `<dl>${metricRows}</dl>` : ""}
    </section>
  `;
};

export const AoiMapView: React.FC<AoiMapViewProps> = ({
  aoi,
  evidence,
  layerBundle,
  enabledLayers,
  onSelectRiskTile,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const dynamicLayerRef = useRef<L.LayerGroup | null>(null);
  const imageLayerRef = useRef<L.ImageOverlay | null>(null);
  const visibleLayerTags = [
    enabledLayers.has("Mapbox") ? "Mapbox crop" : null,
    enabledLayers.has("Sentinel-2") ? "Sentinel footprint" : null,
    enabledLayers.has("Risk tiles") ? "Risk tiles" : null,
    enabledLayers.has("CHIRPS") ? "Rainfall" : null,
    enabledLayers.has("WorldPop") ? "Population" : null,
    enabledLayers.has("WorldCover") ? "Land cover" : null,
    enabledLayers.has("JRC water") ? "Water" : null,
    enabledLayers.has("OSM") ? "OSM" : null,
    enabledLayers.has("Labels") ? "Labels" : null,
  ].filter((tag): tag is string => Boolean(tag));

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      attributionControl: false,
      zoomControl: true,
      preferCanvas: true,
      zoomDelta: 0.5,
      zoomSnap: 0.25,
    });
    L.tileLayer(ESRI_WORLD_IMAGERY, { maxZoom: 19 }).addTo(map);
    dynamicLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    setTimeout(() => map.invalidateSize(), 0);
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const bbox = layerBundle?.bbox ?? evidence?.bbox ?? aoi?.bbox;
    if (!bbox) return;
    const fit = () => {
      map.invalidateSize();
      map.fitBounds(toLeafletBounds(bbox), { padding: [8, 8], maxZoom: 16 });
      map.setZoom(Math.min(map.getZoom() + 0.5, 17), { animate: false });
    };
    requestAnimationFrame(fit);
    setTimeout(fit, 150);
  }, [aoi?.bbox, evidence?.bbox, layerBundle?.bbox]);

  useEffect(() => {
    const map = mapRef.current;
    const group = dynamicLayerRef.current;
    if (!map || !group || !layerBundle) return;
    group.clearLayers();
    if (imageLayerRef.current) {
      map.removeLayer(imageLayerRef.current);
      imageLayerRef.current = null;
    }

    const mapboxOverlay = layerBundle.image_overlays.find((overlay) => overlay.id === "mapbox_satellite");
    if (mapboxOverlay && enabledLayers.has("Mapbox")) {
      imageLayerRef.current = L.imageOverlay(mapboxOverlay.url, toLeafletBounds(mapboxOverlay.bbox), {
        opacity: mapboxOverlay.opacity,
      }).addTo(map);
    }

    const features = layerBundle.feature_collection.features.filter((feature) =>
      featureEnabled(feature as GeoJSON.Feature, enabledLayers)
    );
    L.geoJSON(
      { type: "FeatureCollection", features } as GeoJSON.FeatureCollection,
      {
        style: polygonStyle,
        pointToLayer: (feature, latlng) => L.circleMarker(latlng, pointStyle(feature)),
        onEachFeature: (feature, layer) => {
          const props = feature.properties ?? {};
          layer.bindTooltip(popupHtml(props), {
            className: "map-hover-card",
            direction: "top",
            offset: [0, -10],
            opacity: 1,
            sticky: true,
          });
          if (props.kind === "risk_tile" && typeof props.chip_id === "string" && onSelectRiskTile) {
            layer.on("click", () => onSelectRiskTile(props.chip_id as string));
          }
        },
      }
    ).addTo(group);
  }, [enabledLayers, layerBundle, onSelectRiskTile]);

  return (
    <div className="aoi-map">
      <div ref={containerRef} className="leaflet-canvas" />
      <div className="map-chip-label">
        <strong>{aoi?.name ?? "AOI"}</strong>
        <span>Interactive AOI context</span>
      </div>
      <div className="map-layer-readout">
        {visibleLayerTags.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
    </div>
  );
};

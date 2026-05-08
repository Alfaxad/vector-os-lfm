from django.urls import path

from . import views


urlpatterns = [
    path("telemetry/", views.telemetry_ingest, name="telemetry-ingest"),
    path("telemetry/recent/", views.telemetry_recent, name="telemetry-recent"),
    path("commands/", views.commands, name="commands"),
    path("vectoros/summary/", views.vectoros_summary, name="vectoros-summary"),
    path("vectoros/aois/", views.vectoros_aois, name="vectoros-aois"),
    path("vectoros/risk-tiles/", views.vectoros_risk_tiles, name="vectoros-risk-tiles"),
    path("vectoros/risk-tiles/<str:chip_id>/", views.vectoros_risk_tile_detail, name="vectoros-risk-tile-detail"),
    path("vectoros/map-layers/", views.vectoros_map_layers, name="vectoros-map-layers"),
    path("vectoros/images/<path:image_path>", views.vectoros_image, name="vectoros-image"),
    path("vectoros/connectors/", views.vectoros_connectors, name="vectoros-connectors"),
    path("vectoros/inference/status/", views.vectoros_inference_status, name="vectoros-inference-status"),
    path("vectoros/infer/", views.vectoros_infer, name="vectoros-infer"),
    path("vectoros/copilot/", views.vectoros_copilot, name="vectoros-copilot"),
    path("vectoros/healthsites/", views.vectoros_healthsites, name="vectoros-healthsites"),
]


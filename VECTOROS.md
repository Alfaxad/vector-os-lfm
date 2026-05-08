# VectorOS Runtime Notes

The demo runs as a Django backend plus React/Vite frontend.

## Inference

Default mode is local Transformers inference. `simulation/vectoros_inference.py`
loads `Alfaxad/Vector-LFM2.5-VL-450M` on demand and generates fresh responses
for prompt-suggestion clicks or custom prompts. It uses CUDA, Apple MPS, or CPU
depending on the host.

The app does not ship cached model answers. It does ship a compact smoke data
package so the UI and API can run immediately after clone.

## Data

Default dataset:

```bash
data/processed/vector-100k-demo
```

Full dataset:

```bash
VECTOROS_DATASET_ROOT=/absolute/path/to/vector-100k
```

The full dataset is hosted on Hugging Face at
`Alfaxad/vector-100k`.

## Secrets

Keep these in `.env` or deployment secrets:

```bash
MAPBOX_ACCESS_TOKEN=
HEALTHSITES_API_KEY=
```

The browser should never receive private service keys.

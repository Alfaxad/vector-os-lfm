#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the full VectorOS dataset from Hugging Face.")
    parser.add_argument("--repo", default="Alfaxad/vector-100k", help="Hugging Face dataset repo id.")
    parser.add_argument(
        "--target",
        default="data/processed/vector-100k",
        help="Local directory for the downloaded dataset snapshot.",
    )
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=args.repo,
        repo_type="dataset",
        local_dir=str(target),
    )
    print(f"Downloaded {args.repo} to {target}")


if __name__ == "__main__":
    main()

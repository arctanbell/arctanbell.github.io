#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

BASE_URL = (
    "https://raw.githubusercontent.com/"
    "oolong-tea-2026/arena-ai-leaderboards/main/data"
)
CATEGORIES = ("text", "code", "vision")
FIELDS = ("rank", "model", "vendor", "license", "score", "ci", "votes")
CATEGORY_LABELS = {"text": "Text", "code": "Code", "vision": "Vision"}


def parse_latest(payload: dict) -> str:
    date = payload.get("date")
    path = payload.get("path")
    if not isinstance(date, str) or not isinstance(path, str) or path != date:
        raise ValueError("latest snapshot must contain matching date and path")
    return path


def normalize_category(payload: dict, category: str, limit: int = 20) -> dict:
    meta = payload.get("meta")
    models = payload.get("models")
    if not isinstance(meta, dict) or not isinstance(models, list):
        raise ValueError(f"{category}: expected meta object and models array")
    if meta.get("leaderboard") != category:
        raise ValueError(f"{category}: leaderboard name mismatch")

    normalized = []
    for model in models:
        if (
            not isinstance(model, dict)
            or not isinstance(model.get("rank"), int)
            or not model.get("model")
        ):
            raise ValueError(f"{category}: model requires integer rank and model name")
        normalized.append({field: model.get(field) for field in FIELDS})

    normalized.sort(key=lambda item: item["rank"])
    return {
        "label": CATEGORY_LABELS[category],
        "source_url": meta.get("source_url"),
        "upstream_model_count": meta.get("model_count", len(models)),
        "models": normalized[:limit],
    }


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "arctanbell.github.io leaderboard updater"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def build_snapshot(
    fetcher: Callable[[str], dict],
    fetched_at: str | None = None,
) -> dict:
    path = parse_latest(fetcher(f"{BASE_URL}/latest.json"))
    categories = {
        category: normalize_category(
            fetcher(f"{BASE_URL}/{path}/{category}.json"),
            category,
        )
        for category in CATEGORIES
    }
    return {
        "schema_version": 1,
        "snapshot_date": path,
        "fetched_at": fetched_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "name": "Arena AI Leaderboards — Daily Snapshots",
            "repository": (
                "https://github.com/"
                "oolong-tea-2026/arena-ai-leaderboards"
            ),
            "arena": "https://arena.ai/leaderboard",
        },
        "categories": categories,
    }


def write_snapshot(snapshot: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        dir=output_path.parent,
        text=True,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(snapshot, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, output_path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def update_snapshot(
    fetcher: Callable[[str], dict],
    output_path: Path,
    fetched_at: str | None = None,
) -> None:
    write_snapshot(
        build_snapshot(fetcher, fetched_at=fetched_at),
        output_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/arena-leaderboard.json"),
    )
    args = parser.parse_args()
    update_snapshot(fetch_json, args.output)


if __name__ == "__main__":
    main()

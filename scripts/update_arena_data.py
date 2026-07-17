#!/usr/bin/env python3
from __future__ import annotations

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

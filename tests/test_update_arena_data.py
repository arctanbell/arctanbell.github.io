import json
import tempfile
import unittest
from pathlib import Path

from scripts.update_arena_data import (
    BASE_URL,
    build_snapshot,
    normalize_category,
    parse_latest,
    update_snapshot,
    write_snapshot,
)


def category_payload(name="text", count=25):
    return {
        "meta": {
            "leaderboard": name,
            "source_url": f"https://arena.ai/leaderboard/{name}",
            "fetched_at": "2026-07-16T04:30:00+00:00",
            "model_count": count,
        },
        "models": [
            {
                "rank": rank,
                "model": f"model-{rank}",
                "vendor": None if rank == 2 else "Vendor",
                "license": "open",
                "score": 1500 - rank,
                "ci": None if rank == 2 else 5,
                "votes": 1000 * rank,
            }
            for rank in range(count, 0, -1)
        ],
    }


class UpdateArenaDataTests(unittest.TestCase):
    def test_parse_latest_requires_date_and_path(self):
        self.assertEqual(
            parse_latest({"date": "2026-07-16", "path": "2026-07-16"}),
            "2026-07-16",
        )
        with self.assertRaises(ValueError):
            parse_latest({"date": "2026-07-16"})

    def test_normalize_category_sorts_and_limits_to_twenty(self):
        result = normalize_category(category_payload(), "text")

        self.assertEqual(len(result["models"]), 20)
        self.assertEqual([model["rank"] for model in result["models"][:3]], [1, 2, 3])
        self.assertIsNone(result["models"][1]["vendor"])
        self.assertIsNone(result["models"][1]["ci"])

    def test_normalize_category_rejects_missing_identity(self):
        payload = category_payload(count=1)
        del payload["models"][0]["model"]

        with self.assertRaises(ValueError):
            normalize_category(payload, "text")

    def test_build_snapshot_fetches_all_categories(self):
        payloads = {
            f"{BASE_URL}/latest.json": {
                "date": "2026-07-16",
                "path": "2026-07-16",
            }
        }
        for category in ("text", "code", "vision"):
            payloads[f"{BASE_URL}/2026-07-16/{category}.json"] = category_payload(
                category,
                3,
            )

        result = build_snapshot(
            payloads.__getitem__,
            fetched_at="2026-07-16T06:30:00Z",
        )

        self.assertEqual(result["snapshot_date"], "2026-07-16")
        self.assertEqual(
            set(result["categories"]),
            {"text", "code", "vision"},
        )

    def test_write_snapshot_replaces_valid_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "arena.json"

            write_snapshot({"schema_version": 1}, output)

            self.assertEqual(
                json.loads(output.read_text()),
                {"schema_version": 1},
            )

    def test_build_failure_does_not_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "arena.json"
            output.write_text('{"old": true}')

            with self.assertRaises(KeyError):
                update_snapshot(
                    {
                        f"{BASE_URL}/latest.json": {
                            "date": "2026-07-16",
                            "path": "2026-07-16",
                        }
                    }.__getitem__,
                    output,
                )

            self.assertEqual(output.read_text(), '{"old": true}')


if __name__ == "__main__":
    unittest.main()

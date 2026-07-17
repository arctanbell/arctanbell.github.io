import unittest

from scripts.update_arena_data import normalize_category, parse_latest


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


if __name__ == "__main__":
    unittest.main()

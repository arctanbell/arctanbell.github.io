import unittest
from pathlib import Path


class ArenaPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("arena.html").read_text()

    def test_page_has_no_iframe_and_reads_local_snapshot(self):
        self.assertNotIn("<iframe", self.html)
        self.assertIn('fetch("data/arena-leaderboard.json")', self.html)

    def test_page_contains_three_tabs_and_render_targets(self):
        for category in ("text", "code", "vision"):
            self.assertIn(f'data-category="{category}"', self.html)
        for target in (
            "leaderboard-tabs",
            "leaderboard-body",
            "snapshot-date",
            "leaderboard-status",
            "leaderboard-error",
        ):
            self.assertIn(f'id="{target}"', self.html)

    def test_page_attributes_upstream_sources(self):
        self.assertIn(
            "oolong-tea-2026/arena-ai-leaderboards",
            self.html,
        )
        self.assertIn("https://arena.ai/leaderboard", self.html)

    def test_update_workflow_contract(self):
        workflow = Path(".github/workflows/update-arena.yml").read_text()

        self.assertIn("cron: '30 6 * * *'", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("python3 scripts/update_arena_data.py", workflow)
        self.assertIn("python3 -m unittest discover -s tests -v", workflow)
        self.assertIn(
            "git diff --quiet -- data/arena-leaderboard.json",
            workflow,
        )
        self.assertIn('repos/${GITHUB_REPOSITORY}/pages/builds', workflow)


if __name__ == "__main__":
    unittest.main()

# Static Arena Leaderboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blocked Arena iframe with a daily updated, locally hosted Text/Code/Vision leaderboard on GitHub Pages.

**Architecture:** A standard-library Python updater reads the upstream community snapshot, validates and normalizes the top 20 entries per category, and atomically writes one local JSON file. A scheduled GitHub Actions workflow refreshes and commits that file; `arena.html` renders only the same-origin local snapshot with three client-side tabs and a failure fallback.

**Tech Stack:** Python 3 standard library, `unittest`, static HTML/CSS/JavaScript, GitHub Actions, GitHub Pages.

## Global Constraints

- Categories are exactly `text`, `code`, and `vision`.
- Retain at most 20 ranked models per category.
- The updater uses only the Python standard library.
- The page performs no runtime request to Arena or the upstream snapshot repository.
- The last-known-good local snapshot must survive all upstream fetch and validation failures.
- The workflow runs at `06:30 UTC` daily and supports manual dispatch.
- Preserve the current homepage and unrelated repository files.

## File Map

- Create `scripts/update_arena_data.py`: fetch, validate, normalize, and atomically write the local snapshot.
- Create `tests/test_update_arena_data.py`: unit tests for the updater using in-memory upstream payloads.
- Create `tests/test_arena_page.py`: structural contract tests for the static page and workflow.
- Create `data/arena-leaderboard.json`: committed last-known-good snapshot consumed by the page.
- Create `.github/workflows/update-arena.yml`: scheduled/manual update workflow.
- Modify `arena.html`: static responsive leaderboard UI.

---

### Task 1: Updater contracts and normalization

**Files:**
- Create: `tests/test_update_arena_data.py`
- Create: `scripts/update_arena_data.py`

**Interfaces:**
- Produces: `parse_latest(payload: dict) -> str`
- Produces: `normalize_category(payload: dict, category: str, limit: int = 20) -> dict`

- [ ] **Step 1: Write failing normalization tests**

Create `tests/test_update_arena_data.py` with `unittest` cases that assert:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.update_arena_data import (
    normalize_category,
    parse_latest,
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
        self.assertEqual(parse_latest({"date": "2026-07-16", "path": "2026-07-16"}), "2026-07-16")
        with self.assertRaises(ValueError):
            parse_latest({"date": "2026-07-16"})

    def test_normalize_category_sorts_and_limits_to_twenty(self):
        result = normalize_category(category_payload(), "text")
        self.assertEqual(len(result["models"]), 20)
        self.assertEqual([m["rank"] for m in result["models"][:3]], [1, 2, 3])
        self.assertIsNone(result["models"][1]["vendor"])
        self.assertIsNone(result["models"][1]["ci"])

    def test_normalize_category_rejects_missing_identity(self):
        payload = category_payload(count=1)
        del payload["models"][0]["model"]
        with self.assertRaises(ValueError):
            normalize_category(payload, "text")
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest tests.test_update_arena_data -v`

Expected: import failure because `scripts.update_arena_data` does not exist.

- [ ] **Step 3: Implement parsing and normalization**

Create `scripts/update_arena_data.py` with constants and validation:

```python
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

BASE_URL = "https://raw.githubusercontent.com/oolong-tea-2026/arena-ai-leaderboards/main/data"
CATEGORIES = ("text", "code", "vision")
FIELDS = ("rank", "model", "vendor", "license", "score", "ci", "votes")


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
        if not isinstance(model, dict) or not isinstance(model.get("rank"), int) or not model.get("model"):
            raise ValueError(f"{category}: model requires integer rank and model name")
        normalized.append({field: model.get(field) for field in FIELDS})
    normalized.sort(key=lambda item: item["rank"])
    return {
        "label": {"text": "Text", "code": "Code", "vision": "Vision"}[category],
        "source_url": meta.get("source_url"),
        "upstream_model_count": meta.get("model_count", len(models)),
        "models": normalized[:limit],
    }
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python3 -m unittest tests.test_update_arena_data -v`

Expected: all three normalization tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/update_arena_data.py tests/test_update_arena_data.py
git commit -m "添加 Arena 排行榜数据规范化"
```

---

### Task 2: Snapshot assembly and atomic output

**Files:**
- Modify: `tests/test_update_arena_data.py`
- Modify: `scripts/update_arena_data.py`
- Create: `data/arena-leaderboard.json`

**Interfaces:**
- Consumes: `parse_latest`, `normalize_category`, `BASE_URL`, `CATEGORIES`
- Produces: `build_snapshot(fetcher: Callable[[str], dict], fetched_at: str | None = None) -> dict`
- Produces: `write_snapshot(snapshot: dict, output_path: Path) -> None`
- Produces: executable `python3 scripts/update_arena_data.py --output data/arena-leaderboard.json`
- Produces: `update_snapshot(fetcher: Callable[[str], dict], output_path: Path, fetched_at: str | None = None) -> None`

- [ ] **Step 1: Add failing build and atomic-write tests**

Extend the import block with `BASE_URL`, `build_snapshot`, `update_snapshot`, and `write_snapshot`, then append tests using a URL-keyed fake fetcher:

```python
    def test_build_snapshot_fetches_all_categories(self):
        payloads = {f"{BASE_URL}/latest.json": {"date": "2026-07-16", "path": "2026-07-16"}}
        for category in ("text", "code", "vision"):
            payloads[f"{BASE_URL}/2026-07-16/{category}.json"] = category_payload(category, 3)
        result = build_snapshot(payloads.__getitem__, fetched_at="2026-07-16T06:30:00Z")
        self.assertEqual(result["snapshot_date"], "2026-07-16")
        self.assertEqual(set(result["categories"]), {"text", "code", "vision"})

    def test_write_snapshot_replaces_valid_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "arena.json"
            write_snapshot({"schema_version": 1}, output)
            self.assertEqual(json.loads(output.read_text()), {"schema_version": 1})

    def test_build_failure_does_not_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "arena.json"
            output.write_text('{"old": true}')
            with self.assertRaises(KeyError):
                update_snapshot(
                    {f"{BASE_URL}/latest.json": {"date": "2026-07-16", "path": "2026-07-16"}}.__getitem__,
                    output,
                )
            self.assertEqual(output.read_text(), '{"old": true}')
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest tests.test_update_arena_data -v`

Expected: failure because snapshot assembly and atomic output are not implemented.

- [ ] **Step 3: Implement fetch, assembly, atomic write, and CLI**

Add:

```python
def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "arctanbell.github.io leaderboard updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def build_snapshot(fetcher: Callable[[str], dict], fetched_at: str | None = None) -> dict:
    path = parse_latest(fetcher(f"{BASE_URL}/latest.json"))
    categories = {
        category: normalize_category(fetcher(f"{BASE_URL}/{path}/{category}.json"), category)
        for category in CATEGORIES
    }
    return {
        "schema_version": 1,
        "snapshot_date": path,
        "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "name": "Arena AI Leaderboards — Daily Snapshots",
            "repository": "https://github.com/oolong-tea-2026/arena-ai-leaderboards",
            "arena": "https://arena.ai/leaderboard",
        },
        "categories": categories,
    }


def write_snapshot(snapshot: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", dir=output_path.parent, text=True)
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
    write_snapshot(build_snapshot(fetcher, fetched_at=fetched_at), output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/arena-leaderboard.json"))
    args = parser.parse_args()
    update_snapshot(fetch_json, args.output)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify GREEN and generate the real snapshot**

Run:

```bash
python3 -m unittest tests.test_update_arena_data -v
python3 scripts/update_arena_data.py --output data/arena-leaderboard.json
python3 -m json.tool data/arena-leaderboard.json >/dev/null
```

Expected: all tests pass; JSON contains three categories and no category exceeds 20 models.

- [ ] **Step 5: Commit Task 2**

```bash
git add scripts/update_arena_data.py tests/test_update_arena_data.py data/arena-leaderboard.json
git commit -m "生成 Arena 本地排行榜快照"
```

---

### Task 3: Static leaderboard page

**Files:**
- Create: `tests/test_arena_page.py`
- Modify: `arena.html`

**Interfaces:**
- Consumes: `data/arena-leaderboard.json` schema version 1.
- Produces DOM IDs `leaderboard-tabs`, `leaderboard-body`, `snapshot-date`, `leaderboard-status`, and `leaderboard-error`.

- [ ] **Step 1: Write failing page contract tests**

Create tests that parse the page as text and HTML:

```python
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
        for target in ("leaderboard-tabs", "leaderboard-body", "snapshot-date", "leaderboard-status", "leaderboard-error"):
            self.assertIn(f'id="{target}"', self.html)

    def test_page_attributes_upstream_sources(self):
        self.assertIn("oolong-tea-2026/arena-ai-leaderboards", self.html)
        self.assertIn("https://arena.ai/leaderboard", self.html)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest tests.test_arena_page -v`

Expected: failures because the old iframe remains and static render targets do not exist.

- [ ] **Step 3: Replace `arena.html` with the static UI**

Implement a self-contained page matching `index.html` colors and typography. The semantic body must contain:

```html
<main class="shell">
  <section class="hero">
    <p class="eyebrow">Arena snapshot</p>
    <h1>AI 模型<span>静态排行榜</span></h1>
    <p>每日同步公开 Arena 数据；页面直接读取本站快照，不再嵌入第三方网页。</p>
  </section>
  <section class="leaderboard-card" aria-labelledby="leaderboard-title">
    <header class="leaderboard-head">
      <div><h2 id="leaderboard-title">模型排名</h2><p id="leaderboard-status">正在读取本地快照…</p></div>
      <p>数据日期 <strong id="snapshot-date">—</strong></p>
    </header>
    <div id="leaderboard-tabs" class="tabs" role="tablist">
      <button data-category="text" role="tab" aria-selected="true">Text</button>
      <button data-category="code" role="tab" aria-selected="false">Code</button>
      <button data-category="vision" role="tab" aria-selected="false">Vision</button>
    </div>
    <div class="table-wrap"><table><thead><tr><th>排名</th><th>模型</th><th>厂商</th><th>分数</th><th>95% CI</th><th>票数</th></tr></thead><tbody id="leaderboard-body"></tbody></table></div>
    <div id="leaderboard-error" class="error" hidden>本地排行榜暂时不可用。<a href="https://arena.ai/leaderboard">前往 Arena</a></div>
  </section>
</main>
```

The inline script must fetch the local file, render rows with `textContent` (not HTML interpolation), switch tabs, format nullable values as `—`, and reveal `leaderboard-error` on failure.

- [ ] **Step 4: Run page contracts and browser checks**

Run:

```bash
python3 -m unittest tests.test_arena_page -v
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/arena.html` at desktop and 390px mobile widths. Expected: Text loads by default, each tab switches content, top-three rows are highlighted, table scrolls horizontally on mobile, no iframe or console error appears.

- [ ] **Step 5: Commit Task 3**

```bash
git add arena.html tests/test_arena_page.py
git commit -m "改造 Arena 静态排行榜页面"
```

---

### Task 4: Scheduled refresh workflow

**Files:**
- Modify: `tests/test_arena_page.py`
- Create: `.github/workflows/update-arena.yml`

**Interfaces:**
- Consumes: updater CLI and all `unittest` tests.
- Produces: daily and manual refresh commit to `main`.

- [ ] **Step 1: Add failing workflow contract test**

Append:

```python
    def test_update_workflow_contract(self):
        workflow = Path(".github/workflows/update-arena.yml").read_text()
        self.assertIn("cron: '30 6 * * *'", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("python3 scripts/update_arena_data.py", workflow)
        self.assertIn("python3 -m unittest discover -s tests -v", workflow)
        self.assertIn("git diff --quiet -- data/arena-leaderboard.json", workflow)
```

- [ ] **Step 2: Run test and verify RED**

Run: `python3 -m unittest tests.test_arena_page.ArenaPageTests.test_update_workflow_contract -v`

Expected: file-not-found failure.

- [ ] **Step 3: Create the workflow**

Create `.github/workflows/update-arena.yml`:

```yaml
name: Update Arena leaderboard

on:
  schedule:
    - cron: '30 6 * * *'
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: update-arena-leaderboard
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run tests
        run: python3 -m unittest discover -s tests -v
      - name: Refresh snapshot
        run: python3 scripts/update_arena_data.py --output data/arena-leaderboard.json
      - name: Commit changed snapshot
        run: |
          if git diff --quiet -- data/arena-leaderboard.json; then
            echo "Arena snapshot is already current."
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/arena-leaderboard.json
          git commit -m "chore: update Arena leaderboard snapshot"
          git push
```

- [ ] **Step 4: Run complete local verification**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m json.tool data/arena-leaderboard.json >/dev/null
git diff --check
```

Expected: all tests pass, JSON parses, and diff check is clean.

- [ ] **Step 5: Commit Task 4**

```bash
git add .github/workflows/update-arena.yml tests/test_arena_page.py
git commit -m "添加 Arena 每日更新工作流"
```

---

### Task 5: Publish and production verification

**Files:**
- No new files.

**Interfaces:**
- Consumes all prior tasks.
- Produces deployed `https://arctanbell.github.io/arena.html`.

- [ ] **Step 1: Verify branch state and final tests**

Run:

```bash
git status -sb
python3 -m unittest discover -s tests -v
git diff --check
```

Expected: tests pass and only intentional commits are ahead of `origin/main`.

- [ ] **Step 2: Push `main`**

Run: `git push origin main`

Expected: remote `main` advances to local `HEAD`.

- [ ] **Step 3: Monitor Pages deployment**

Use the public Actions API to verify the Pages workflow for the new head SHA completes with `success`.

- [ ] **Step 4: Verify live content**

Fetch `https://arctanbell.github.io/arena.html` with cache busting and confirm:

```text
AI 模型静态排行榜
data-category="text"
data/arena-leaderboard.json
```

Fetch `https://arctanbell.github.io/data/arena-leaderboard.json` and confirm schema version 1 plus Text, Code, and Vision arrays.

- [ ] **Step 5: Manually trigger updater if permission allows**

If authenticated GitHub tooling is available, dispatch `update-arena.yml` and verify it succeeds without creating a commit when the snapshot is already current. If authentication is unavailable, report that scheduled and manual triggers are configured but the first manual dispatch remains for the user.

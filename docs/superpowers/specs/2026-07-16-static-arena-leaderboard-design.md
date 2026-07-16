# Static Arena Leaderboard Design

## Goal

Replace the blocked third-party Arena iframe with a locally hosted static leaderboard that remains usable on GitHub Pages. The page will show the latest public Text, Code, and Vision rankings and update automatically once per day.

## Scope

The first version includes:

- Text, Code, and Vision leaderboard tabs.
- The top 20 models in each category.
- Rank, model name, vendor, Arena score, 95% confidence interval, and vote count.
- A visible data timestamp and source attribution.
- A scheduled GitHub Actions update and a manual workflow trigger.
- A local last-known-good JSON snapshot committed to the repository.

The first version does not include historical charts, ranking change calculations, user-configurable categories, or a database.

## Data Source

The updater reads the daily MIT-licensed JSON snapshots published by:

- Repository: `oolong-tea-2026/arena-ai-leaderboards`
- Latest pointer: `data/latest.json`
- Category snapshots: `data/<date>/text.json`, `code.json`, and `vision.json`

The page will identify this as a community-maintained snapshot of public Arena data and link both the snapshot repository and Arena itself. The local normalized JSON will include the upstream snapshot date, fetch time, and source URLs.

## Architecture

### Updater

`scripts/update_arena_data.py` will use only the Python standard library.

The updater will:

1. Download `data/latest.json` from the upstream repository.
2. Resolve the latest snapshot date.
3. Download Text, Code, and Vision JSON files for that date.
4. Validate the expected `meta` and `models` structures.
5. Normalize the required fields and retain the first 20 ranked models per category.
6. Write `data/arena-leaderboard.json` atomically only after every category succeeds.

Model entries will use this local schema:

```json
{
  "rank": 1,
  "model": "model-name",
  "vendor": "Vendor",
  "license": "proprietary",
  "score": 1400,
  "ci": 5,
  "votes": 10000
}
```

Missing optional values will be written as `null`. Missing ranks or model names will be treated as invalid input.

### Local data file

`data/arena-leaderboard.json` will contain:

- Schema version.
- Upstream snapshot date.
- Fetch timestamp in UTC.
- Source attribution.
- Text, Code, and Vision category metadata and model arrays.

The data file is committed so the page works without runtime access to the upstream service.

### Scheduled workflow

`.github/workflows/update-arena.yml` will:

- Run daily at 06:30 UTC (14:30 Asia/Shanghai).
- Support `workflow_dispatch` for manual refreshes.
- Grant `contents: write` only to the update job.
- Run the updater and its tests.
- Commit and push only when `data/arena-leaderboard.json` changes.

A failed fetch or validation will fail the workflow before the local snapshot is replaced. The last successful committed snapshot therefore remains online.

### Static page

`arena.html` will be redesigned to match the current personal homepage.

The page will:

- Load only `data/arena-leaderboard.json` from the same GitHub Pages origin.
- Default to the Text category.
- Switch between Text, Code, and Vision without navigation.
- Highlight the top three models and render all 20 rows in a responsive table.
- Format scores, confidence intervals, and vote counts consistently.
- Show snapshot date, category model count, and source links.
- Show a concise fallback card with the direct Arena link if the local JSON cannot be loaded.

No external JavaScript framework or runtime API request will be added.

## Error Handling

- Network, HTTP, JSON, or schema errors in the updater terminate with a non-zero exit code.
- The updater writes to a temporary file and replaces the local snapshot only after complete validation.
- An upstream category failure prevents a partial three-category update.
- The page handles missing optional fields with an em dash.
- If the local snapshot is unavailable or malformed, the page displays an error message and an external Arena link instead of an empty table.

## Testing

`tests/test_update_arena_data.py` will use `unittest` and local fixtures to verify:

- Latest snapshot date parsing.
- Category normalization and rank ordering.
- Top-20 truncation.
- Preservation of nullable optional fields.
- Rejection of malformed category data.
- Atomic output behavior on validation failure.

Additional verification will include:

- Running the updater against the current public snapshot.
- Parsing the generated JSON and confirming three categories with at most 20 models each.
- HTML structure and local-anchor audit.
- Desktop and mobile browser screenshots.
- `git diff --check` before publishing.

## Success Criteria

The work is complete when:

1. `arena.html` contains no third-party iframe.
2. Text, Code, and Vision tabs render from the committed local JSON.
3. Each category displays up to 20 ranked models with source and update metadata.
4. The automated tests pass.
5. The scheduled and manual workflow definitions are valid.
6. GitHub Pages deploys successfully and the live Arena page shows the static ranking.

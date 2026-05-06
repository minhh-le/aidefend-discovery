# Monorepo Layout

`aidefend-discovery` is the canonical private working repo for AIDEFEND
discovery, review, and local service integration.

## Surfaces

| Surface | Path | Purpose |
| --- | --- | --- |
| Discovery pipeline | `scripts/`, `lab/aidefend_discovery/`, `reports/` | Ingest public signals, normalize candidates, score against the bundled framework data, and emit candidate-only gap reports. |
| Review console | `review_console/` + `scripts/aidefend_discovery/review_console.py` | Local reviewer workbench over one `gap_run_*.json`, with sqlite decision capture and reviewed-only exports. |
| MCP / REST service | `services/aidefend-mcp/` | Full AIDEFEND MCP/REST service plus optional discovery namespace tools. Discovery responses stay labeled with `discovery_namespace: true`. |
| Framework snapshot | `vendor/aidefense-framework/` | Tracked source snapshot of the AIDEFEND site/data/tactic files used as the default comparison baseline. |

## Defaults

- Discovery commands default `--data-json` to
  `vendor/aidefense-framework/data/data.json`.
- `scripts/anchor_diff.py` also defaults to the bundled framework data.
- `services/aidefend-mcp` defaults `LOCAL_FRAMEWORK_PATH` to the bundled
  framework snapshot and `DISCOVERY_REPORTS_PATH` to the root `reports/`
  directory.
- Set `DISCOVERY_DB_PATH=../../lab/aidefend_discovery/discovery_state.db` from
  `services/aidefend-mcp/` only when you want MCP discovery tools to read a
  local candidate sqlite store. The tracked repo intentionally does not include
  runtime sqlite databases.

## Snapshot Policy

Imported upstream code/data is tracked by source repo URL and commit SHA in
[`vendor/SNAPSHOTS.md`](../../vendor/SNAPSHOTS.md). Refreshes should replace
the plain files, update that manifest, and exclude generated/runtime output.

The repository remains private for now. Do not push to Edward's upstream repos
from this consolidation branch.

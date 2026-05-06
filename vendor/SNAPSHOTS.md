# Imported Snapshots

This monorepo vendors external AIDEFEND sources as plain file snapshots. They
are not submodules and do not include nested Git history or runtime artifacts.

| Path | Source | Commit | License / attribution |
| --- | --- | --- | --- |
| `vendor/aidefense-framework/` | `https://github.com/edward-playground/aidefense-framework` | `e4d5659e03ac087f459350afde0e13161cdf2f93` | AIDEFEND framework content is published under CC BY 4.0; see the upstream README badge and attribution. |
| `services/aidefend-mcp/` | `https://github.com/minhh-le/aidefend-mcp` | `118c56cb8567ccc4eee9df1f766cb018be37963f` | MIT; see `services/aidefend-mcp/LICENSE`. |

Excluded from imports: `.git`, virtualenvs, `node_modules`, Python caches,
pytest/mypy/ruff caches, coverage output, logs, sqlite/runtime databases,
LanceDB runtime output, and lock/cache files under service data directories.

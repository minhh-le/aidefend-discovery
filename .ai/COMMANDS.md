# Commands

Updated: 2026-05-08

## Orientation

```bash
git status --short --branch
find . -maxdepth 3 -type f | sort
```

## AIDEFEND Discovery

```bash
cd /path/to/aidefend-discovery
make demo
python3 scripts/run_demo.py --no-open --port 8878
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v
python3 scripts/run_discovery_gap.py \
  --feed-url https://github.com/langchain-ai/langchain/releases.atom \
  --allowlist lab/aidefend_discovery/feeds.allowlist \
  --max-items 15
python3 scripts/run_discovery_gap.py \
  --source nvd \
  --state-db lab/aidefend_discovery/discovery_state.db \
  --no-fetch-pages \
  --max-items 20
python3 scripts/run_discovery_gap.py \
  --source ghsa \
  --state-db lab/aidefend_discovery/discovery_state.db \
  --ghsa-severity high \
  --no-fetch-pages \
  --max-items 20
# Add hosts to lab/aidefend_discovery/page_fetch.allowlist for Trafilatura fetch.
# Feed-only (no HTTP to article pages): add --no-fetch-pages
python3 scripts/eval_discovery_gold.py --report reports/gap_run_YYYYMMDD.json \
  --gold lab/aidefend_discovery/gold/example_labels.jsonl
python3 scripts/export_review.py --state-db lab/aidefend_discovery/discovery_state.db --output reports/review_export.csv
python3 scripts/discovery_metrics.py --state-db lab/aidefend_discovery/discovery_state.db --output reports/discovery_metrics.json
python3 scripts/export_review_digest.py --report reports/gap_run_YYYYMMDD.json \
  --output reports/discovery_digest_YYYYMMDD.md --top-n 10
python3 scripts/export_review_digest.py --sample --output reports/discovery_digest_sample.md
cd review_console && npm install && npm run build && cd ..
PYTHONPATH=scripts python3 -m aidefend_discovery.review_console \
  --report tests/fixtures/sample_gap_run.json \
  --db lab/aidefend_discovery/review_console.db \
  --port 8765
cd review_console && npm test -- src/App.test.tsx && npm run build && cd ..
cd services/aidefend-mcp && pytest tests/test_discovery_tools.py && cd ../..
```

## Optional Demo Keys

```bash
export NVD_API_KEY=...
export GH_PAT_FOR_GHSA=...   # or GITHUB_TOKEN
export AI_SUMMARY_PROVIDER=openrouter
export AI_SUMMARY_BASE_URL=https://openrouter.ai/api/v1
export AI_SUMMARY_API_KEY=...
export AI_SUMMARY_MODEL=...
make demo
```

The UI also supports a session-only pasted AI API key. Do not write keys to
docs, fixtures, reports, logs, sqlite DBs, or `.ai` files.

## Safety Checks

```bash
# Look for obvious secret-like assignments before commit
python3 - <<'PY'
from pathlib import Path
import re
hits=[]
for p in Path('.').rglob('*'):
    if p.is_file() and '.git' not in p.parts:
        txt=p.read_text(errors='ignore')
        for i,line in enumerate(txt.splitlines(),1):
            if re.search(r'(?i)(api[_-]?key|token|password|secret|refresh_token|client_secret|oauth|cookie)\s*[:=]', line):
                hits.append(f'{p}:{i}:{line[:120]}')
print('secret_like_assignments', hits)
PY
```

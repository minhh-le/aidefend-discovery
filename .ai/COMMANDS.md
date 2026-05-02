# Commands

Updated: 2026-04-30

## Orientation

```bash
git status --short --branch
find . -maxdepth 3 -type f | sort
```

## AIDEFEND Discovery

```bash
cd /path/to/aidefend-discovery
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v
python3 scripts/run_discovery_gap.py \
  --data-json ../aidefense-framework/data/data.json \
  --feed-url https://github.com/langchain-ai/langchain/releases.atom \
  --allowlist lab/aidefend_discovery/feeds.allowlist \
  --max-items 15
# Add hosts to lab/aidefend_discovery/page_fetch.allowlist for Trafilatura fetch.
# Feed-only (no HTTP to article pages): add --no-fetch-pages
python3 scripts/eval_discovery_gold.py --report reports/gap_run_YYYYMMDD.json \
  --gold lab/aidefend_discovery/gold/example_labels.jsonl
```

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

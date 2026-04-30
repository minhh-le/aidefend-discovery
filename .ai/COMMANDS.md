# Commands

Updated: 2026-04-30

## Orientation

```bash
git status --short --branch
find . -maxdepth 3 -type f | sort
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

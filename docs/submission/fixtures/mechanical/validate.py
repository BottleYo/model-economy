import json
from pathlib import Path


paths = sorted(Path(__file__).parent.glob("fixture-*.json"))
if len(paths) != 5:
    raise SystemExit("expected exactly five fixtures")
for path in paths:
    document = json.loads(path.read_text(encoding="utf-8"))
    keys = set(document)
    if keys not in ({"deprecated_key"}, {"current_key"}):
        raise SystemExit(f"unexpected keys: {path.name}")
print("validated 5 fixtures")

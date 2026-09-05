#!/usr/bin/env sh
set -eu

python - <<'PY'
from agent.config import Settings

settings = Settings.from_env()
for path in (settings.input_dir, settings.library_dir, settings.failed_dir, settings.work_dir):
	if not path.exists():
		raise SystemExit(1)
print("ok")
PY

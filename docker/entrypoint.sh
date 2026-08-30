#!/bin/sh
set -eu

python - <<'PY'
import os
import time
import urllib.error
import urllib.request

qdrant_url = (
    f"http://{os.environ['QDRANT_HOST']}:{os.environ['QDRANT_PORT']}/collections"
)
ollama_url = f"{os.environ['OLLAMA_API_BASE'].rstrip('/')}/api/tags"

for service, url in (("Qdrant", qdrant_url), ("Ollama", ollama_url)):
    for attempt in range(60):
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    break
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(2)
    else:
        raise SystemExit(f"{service} is unavailable after 120 seconds: {url}")
PY

exec "$@"


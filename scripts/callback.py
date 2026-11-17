"""POST the render result back to the Make webhook that asked for it."""
import json, os, sys, urllib.parse, urllib.request

path = sys.argv[1]
result = json.load(open(path)) if os.path.exists(path) else {"ok": False, "errors": ["render job failed early"], "urls": []}
result["run_url"] = os.environ.get("RUN_URL", "")
cb = os.environ.get("CALLBACK", "")
host = urllib.parse.urlparse(cb).hostname or ""
if not cb:
    print("no callback (manual run)"); print(json.dumps(result, ensure_ascii=False, indent=2)); sys.exit(0)
if not host.endswith(".make.com"):
    sys.exit(f"refusing callback to non-Make host: {host}")
req = urllib.request.Request(cb, data=json.dumps(result, ensure_ascii=False).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
print(urllib.request.urlopen(req, timeout=30).status)

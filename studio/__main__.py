"""python -m studio <spec.json> [out_dir]

Builds and renders one post spec, writes <out_dir>/manifest.json and exits non-zero if the spec is
invalid or the layout check finds a problem (so nothing broken is ever published).
"""
import json, os, sys
from .build import build, SpecError
from .render import render


def main():
    spec_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "out"
    raw = open(spec_path, encoding="utf-8").read()
    spec = json.loads(raw)
    if isinstance(spec, str):          # Make may send the spec as a JSON string
        spec = json.loads(spec)
    manifest = {"post_code": spec.get("post_code"), "ok": False, "files": [], "errors": []}
    try:
        items = build(spec)
        res = render(items, out_dir)
        manifest["files"] = [os.path.basename(r["file"]) for r in res]
        manifest["errors"] = [f"{os.path.basename(r['file'])}: {w}" for r in res for w in r["warnings"]]
        manifest["ok"] = not manifest["errors"]
    except SpecError as e:
        manifest["errors"] = [str(e)]
    os.makedirs(out_dir, exist_ok=True)
    json.dump(manifest, open(os.path.join(out_dir, "manifest.json"), "w"), ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False))
    sys.exit(0 if manifest["ok"] else 1)


if __name__ == "__main__":
    main()

"""Commit rendered files to renders/<yyyy-mm>/<post_code>/ and wait until GitHub Pages serves them."""
import datetime, json, os, subprocess, sys, time, urllib.request

out = sys.argv[1]
repo = os.environ["REPO"]                       # owner/name
owner, name = repo.split("/")
man = json.load(open(os.path.join(out, "manifest.json"))) if os.path.exists(os.path.join(out, "manifest.json")) \
    else {"ok": False, "errors": ["renderer crashed before writing a manifest"], "files": []}
result = {**man, "urls": []}

if man.get("ok"):
    code = man["post_code"] or "post"
    rel = f"renders/{datetime.date.today():%Y-%m}/{code}"
    os.makedirs(rel, exist_ok=True)
    files = man["files"] + [f for f in os.listdir(out) if f.endswith("_cover.jpg")]
    for f in files:
        os.replace(os.path.join(out, f), os.path.join(rel, f))
    run = lambda *a: subprocess.run(a, check=True)
    run("git", "config", "user.name", "haflati-studio-bot")
    run("git", "config", "user.email", "actions@users.noreply.github.com")
    run("git", "add", rel)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:  # identical re-render: nothing new to commit
        run("git", "commit", "-m", f"render {code}")
    for attempt in range(5):                      # other renders may have pushed meanwhile
        if subprocess.run(["git", "pull", "--rebase", "-q"]).returncode == 0 and \
           subprocess.run(["git", "push", "-q"]).returncode == 0:
            break
        time.sleep(3 + attempt * 3)
    else:
        result.update(ok=False, errors=["could not push rendered files"])
    base = f"https://{owner}.github.io/{name}/{rel}"
    result["urls"] = [f"{base}/{f}" for f in man["files"]]
    result["covers"] = [f"{base}/{f}" for f in files if f.endswith("_cover.jpg")]
    # wait (max ~6 min) until Pages serves the first file, so Instagram can fetch it
    if result["ok"]:
        for _ in range(36):
            try:
                if urllib.request.urlopen(result["urls"][0], timeout=10).status == 200:
                    break
            except Exception:
                pass
            time.sleep(10)
        else:
            result["errors"].append("files committed but GitHub Pages did not serve them within 6 minutes")
            result["ok"] = False

json.dump(result, open(os.path.join(out, "result.json"), "w"), ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))

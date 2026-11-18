"""Schedule a rendered post on Instagram through Zernio, then log the outcome in the repo.

python scripts/schedule.py spec.json out/result.json

The spec may carry:
  caption        Instagram caption (required to schedule)
  scheduled_for  ISO time, e.g. 2026-11-20T12:30:00+04:00 (required unless publish_now)
  publish_now    true to post immediately (tests only)
  dry_run        true to render only and never contact Zernio
  force_schedule true to schedule even when config/mode.txt is not "live" (tests only)
  action         "check_zernio" to only confirm the API key works (lists connected accounts)

Writes the Zernio outcome into result.json and into log/posts/<post_code>.json, which the
daily Make scenario reads to update the Calendar sheet.
"""
import json, os, subprocess, sys, time, urllib.error, urllib.request

API = "https://zernio.com/api/v1"
ACCOUNT_ID = os.environ.get("ZERNIO_ACCOUNT_ID") or "6af96efe1f59630852eba0c2"
KEY = os.environ.get("ZERNIO_API_KEY", "")

spec_path, result_path = sys.argv[1], sys.argv[2]
spec = json.load(open(spec_path, encoding="utf-8"))
if isinstance(spec, str):
    spec = json.loads(spec)
result = json.load(open(result_path)) if os.path.exists(result_path) else \
    {"post_code": spec.get("post_code"), "ok": False, "errors": ["render job failed early"], "urls": []}
result.setdefault("errors", [])


def call(method, path, body=None, idem=None):
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if idem:
        headers["Idempotency-Key"] = idem
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


def save():
    json.dump(result, open(result_path, "w"), ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if spec.get("action") == "check_zernio":
    if not KEY:
        result.update(ok=False, errors=["ZERNIO_API_KEY secret is not available to the workflow"])
    else:
        code, body = call("GET", "/accounts")
        accts = body if isinstance(body, list) else body.get("accounts", [])
        info = body if isinstance(body, dict) else {}
        result.update(ok=code == 200, errors=[] if code == 200 else [f"Zernio answered {code}: {info.get('error') or info.get('message') or ''}"],
                      zernio={"accounts": [{"id": a.get("_id") or a.get("id"), "platform": a.get("platform"),
                                            "username": a.get("username") or a.get("displayName")} for a in accts]})
        result["zernio"]["instagram_account_found"] = any(a["id"] == ACCOUNT_ID for a in result["zernio"]["accounts"])
    save(); sys.exit(0)

try:  # repo-wide switch: anything but "live" renders previews only (safe default)
    MODE = open("config/mode.txt").read().strip().lower()
except OSError:
    MODE = "preview"
if MODE != "live" and not spec.get("force_schedule"):
    spec["dry_run"] = True

want = spec.get("caption") and (spec.get("scheduled_for") or spec.get("publish_now"))
if not want or spec.get("dry_run"):
    result["zernio"] = {"status": "preview" if spec.get("dry_run") else "not_scheduled",
                        "reason": f"mode is {MODE!r}, not 'live'" if spec.get("dry_run") else "no caption/time in spec"}
elif not result.get("ok"):
    result["zernio"] = {"status": "not_scheduled", "reason": "render or layout check failed"}
elif not KEY:
    result.update(ok=False); result["errors"].append("ZERNIO_API_KEY secret is not available to the workflow")
else:
    is_reel = spec.get("format") == "reel"
    media = [{"url": u, "type": "video" if u.endswith(".mp4") else "image"} for u in result["urls"]]
    platform = {"platform": "instagram", "accountId": ACCOUNT_ID}
    if is_reel:
        psd = {"shareToFeed": True}
        if result.get("covers"):
            psd["instagramThumbnail"] = result["covers"][0]
        platform["platformSpecificData"] = psd
    body = {"content": spec["caption"], "mediaItems": media, "platforms": [platform],
            "metadata": {"post_code": result.get("post_code")}}
    if spec.get("publish_now"):
        body["publishNow"] = True
    else:
        body["scheduledFor"] = spec["scheduled_for"]
        body["timezone"] = "Asia/Dubai"
    code, resp = call("POST", "/posts", body, idem=f"haflati-{result.get('post_code')}-{spec.get('scheduled_for', 'now')}")
    post = resp.get("post") or {}
    status = post.get("status")
    good = code in (200, 201) and status not in ("failed", "partial")
    result["zernio"] = {"http": code, "post_id": post.get("_id"), "status": status,
                        "message": resp.get("message") or resp.get("error"),
                        "warnings": resp.get("warnings"), "scheduled_for": spec.get("scheduled_for")}
    if not good:
        result["ok"] = False
        result["errors"].append(f"Zernio did not accept the post ({code}): {resp.get('error') or resp.get('message') or status}")

save()

# Log for the daily Make sync (best effort: the callback still carries the same result)
code = result.get("post_code") or "post"
os.makedirs("log/posts", exist_ok=True)
entry = {k: result.get(k) for k in ("post_code", "ok", "errors", "urls", "covers", "zernio")}
entry.update(lang=spec.get("lang"), format=spec.get("format"), logged_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(entry, open(f"log/posts/{code}.json", "w"), ensure_ascii=False, indent=2)
run = lambda *a: subprocess.run(a)
run("git", "config", "user.name", "haflati-studio-bot")
run("git", "config", "user.email", "actions@users.noreply.github.com")
run("git", "add", f"log/posts/{code}.json")
if run("git", "commit", "-q", "-m", f"log {code}").returncode == 0:
    for attempt in range(5):
        if run("git", "pull", "--rebase", "-q").returncode == 0 and run("git", "push", "-q").returncode == 0:
            break
        time.sleep(3 + attempt * 3)

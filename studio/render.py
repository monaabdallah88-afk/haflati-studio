"""Render documents from layouts.py to JPG (stills) or MP4 (reels) with headless Chromium.

Also runs a layout check on every render: text running off the canvas or two text blocks
overlapping fails the render, so a bad post never reaches Instagram.
"""
import asyncio, base64, html, json, os, re, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(HERE, "assets", "fonts")
LOGO_SVG = open(os.path.join(HERE, "assets", "logo.svg"), encoding="utf-8").read()
LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode()

_FACES = [("DM Serif Display", "dm-serif-display-latin-400-normal", 400, "normal"),
          ("DM Serif Display", "dm-serif-display-latin-400-italic", 400, "italic")]
_FACES += [("DM Sans", f"dm-sans-latin-{w}-{s}", w, s) for w in (400, 500, 700) for s in ("normal", "italic")]
_FACES += [("JetBrains Mono", f"jetbrains-mono-latin-{w}-normal", w, "normal") for w in (400, 500)]
_FACES += [("Tajawal", f"tajawal-{sub}-{w}-normal", w, "normal") for w in (400, 500, 700, 800) for sub in ("arabic", "latin")]


def _font_css():
    out = []
    for fam, f, w, s in _FACES:
        data = base64.b64encode(open(os.path.join(FONTS_DIR, f + ".woff2"), "rb").read()).decode()
        out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{s};"
                   f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "\n".join(out)

FONT_CSS = _font_css()


def px(v, ref=0):
    v = str(v).strip()
    if v.endswith("px"): return float(v[:-2])
    if v.endswith("%"): return float(v[:-1]) / 100 * ref
    return float(v)


def pct(v):
    return float(str(v).rstrip("%")) / 100


def spans(s):
    s = html.escape(s)
    s = s.replace("[style italic]", "<i>").replace("[/style]", "</i>")
    s = re.sub(r"\[color (#[0-9A-Fa-f]{6})\]", r'<span style="color:\1">', s).replace("[/color]", "</span>")
    return s


SHADOW = {"light": "text-shadow:0 2px 3px rgba(20,14,10,.35),0 4px 28px rgba(20,14,10,.45)",
          "dark": "text-shadow:0 1px 18px rgba(252,243,232,.55)"}


def gradient(e):
    y0, y1 = pct(e.get("fill_y0", "0%")), pct(e.get("fill_y1", "100%"))
    stops = ", ".join(f"{st['color']} {100 * (y0 + pct(st['offset']) * (y1 - y0)):.1f}%" for st in e["fill_color"])
    return f"linear-gradient(to bottom, {stops})"


def el_html(e, pw, ph, idx):
    w = px(e["width"], pw) if e.get("width") else None
    h = px(e["height"], ph) if e.get("height") else None
    x, y = px(e.get("x", "50%"), pw), px(e.get("y", "50%"), ph)
    xa, ya = pct(e.get("x_anchor", "50%")), pct(e.get("y_anchor", "50%"))
    attrs = f'id="e{idx}" data-anim=\'{html.escape(json.dumps(e.get("anim", {})))}\''
    if e.get("_in_stack"):   # laid out by the parent stack (flex column), only spacing applies
        pos = f"position:relative;flex:none;margin-top:{e.get('_gap', 0)}px;align-self:{e.get('_align', 'center')};"
    else:
        pos = f"position:absolute;left:{x}px;top:{y}px;transform:translate({-xa * 100}%,{-ya * 100}%);"
    t = e["type"]
    if t == "stack":
        kids = "".join(el_html({**c, "_in_stack": True, "_gap": (0 if i == 0 else c.get("gap", e.get("gap", 24))),
                                "_align": c.get("align_self", "center")}, w, ph, f"{idx}_{i}")
                       for i, c in enumerate(e["children"]))
        return f'<div {attrs} style="{pos}width:{w}px;display:flex;flex-direction:column">{kids}</div>'
    if t == "image":
        r = px(e.get("border_radius", "0 px"))
        if e["source"] == "logo":
            if e.get("color_overlay"):
                return (f'<div {attrs} style="{pos}width:{w}px;height:{h}px;background:{e["color_overlay"]};'
                        f'-webkit-mask:url({LOGO_URI}) center/contain no-repeat;mask:url({LOGO_URI}) center/contain no-repeat"></div>')
            return f'<img {attrs} src="{LOGO_URI}" style="{pos}width:{w}px;height:{h}px;object-fit:contain">'
        src = e["source"]
        if os.environ.get("OFFLINE_PHOTOS"):
            svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='1000'><defs><linearGradient id='g' x2='1' y2='1'>"
                   "<stop offset='0' stop-color='#f4a7c0'/><stop offset='1' stop-color='#f7d36b'/></linearGradient></defs>"
                   "<rect width='800' height='1000' fill='url(#g)'/><circle cx='400' cy='620' r='200' fill='#fff' opacity='.6'/></svg>")
            src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
        return (f'<div {attrs} class="ph" style="{pos}width:{w}px;height:{h}px;border-radius:{r}px;overflow:hidden">'
                f'<img src="{src}" style="width:100%;height:100%;object-fit:cover;transform-origin:50% 50%"></div>')
    if t == "shape":
        r = px(e.get("border_radius", "0 px"))
        rect = e["path"].startswith("M 0 0 L 100 0 L 100 100 L 0 100 Z")
        if e.get("fill_mode") == "linear":
            return f'<div {attrs} style="{pos}width:{w}px;height:{h}px;background:{gradient(e)};border-radius:{r}px"></div>'
        if rect and not e.get("stroke_color"):
            return f'<div {attrs} style="{pos}width:{w}px;height:{h}px;background:{e["fill_color"]};border-radius:{r}px"></div>'
        if rect and e.get("stroke_color"):
            sw = px(e["stroke_width"])
            return (f'<div {attrs} style="{pos}width:{w}px;height:{h}px;border-radius:{r}px;box-sizing:border-box;'
                    f'border:{sw}px solid {e["stroke_color"]};background:{e.get("fill_color") or "none"}"></div>')
        stroke = ""
        if e.get("stroke_color"):
            stroke = (f'stroke="{e["stroke_color"]}" stroke-width="{px(e["stroke_width"])}" stroke-linecap="round" '
                      f'stroke-linejoin="round" vector-effect="non-scaling-stroke"')
        return (f'<svg {attrs} style="{pos}overflow:visible" width="{w}" height="{h}" viewBox="0 0 100 100" '
                f'preserveAspectRatio="none"><path d="{e["path"]}" fill="{e.get("fill_color") or "none"}" {stroke}/></svg>')
    if t == "text":
        al = {"0%": "left", "50%": "center", "100%": "right"}[e["x_alignment"]]
        lh = pct(e["line_height"])
        ls = pct(e["letter_spacing"]) / 10
        return (f'<div {attrs} class="tx" dir="{e["text_direction"]}" style="{pos}width:{w}px;'
                f'font-family:\'{e["font_family"]}\';font-weight:{e["font_weight"]};font-style:{e.get("font_style", "normal")};'
                f'font-size:{px(e["font_size"])}px;line-height:{lh};letter-spacing:{ls}em;color:{e["fill_color"]};'
                f'text-align:{al};font-kerning:normal;{SHADOW.get(e.get("shadow"), "")}" data-color="{" ".join([e["fill_color"]] + re.findall(r"\[color (#[0-9A-Fa-f]{6})\]", e["text"]))}" '
                f'data-size="{px(e["font_size"])}">{spans(e["text"])}</div>')
    raise ValueError(t)


ANIM_JS = """
window.__frame = (t) => {
  const ease = x => 1 - Math.pow(1 - Math.min(Math.max(x, 0), 1), 3);
  for (const el of document.querySelectorAll('[data-anim]')) {
    const a = JSON.parse(el.dataset.anim || '{}'); if (!a.type) continue;
    if (a.type === 'zoom') { const D = window.__dur; const s = a.from + (a.to - a.from) * (t / D);
      el.querySelector('img').style.transform = `scale(${s})`; continue; }
    const p = ease((t - a.start) / a.dur);
    const base = el.style.transform.replace(/ translateY\\([^)]*\\)| scale\\([^)]*\\)/g, '');
    el.style.opacity = p;
    if (a.type === 'fade_up') el.style.transform = base + ` translateY(${(1 - p) * 40}px)`;
    if (a.type === 'pop') el.style.transform = base + ` scale(${0.4 + 0.6 * p})`;
  }
};
window.__check = () => {
  const W = document.body.clientWidth, H = document.body.clientHeight, out = [];
  const tx = [...document.querySelectorAll('.tx')].map(el => {
    const r = document.createRange(); r.selectNodeContents(el);
    const b = [...r.getClientRects()]; if (!b.length) return null;
    const box = el.getBoundingClientRect();   // vertical extent = line boxes (line-height), horizontal = actual glyphs
    return {el, l: Math.min(...b.map(x => x.left)), t: box.top, r: Math.max(...b.map(x => x.right)), b: box.bottom,
            s: el.innerText.slice(0, 40)};
  }).filter(Boolean);
  for (const a of tx) if (a.l < 20 || a.t < 20 || a.r > W - 20 || a.b > H - 20) out.push('off-canvas: ' + a.s);
  for (let i = 0; i < tx.length; i++) for (let j = i + 1; j < tx.length; j++) {
    const a = tx[i], b = tx[j];
    if (a.l < b.r - 4 && b.l < a.r - 4 && a.t < b.b - 4 && b.t < a.b - 4) out.push(`overlap: "${a.s}" / "${b.s}"`);
  }
  return out;
};
"""


def page(doc):
    body = "".join(el_html(e, doc["width"], doc["height"], i) for i, e in enumerate(doc["elements"]))
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{FONT_CSS}*{{margin:0;padding:0}}'
            f'body{{width:{doc["width"]}px;height:{doc["height"]}px;position:relative;overflow:hidden;'
            f'background:{doc["fill_color"]}}}</style><script>window.__dur={doc.get("duration", 0)};{ANIM_JS}</script>'
            f'</head><body>{body}</body></html>')


async def _ready(pg):
    await pg.evaluate("document.fonts.ready")
    await pg.wait_for_function("[...document.images].every(i => i.complete && i.naturalWidth > 0)", timeout=60000)


def _lum(rgb):
    def c(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)


async def contrast_problems(pg):
    """Screenshot the background behind every text block (text hidden) and compare it with the text colour.
    Uses the worst 10% of background pixels, so a light patch behind white text is caught."""
    from PIL import Image
    import io
    boxes = await pg.evaluate("""[...document.querySelectorAll('.tx')].map(el => { const r = el.getBoundingClientRect();
        return {x: r.left, y: r.top, w: r.width, h: r.height, c: el.dataset.color, s: +el.dataset.size, t: el.innerText.slice(0, 40)}; })""")
    await pg.add_style_tag(content=".tx{visibility:hidden !important}")
    out = []
    for b in boxes:
        if b["w"] < 2 or b["h"] < 2:
            continue
        shot = await pg.screenshot(clip={"x": max(b["x"], 0), "y": max(b["y"], 0), "width": b["w"], "height": b["h"]})
        px_ = sorted(_lum(p) for p in Image.open(io.BytesIO(shot)).convert("RGB").resize((60, 20)).getdata())
        need = 3.0 if b["s"] >= 48 else 4.5
        for c in b["c"].split():          # main colour + every accent colour used in the block
            c = c.lstrip("#")
            tl = _lum(tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)))
            bg = px_[int(len(px_) * 0.9)] if tl > 0.5 else px_[int(len(px_) * 0.1)]
            ratio = (max(tl, bg) + 0.05) / (min(tl, bg) + 0.05)
            if ratio < need:
                out.append(f'low contrast {ratio:.1f}:1 (needs {need}:1) for #{c}: {b["t"]}')
    await pg.evaluate("document.querySelectorAll('style').forEach(s => { if (s.textContent.includes('.tx{visibility')) s.remove(); })")
    return out


async def render_all(items, out_dir):
    """items: list of (stem, doc). Returns list of dicts {file, warnings}."""
    from playwright.async_api import async_playwright
    os.makedirs(out_dir, exist_ok=True)
    results = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for stem, doc in items:
            pg = await b.new_page(viewport={"width": doc["width"], "height": doc["height"]})
            await pg.set_content(page(doc), wait_until="load")
            await _ready(pg)
            if doc["output_format"] == "mp4":
                await pg.evaluate(f"__frame({doc['duration']})")
                warnings = await pg.evaluate("__check()") + await contrast_problems(pg)
                path = os.path.join(out_dir, stem + ".mp4")
                fps, n = doc.get("frame_rate", 30), int(doc["duration"] * doc.get("frame_rate", 30))
                ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
                                       "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                                       "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
                for i in range(n):
                    await pg.evaluate(f"__frame({i / fps})")
                    ff.stdin.write(await pg.screenshot(type="jpeg", quality=95))
                ff.stdin.close(); ff.wait()
                # poster frame for the grid / QA
                await pg.evaluate(f"__frame({doc['duration']})")
                await pg.screenshot(path=os.path.join(out_dir, stem + "_cover.jpg"), type="jpeg", quality=92)
            else:
                path = os.path.join(out_dir, stem + ".jpg")
                await pg.screenshot(path=path, type="jpeg", quality=92)
                warnings = await pg.evaluate("__check()") + await contrast_problems(pg)
            await pg.close()
            results.append({"file": path, "warnings": warnings})
        await b.close()
    return results


def render(items, out_dir):
    return asyncio.run(render_all(items, out_dir))

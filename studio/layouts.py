"""Haflati Instagram layouts.

Every format returns a RenderScript-style dict (canvas + positioned elements).
render.py turns that dict into a JPG (stills) or MP4 (reels).
Brand system taken from haflati.ae and @haflati.ae: DM Serif Display headlines with one
italic coloured accent word, DM Sans body, JetBrains Mono eyebrows, Tajawal Arabic;
cream / lilac / peach / gold / green / ink; sunbursts, sparkles, smileys, the real logo.
"""
import math

W, H = 1080, 1350
CREAM, LILAC, GOLD, GREEN, PEACH, INK, WHITE = "#FCF3E8", "#D5B6E8", "#E4B03A", "#2F6A3E", "#EFB089", "#2C221B", "#FFFFFF"
BANDS = {"cream": CREAM, "lilac": LILAC, "peach": PEACH}
SERIF, SANS, MONO, AR = "DM Serif Display", "DM Sans", "JetBrains Mono", "Tajawal"
M = 96  # outer margin

LOGO_RATIO = 93.17 / 484.32
def logo(x, y, w, mono=None, anchor_right=False):
    """The real Haflati logo (assets/logo.svg). mono = single colour version (e.g. white on photos)."""
    e = {"type": "image", "source": "logo", "x": f"{x} px", "y": f"{y} px", "width": f"{w} px",
         "height": f"{round(w * LOGO_RATIO, 1)} px", "x_anchor": "100%" if anchor_right else "0%", "y_anchor": "0%",
         "fit": "contain"}
    if mono: e["color_overlay"] = mono
    return e

# ---------- primitives ----------
def box(x, y, w, h, path, fill=None, stroke=None, sw=0, xa="0%", ya="0%", r=None):
    e = {"type": "shape", "x": f"{x} px", "y": f"{y} px", "width": f"{w} px", "height": f"{h} px",
         "x_anchor": xa, "y_anchor": ya, "path": path, "fill_color": fill}
    if stroke: e.update({"stroke_color": stroke, "stroke_width": f"{sw} px", "stroke_cap": "round", "stroke_join": "round"})
    if r is not None: e["border_radius"] = f"{r} px"
    return e

RECT = "M 0 0 L 100 0 L 100 100 L 0 100 Z"
def rect(x, y, w, h, fill, r=0): return box(x, y, w, h, RECT, fill, r=r)
def circle(cx, cy, d, fill): return box(cx, cy, d, d, RECT, fill, xa="50%", ya="50%", r=d / 2)
def rule(x, y, w, color, t=2): return rect(x, y, w, t, color)

def sparkle(cx, cy, s, color):
    return box(cx, cy, s, s, "M 50 0 C 54 38 62 46 100 50 C 62 54 54 62 50 100 C 46 62 38 54 0 50 C 38 46 46 38 50 0 Z",
               color, xa="50%", ya="50%")

def sunburst(cx, cy, s, ray=GREEN, core=GOLD, dot=INK):
    rays = " ".join(
        f"M {50 + 30 * math.cos(a):.2f} {50 + 30 * math.sin(a):.2f} L {50 + 48 * math.cos(a):.2f} {50 + 48 * math.sin(a):.2f}"
        for a in [i * math.pi / 8 for i in range(16)])
    return [box(cx, cy, s, s, rays, None, ray, s * 0.035, "50%", "50%"),
            circle(cx, cy, s * 0.36, core), circle(cx, cy, s * 0.14, dot)]

def smiley(cx, cy, d, face, ink=INK, mood="happy"):
    e = d * 0.11
    q = "M 0 0 Q 50 100 100 0" if mood == "happy" else "M 0 50 L 100 50"
    return [circle(cx, cy, d, face), circle(cx - d * 0.17, cy - d * 0.08, e, ink), circle(cx + d * 0.17, cy - d * 0.08, e, ink),
            box(cx, cy + d * 0.14, d * 0.42, d * 0.16, q, None, ink, d * 0.075, "50%", "50%")]

def wavy(x, y, w, color, sw=8):
    n = 6
    d = "M 0 50 " + " ".join(f"Q {(i + .5) * 100 / n:.2f} {0 if i % 2 == 0 else 100} {(i + 1) * 100 / n:.2f} 50" for i in range(n))
    return box(x, y, w, 26, d, None, color, sw)

def text(x, y, w, s, font, size, color, weight="400", lh=110, ls=0, align="left", rtl=False, style="normal", **kw):
    e = {"type": "text", "text": s, "x": f"{x} px", "y": f"{y} px", "width": f"{w} px", "x_anchor": "0%", "y_anchor": "0%",
         "font_family": font, "font_weight": weight, "font_size": f"{size} px", "font_style": style,
         "line_height": f"{lh}%", "letter_spacing": f"{ls}%", "fill_color": color,
         "x_alignment": {"left": "0%", "center": "50%", "right": "100%"}[align], "y_alignment": "0%",
         "text_direction": "rtl" if rtl else "ltr"}
    e.update(kw)
    return e

def acc(word, color):  # italic accent word, as on the existing posts
    return f"[style italic][color {color}]{word}[/color][/style]"

def pill(x, y, label, face, bg=CREAM, w=None):
    w = w or (len(label) * 15.5 + 110)
    return [rect(x, y, w, 64, bg, 32), *smiley(x + 38, y + 32, 28, face, WHITE if face == GREEN else INK),
            text(x + 66, y + 17, w - 80, label, SANS, 27, INK, "500")]

def footer(dark=False, note=None, note_color=GREEN):
    els = [logo(W - M, H - 112, 250, mono=WHITE if dark else None, anchor_right=True)]
    if note: els.append(text(M, H - 100, 560, note, SANS, 24, note_color, "500"))
    return els

def doc(bg, els):
    return {"output_format": "jpg", "width": W, "height": H, "fill_color": bg, "elements": els}

# ---------- formats ----------
def f_statement(head, ar_eyebrow, cats, note):
    els = [*smiley(M + 18, 150, 40, LILAC), *sunburst(W - M - 40, 150, 92),
           text(M, 128, W - 2 * M - 120, ar_eyebrow, AR, 34, GREEN, "700", align="right", rtl=True),
           text(M, 330, W - 2 * M, head, SERIF, 140, INK, lh=100, ls=-10),
           rule(M, 1010, W - 2 * M, "#E4D7C6"),
           text(M, 1050, W - 2 * M, "  ·  ".join(cats).upper(), MONO, 26, INK, "500", ls=80),
           *footer(note=note)]
    return doc(CREAM, els)

def f_problem(head, items, tagline):
    els = [*sunburst(W - M - 40, 150, 100, ray=INK, core=GOLD, dot=INK), sparkle(W - M - 40, 330, 46, CREAM),
           text(M, 230, 760, head, SERIF, 116, INK, lh=104, ls=-10)]
    y = 640
    for it in items:
        els += smiley(M + 18, y + 22, 34, PEACH, INK, mood="flat")
        els += [box(M + 18, y + 22, 34, 34, RECT, None, INK, 2.5, "50%", "50%", r=17)]
        els.append(text(M + 56, y, 760, it, SANS, 38, INK, "400"))
        y += 66
    els += [rule(M, y + 30, 640, INK), text(M, y + 60, 800, tagline, SERIF, 38, INK, style="italic"),
            *footer(dark=True)]
    return doc(PEACH, els)

def f_chips(eyebrow, head, chips, sign_off):
    faces = [GOLD, GREEN, LILAC, PEACH]
    els = [*sunburst(M + 40, 150, 92, ray=INK, core=GOLD, dot=INK), sparkle(W - M - 30, 140, 50, GREEN),
           text(M, 330, 800, eyebrow, SERIF, 42, INK, style="italic"),
           text(M, 400, W - 2 * M, head, SERIF, 104, INK, lh=104, ls=-10)]
    cx, cy = M, 830
    for i, c in enumerate(chips):
        w = len(c) * 15.5 + 110
        if cx + w > W - M: cx, cy = M, cy + 88
        els += pill(cx, cy, c, faces[i % 4], w=w)
        cx += w + 20
    els += [text(M, cy + 130, 700, sign_off, SERIF, 40, INK, style="italic"), *footer(dark=True)]
    return doc(LILAC, els)

def f_bilingual(en_head, ar_head, ar_sub):
    els = [*sunburst(M + 40, 150, 92, ray=INK, core=GOLD, dot=INK), sparkle(W - M - 40, 230, 46, GOLD),
           text(M, 300, W - 2 * M, en_head, SERIF, 100, INK, lh=104, ls=-10),
           rule(M, 640, 90, INK, 3),
           text(M, 700, W - 2 * M, ar_head, AR, 84, INK, "800", lh=130, align="right", rtl=True),
           text(M, 830, W - 2 * M, ar_sub, AR, 44, INK, "400", lh=150, align="right", rtl=True),
           *smiley(M + 30, 1040, 56, GREEN, WHITE), *footer(dark=True)]
    return doc(LILAC, els)

def f_hero(line1, word, eyebrow, w_word):
    els = [sparkle(150, 170, 34, LILAC), sparkle(W - 150, 330, 40, GOLD), sparkle(170, H - 330, 30, GOLD),
           sparkle(W - 170, H - 420, 34, LILAC),
           text(M, 470, W - 2 * M, line1, SERIF, 120, INK, lh=100, align="center", ls=-10),
           text(M, 600, W - 2 * M, f"[style italic]{word}[/style]?", SERIF, 210, GREEN, lh=100,
                align="center", ls=-20),
           wavy((W - w_word) / 2, 790, w_word, GOLD, 9),
           text(M, 900, W - 2 * M, eyebrow.upper(), MONO, 24, "#6E6258", "500", align="center", ls=160),
           logo(W / 2 + 125, H - 140, 250, anchor_right=True)]
    return doc(CREAM, els)


def photo(url, x, y, w, h, r=0):
    return {"type": "image", "source": url, "x": f"{x} px", "y": f"{y} px", "width": f"{w} px", "height": f"{h} px",
            "x_anchor": "0%", "y_anchor": "0%", "fit": "cover", "border_radius": f"{r} px"}

def pexels(pid):
    return f"https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg?auto=compress&cs=tinysrgb&w=1400"

def f_arch(bg, eyebrow, head, sub, pid, note, rtl=False, outline=GOLD, ink=INK):
    aw, ay = 540, 470
    ah = H - ay + aw // 2 + 40          # bottom curve falls off the canvas -> flat-bottom arch
    ax = M if rtl else W - M - aw
    off = 24 if rtl else -24
    tx, tw = (ax + aw + 48, W - M - (ax + aw + 48)) if rtl else (M, ax - M - 48)
    al = "right" if rtl else "left"
    if rtl:
        top = [text(M, 120, W - 2 * M, eyebrow, AR, 34, GREEN if bg == CREAM else INK, "700", align="right", rtl=True),
               text(M, 185, W - 2 * M, head, AR, 92, ink, "800", lh=125, align="right", rtl=True),
               text(tx, ay + 70, tw, sub, AR, 38, ink, "400", lh=150, align="right", rtl=True)]
    else:
        top = [text(M, 120, W - 2 * M, eyebrow.upper(), MONO, 24, ink, "500", ls=120),
               text(M, 175, W - 2 * M, head, SERIF, 104, ink, lh=100, ls=-10),
               text(tx, ay + 70, tw, sub, SANS, 34, ink, "400", lh=135)]
    els = [box(ax + off, ay + off, aw, ah, RECT, None, outline, 4, r=aw / 2),
           photo(pexels(pid), ax, ay, aw, ah, r=aw / 2),
           *sunburst(ax + (aw if rtl else 0), ay + 90, 96),
           sparkle((W - M - 30) if rtl else (M + 30), ay + 420, 34, GOLD), sparkle((W - M - 120) if rtl else (M + 150), ay + 500, 22, WHITE if bg != CREAM else LILAC),
           *top,
           text(tx, H - 190, tw, note, AR if rtl else SANS, 28 if rtl else 24, GREEN if (rtl and bg == CREAM) else (GREEN if bg == CREAM else INK),
                "700" if rtl else "500", align=al, rtl=rtl),
           logo(W - M if rtl else M, H - 120, 230, anchor_right=rtl)]
    return doc(bg, els)

def scrim(zone, tone, w, h):
    """Contrast layer between photo and text: dark fade under white text, light veil under dark text."""
    if tone == "light":
        stops = [{"offset": "0%", "color": "rgba(28,20,14,0)"}, {"offset": "100%", "color": "rgba(28,20,14,0.78)"}]
        y0, y1 = ("35%", "100%") if zone == "bottom" else ("45%", "0%")
    else:
        stops = [{"offset": "0%", "color": "rgba(252,243,232,0)"}, {"offset": "100%", "color": "rgba(252,243,232,0.62)"}]
        y0, y1 = ("40%", "100%") if zone == "bottom" else ("50%", "0%")
    if zone == "top":
        stops = [{"offset": "0%", "color": stops[1]["color"]}, {"offset": "100%", "color": stops[0]["color"]}]
        y0, y1 = y1, y0
    return {**rect(0, 0, w, h, None), "fill_mode": "linear", "fill_x0": "50%", "fill_y0": y0, "fill_x1": "50%",
            "fill_y1": y1, "fill_color": stops}


def f_photo_line(pid, line, rtl=False, sub=None, zone="bottom", tone="light"):
    """Floward-style: full-bleed photo, one short line placed in the photo's empty area.
    zone/tone come from the photo library (text_zone, text_tone)."""
    ink = WHITE if tone == "light" else INK
    sh = {"shadow": tone}
    els = [photo(pexels(pid), 0, 0, W, H), scrim(zone, tone, W, H)]
    y = 130 if zone == "top" else H - 430
    els.append(sparkle(W / 2, y - 45, 30, GOLD))
    if rtl:
        els.append(text(M, y, W - 2 * M, line, AR, 74, ink, "800", lh=130, align="center", rtl=True, **sh))
        if sub: els.append(text(M, y + 200, W - 2 * M, sub, AR, 34, ink, "700", align="center", rtl=True, **sh))
    else:
        els.append(text(M, y, W - 2 * M, line, SERIF, 84, ink, lh=104, align="center", ls=-10, **sh))
        if sub: els.append(text(M, y + 222, W - 2 * M, sub.upper(), MONO, 26, ink, "500", align="center", ls=120, **sh))
    ly = (y + 285) if zone == "top" else (H - 115)
    els.append(logo(W / 2 + 115, ly, 230, mono=WHITE if tone == "light" else INK, anchor_right=True))
    return doc(INK, els)

def f_split(pid, eyebrow, head, band=PEACH, rtl=False):
    """Photo on top, solid brand-colour band below with the headline; sunburst on the seam."""
    py = 830
    els = [photo(pexels(pid), 0, 0, W, py), rect(0, py, W, H - py, band),
           *sunburst(W - M - 50 if not rtl else M + 50, py, 110)]
    if rtl:
        els += [text(M, py + 80, W - 2 * M, eyebrow, AR, 32, INK if band == LILAC else GREEN, "700", align="right", rtl=True),
                text(M, py + 130, W - 2 * M, head, AR, 68, INK, "800", lh=125, align="right", rtl=True),
                logo(M, H - 110, 210)]
    else:
        els += [text(M, py + 80, W - 2 * M, eyebrow.upper(), MONO, 22, INK, "500", ls=120),
                text(M, py + 125, W - 2 * M, head, SERIF, 86, INK, lh=100, ls=-10),
                logo(W - M, H - 110, 210, mono=INK if band == PEACH else None, anchor_right=True)]
    return doc(band, els)

def f_framed(pid, caption, frame=LILAC, rtl=False, accent=WHITE):
    """Photo inset in a thick brand-colour frame, caption underneath, smiley sticker on the corner."""
    fx, fy, fw, fh = 72, 72, W - 144, 1000
    els = [photo(pexels(pid), fx, fy, fw, fh, r=28),
           *smiley(fx + fw - 30 if not rtl else fx + 30, fy + fh - 10, 96, GOLD),
           text(fx, fy + fh + 60, fw, caption, AR if rtl else SERIF, 52 if rtl else 60, INK,
                "800" if rtl else "400", lh=110, align="right" if rtl else "left", rtl=rtl),
           logo(fx if rtl else fx + fw, H - 100, 200, mono=INK if frame == PEACH else None, anchor_right=not rtl)]
    return doc(frame, els)


# ---------------------------------------------------------------- reels (1080x1920)
RW, RH = 1080, 1920

def f_reel(pid, line, rtl=False, sub=None, zone="bottom", tone="light", duration=7.0):
    """Animated still: slow push-in on the photo, sparkle + headline + sub fade up, logo lands last."""
    ink = WHITE if tone == "light" else INK
    sh = {"shadow": tone}
    els = [{**photo(pexels(pid), 0, 0, RW, RH), "anim": {"type": "zoom", "from": 1.0, "to": 1.09}}, scrim(zone, tone, RW, RH)]
    y = 300 if zone == "top" else RH - 900   # keep clear of the Reels caption/buttons area
    els.append({**sparkle(RW / 2, y - 60, 40, GOLD), "anim": {"type": "pop", "start": 0.5, "dur": 0.5}})
    if rtl:
        els.append({**text(M, y, RW - 2 * M, line, AR, 88, ink, "800", lh=130, align="center", rtl=True, **sh),
                    "anim": {"type": "fade_up", "start": 0.8, "dur": 0.9}})
        if sub: els.append({**text(M, y + 250, RW - 2 * M, sub, AR, 40, ink, "700", align="center", rtl=True, **sh),
                            "anim": {"type": "fade_up", "start": 1.6, "dur": 0.8}})
    else:
        els.append({**text(M, y, RW - 2 * M, line, SERIF, 100, ink, lh=104, align="center", ls=-10, **sh),
                    "anim": {"type": "fade_up", "start": 0.8, "dur": 0.9}})
        if sub: els.append({**text(M, y + 260, RW - 2 * M, sub.upper(), MONO, 32, ink, "500", align="center", ls=110, **sh),
                            "anim": {"type": "fade_up", "start": 1.6, "dur": 0.8}})
    els.append({**logo(RW / 2 + 140, y + 350, 280, mono=WHITE if tone == "light" else INK, anchor_right=True),
                "anim": {"type": "fade_up", "start": 2.4, "dur": 0.8}})
    return {"output_format": "mp4", "width": RW, "height": RH, "fill_color": INK, "duration": duration,
            "frame_rate": 30, "elements": els}

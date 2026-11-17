"""Turn one post spec (written by the weekly planner, sent by Make) into render documents.

Spec fields (all text already approved by the planner/QA step):
  post_code   unique id, used for file names
  format      statement | problem | chips | bilingual | hero | arch | photo_line | split | framed | carousel | reel
  lang        en | ar
  headline    accent word wrapped in *stars*, e.g. "Your work deserves to be *found.*"
  ...         format-specific fields, see FORMAT_FIELDS below
Photos are referenced by pexels_id and must exist in assets/photo_library.csv; the library supplies
text_zone / text_tone so text never lands on the product.
"""
import csv, os, re
from . import layouts as L

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = {r["pexels_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "assets", "photo_library.csv"), encoding="utf-8"))}

FORMAT_FIELDS = {
    "statement": ["headline", "eyebrow_ar", "categories", "note"],
    "problem": ["headline", "items", "tagline"],
    "chips": ["eyebrow", "headline", "chips", "sign_off"],
    "bilingual": ["headline", "headline_ar", "sub_ar"],
    "hero": ["line1", "word", "eyebrow"],
    "arch": ["photo", "background", "eyebrow", "headline", "sub", "note"],
    "photo_line": ["photo", "headline", "sub"],
    "split": ["photo", "band", "eyebrow", "headline"],
    "framed": ["photo", "frame", "headline"],
    "reel": ["photo", "headline", "sub"],
}
MAX_CHARS = {  # headline limits that keep text inside its area (checked again by render.py)
    ("statement", "en"): 40, ("problem", "en"): 34, ("chips", "en"): 44, ("bilingual", "en"): 34,
    ("arch", "en"): 30, ("arch", "ar"): 30, ("photo_line", "en"): 48, ("photo_line", "ar"): 30,
    ("split", "en"): 40, ("split", "ar"): 32, ("framed", "en"): 34, ("framed", "ar"): 28,
    ("reel", "en"): 48, ("reel", "ar"): 30,
}


class SpecError(ValueError):
    pass


def accent(s, color, lang):
    """*word* -> italic coloured accent (English) or coloured only (Arabic has no italic)."""
    if lang == "ar":
        return re.sub(r"\*(.+?)\*", lambda m: f"[color {color}]{m.group(1)}[/color]", s)
    return re.sub(r"\*(.+?)\*", lambda m: L.acc(m.group(1), color), s)


def plain(s):
    return re.sub(r"\*(.+?)\*", r"\1", s or "")


def photo_info(spec):
    pid = str(spec.get("photo", ""))
    if pid not in LIB:
        raise SpecError(f"photo {pid!r} is not in the approved photo library")
    r = LIB[pid]
    fmt = spec["format"]
    allowed = r["allowed_formats"].split("|")
    if fmt not in allowed and not (fmt == "reel" and "photo_line" in allowed):
        raise SpecError(f"photo {pid} is not allowed in format {fmt} (allowed: {r['allowed_formats']})")
    return pid, r["text_zone"] or "bottom", r["text_tone"] or "light"


def check(spec):
    fmt, lang = spec.get("format"), spec.get("lang", "en")
    if fmt == "carousel":
        if not 2 <= len(spec.get("slides", [])) <= 10:
            raise SpecError("carousel needs 2-10 slides")
        return
    if fmt not in FORMAT_FIELDS:
        raise SpecError(f"unknown format {fmt!r}")
    missing = [f for f in FORMAT_FIELDS[fmt] if not spec.get(f)]
    if missing:
        raise SpecError(f"{fmt}: missing {', '.join(missing)}")
    lim = MAX_CHARS.get((fmt, lang))
    if lim and len(plain(spec["headline"])) > lim:
        raise SpecError(f"{fmt}/{lang}: headline is {len(plain(spec['headline']))} chars, limit {lim}")


def one(spec):
    check(spec)
    fmt, lang = spec["format"], spec.get("lang", "en")
    rtl = lang == "ar"
    h = spec.get("headline", "")
    if fmt == "statement":
        return L.f_statement(accent(h, L.GOLD, lang), spec["eyebrow_ar"], spec["categories"], spec["note"])
    if fmt == "problem":
        return L.f_problem(accent(h, L.GREEN, lang), spec["items"][:4], spec["tagline"])
    if fmt == "chips":
        return L.f_chips(spec["eyebrow"], accent(h, L.WHITE, lang), spec["chips"][:6], spec["sign_off"])
    if fmt == "bilingual":
        return L.f_bilingual(accent(h, L.WHITE, "en"), spec["headline_ar"], spec["sub_ar"])
    if fmt == "hero":
        w = max(200, min(760, int(len(spec["word"]) * 96)))
        return L.f_hero(spec["line1"], spec["word"], spec["eyebrow"], w)
    if fmt == "arch":
        bg = L.BANDS.get(spec["background"], L.CREAM)
        col = L.GOLD if bg == L.CREAM else L.WHITE
        return L.f_arch(bg, spec["eyebrow"], accent(h, col if not rtl else L.GREEN, lang), spec["sub"],
                        photo_info(spec)[0], spec["note"], rtl=rtl, outline=L.GOLD if bg == L.CREAM else L.WHITE)
    if fmt == "photo_line":
        pid, zone, tone = photo_info(spec)
        col = L.GOLD if tone == "light" else L.GREEN
        return L.f_photo_line(pid, accent(h, col, lang), rtl=rtl, sub=spec.get("sub"), zone=zone, tone=tone)
    if fmt == "split":
        band = L.BANDS.get(spec["band"], L.PEACH)
        col = L.WHITE if band == L.LILAC else L.GREEN
        return L.f_split(photo_info(spec)[0], spec["eyebrow"], accent(h, col, lang), band, rtl=rtl)
    if fmt == "framed":
        frame = L.BANDS.get(spec["frame"], L.CREAM)
        col = L.WHITE if frame == L.LILAC else L.GREEN
        return L.f_framed(photo_info(spec)[0], accent(h, col, lang), frame, rtl=rtl)
    if fmt == "reel":
        pid, zone, tone = photo_info(spec)
        col = L.GOLD if tone == "light" else L.GREEN
        return L.f_reel(pid, accent(h, col, lang), rtl=rtl, sub=spec.get("sub"), zone=zone, tone=tone)
    raise SpecError(fmt)


def build(spec):
    """Returns a list of (filename_stem, render_document)."""
    code = re.sub(r"[^A-Za-z0-9_-]", "-", str(spec.get("post_code") or "post"))
    if spec.get("format") == "carousel":
        check(spec)
        out = []
        for i, s in enumerate(spec["slides"], 1):
            s = {"lang": spec.get("lang", "en"), **s}
            out.append((f"{code}_{i:02d}", one(s)))
        return out
    return [(code, one(spec))]

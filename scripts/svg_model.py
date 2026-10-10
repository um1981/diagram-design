#!/usr/bin/env python3
"""Static SVG model shared by measure_text.py (text-fit check) and export_drawio.py.

Turns a diagram-design HTML file (or a standalone .svg) into a flat list of
primitives with absolute geometry and fully resolved style - without a browser:

* the first <svg> is extracted and made standalone by export_svg.py (page CSS is
  carried in, so class-styled diagrams resolve too);
* a small CSS engine applies the carried rules (descendant selectors made of
  tag / #id / .class compounds, specificity order, var() resolution);
* presentation attributes < CSS rules < inline style, with SVG inheritance;
* transforms (translate / scale / rotate / matrix) are composed to absolute
  coordinates;
* text is measured with the bundled Sarabun / Geist Mono metrics
  (assets/fonts/metrics.json), so widths are exact up to kerning.

Standard library only.
"""

from __future__ import annotations

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export_svg  # noqa: E402

SVG_NS = "{http://www.w3.org/2000/svg}"
METRICS_PATH = HERE.parent / "assets" / "fonts" / "metrics.json"

INHERITED = {
    "fill", "stroke", "stroke-width", "stroke-dasharray", "stroke-opacity",
    "fill-opacity", "font-family", "font-size", "font-weight", "font-style",
    "text-anchor", "letter-spacing", "text-transform", "visibility",
    "dominant-baseline", "marker-end", "marker-start", "marker-mid",
    "stroke-linecap", "stroke-linejoin",
}
STYLE_PROPS = INHERITED | {"opacity", "display", "rx", "ry"}
DEFAULTS = {
    "fill": "#000000", "stroke": "none", "stroke-width": "1",
    "font-size": "16", "font-weight": "400", "font-style": "normal",
    "font-family": "Sarabun, sans-serif", "text-anchor": "start",
    "letter-spacing": "0", "text-transform": "none", "opacity": "1",
    "fill-opacity": "1", "stroke-opacity": "1", "visibility": "visible",
    "display": "inline",
}

THAI_RE = re.compile(r"[฀-๿]")
THAI_UPPER = set("ัิีึื็")
THAI_TONE = set("่้๊๋์ํ๎")
THAI_LOWER = set("ฺุู")
THAI_DESC_CONS = set("ฎฏญฐฤฦ")
THAI_TALL_CONS = set("ปฝฟฬ")
LATIN_DESC = set("gjpqy,;()[]{}|/")


# ───────────────────────── metrics ─────────────────────────

_METRICS: dict | None = None


def metrics() -> dict:
    global _METRICS
    if _METRICS is None:
        _METRICS = json.loads(METRICS_PATH.read_text(encoding="utf-8"))["fonts"]
    return _METRICS


def font_key(family: str, weight: float, style: str = "normal") -> str:
    fam = (family or "").lower()
    if "mono" in fam:
        return "mono-500" if weight >= 500 else "mono-400"
    if style == "italic" and weight < 500:
        return "sarabun-400i"
    for w in (700, 600, 500):
        if weight >= w:
            return f"sarabun-{w}"
    return "sarabun-400"


def text_width(text: str, size: float, family: str = "Sarabun", weight: float = 400,
               style: str = "normal", letter_spacing: float = 0.0,
               transform: str = "none") -> float:
    """Advance width in px. letter_spacing is in px (already resolved)."""
    if transform == "uppercase":
        text = text.upper()
    adv = metrics()[font_key(family, weight, style)]
    total = 0.0
    spaced = 0
    for ch in text:
        code = format(ord(ch), "x")
        if code in adv:
            a = adv[code]
        elif ord(ch) >= 0x1100 and _is_wide(ch):
            a = 1000
        else:
            a = 600
        total += a
        if a > 0:
            spaced += 1
    return total * size / 1000.0 + letter_spacing * spaced


def _is_wide(ch: str) -> bool:
    import unicodedata
    return unicodedata.east_asian_width(ch) in ("W", "F")


def vertical_extent(text: str, size: float) -> tuple[float, float]:
    """(ascent, descent) in px above/below the baseline, Thai-aware (Sarabun)."""
    chars = set(text)
    if THAI_RE.search(text):
        stacked = any(
            a in THAI_UPPER and b in THAI_TONE for a, b in zip(text, text[1:])
        ) or "ำ" in chars and bool(chars & THAI_TONE)
        if stacked:
            asc = 1.25
        elif chars & (THAI_UPPER | THAI_TONE | THAI_TALL_CONS | {"ำ"}):
            asc = 0.98
        else:
            asc = 0.72
        desc = 0.33 if chars & (THAI_LOWER | THAI_DESC_CONS) else 0.12
    else:
        asc = 0.72 if not any(c.isupper() or c.isdigit() or c in "bdfhklt" for c in text) else 0.72
        desc = 0.23 if chars & LATIN_DESC else 0.05
    return asc * size, desc * size


# ───────────────────────── geometry ─────────────────────────

Matrix = tuple  # (a, b, c, d, e, f)
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mat_mul(m: Matrix, n: Matrix) -> Matrix:
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1,
    )


def apply(m: Matrix, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def scale_of(m: Matrix) -> float:
    a, b, c, d, _, _ = m
    return math.sqrt(abs(a * d - b * c)) or 1.0


def is_rotated(m: Matrix) -> bool:
    return abs(m[1]) > 1e-6 or abs(m[2]) > 1e-6


NUM_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse_transform(value: str | None) -> Matrix:
    m = IDENTITY
    if not value:
        return m
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", value):
        nums = [float(v) for v in NUM_RE.findall(args)]
        if name == "translate":
            t = (1, 0, 0, 1, nums[0], nums[1] if len(nums) > 1 else 0)
        elif name == "scale":
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            t = (sx, 0, 0, sy, 0, 0)
        elif name == "rotate":
            ang = math.radians(nums[0])
            cs, sn = math.cos(ang), math.sin(ang)
            t = (cs, sn, -sn, cs, 0, 0)
            if len(nums) == 3:
                cx, cy = nums[1], nums[2]
                t = mat_mul(mat_mul((1, 0, 0, 1, cx, cy), t), (1, 0, 0, 1, -cx, -cy))
        elif name == "matrix" and len(nums) == 6:
            t = tuple(nums)
        elif name == "skewX":
            t = (1, 0, math.tan(math.radians(nums[0])), 1, 0, 0)
        elif name == "skewY":
            t = (1, math.tan(math.radians(nums[0])), 0, 1, 0, 0)
        else:
            continue
        m = mat_mul(m, t)
    return m


def num(value, default: float = 0.0) -> float:
    if value is None:
        return default
    match = NUM_RE.search(str(value))
    return float(match.group()) if match else default


# ───────────────────────── colors ─────────────────────────

NAMED = {
    "white": "#ffffff", "black": "#000000", "none": "none", "transparent": "none",
    "red": "#ff0000", "green": "#008000", "blue": "#0000ff", "gray": "#808080",
    "grey": "#808080", "currentcolor": None,
}


def parse_color(value: str | None) -> tuple[str, float] | None:
    """Return ('#rrggbb', alpha) or None for none/url()/unknown."""
    if value is None:
        return None
    v = value.strip().lower()
    if not v or v == "none" or v == "transparent" or v.startswith("url("):
        return None
    if v in NAMED and NAMED[v]:
        return NAMED[v], 1.0
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            return "#" + h[:6], int(h[6:], 16) / 255
        if len(h) == 6:
            return "#" + h, 1.0
        return None
    m = re.match(r"rgba?\(([^)]*)\)", v)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1)) if p.strip()]
        try:
            r, g, b = (int(float(p.rstrip("%")) * (2.55 if p.endswith("%") else 1)) for p in parts[:3])
            a = float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1) if len(parts) > 3 else 1.0
        except (ValueError, IndexError):
            return None
        return f"#{r:02x}{g:02x}{b:02x}", a
    return None


def blend(fg: str, alpha: float, bg: str) -> str:
    """Composite fg@alpha over opaque bg → opaque hex."""
    fr, fg_, fb = (int(fg[i:i + 2], 16) for i in (1, 3, 5))
    br, bg_, bb = (int(bg[i:i + 2], 16) for i in (1, 3, 5))
    mix = lambda f, b: round(f * alpha + b * (1 - alpha))  # noqa: E731
    return f"#{mix(fr, br):02x}{mix(fg_, bg_):02x}{mix(fb, bb):02x}"


# ───────────────────────── CSS ─────────────────────────

@dataclass
class Rule:
    parts: list  # list of compounds, each (tag, id, classes)
    spec: tuple
    order: int
    decls: dict


def _parse_compound(text: str):
    if ":" in text or "[" in text or "*" == text:
        return None
    tag = None
    m = re.match(r"^[a-zA-Z][\w-]*", text)
    if m:
        tag = m.group().lower()
    ids = re.findall(r"#([\w-]+)", text)
    classes = re.findall(r"\.([\w-]+)", text)
    return tag, (ids[0] if ids else None), classes


def parse_css(css: str) -> tuple[list[Rule], dict]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@import[^;]*;", "", css)
    css = re.sub(r"@media[^{]*\{((?:[^{}]*\{[^{}]*\})*)[^{}]*\}", "", css)  # drop media blocks
    rules: list[Rule] = []
    variables: dict = {}
    order = 0
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        decls = {}
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            k, v = decl.split(":", 1)
            k = k.strip().lower()
            v = v.replace("!important", "").strip()
            if k.startswith("--"):
                variables[k] = v
            elif k == "font":
                decls.update(_expand_font(v))
            else:
                decls[k] = v
        for sel in selectors.split(","):
            sel = sel.strip().replace(">", " ")
            if not sel:
                continue
            compounds = [_parse_compound(c) for c in sel.split()]
            if any(c is None for c in compounds):
                continue
            ids = sum(1 for c in compounds if c[1])
            cls = sum(len(c[2]) for c in compounds)
            tags = sum(1 for c in compounds if c[0])
            order += 1
            rules.append(Rule(compounds, (ids, cls, tags), order, decls))
    rules.sort(key=lambda r: (r.spec, r.order))
    return rules, variables


def _expand_font(v: str) -> dict:
    out = {}
    m = re.match(r"^(?:(italic|normal)\s+)?(?:(\d{3}|bold|normal)\s+)?([\d.]+)px(?:/[\d.]+\w*)?\s+(.+)$", v.strip())
    if m:
        if m.group(1):
            out["font-style"] = m.group(1)
        if m.group(2):
            out["font-weight"] = "700" if m.group(2) == "bold" else ("400" if m.group(2) == "normal" else m.group(2))
        out["font-size"] = m.group(3)
        out["font-family"] = m.group(4)
    return out


def _matches(compound, el_info) -> bool:
    tag, id_, classes = compound
    etag, eid, eclasses = el_info
    if tag and tag != etag:
        return False
    if id_ and id_ != eid:
        return False
    return all(c in eclasses for c in classes)


def rule_matches(rule: Rule, chain: list) -> bool:
    """chain = [(tag, id, classes)] from root to element."""
    parts = rule.parts
    if not _matches(parts[-1], chain[-1]):
        return False
    i = len(chain) - 2
    for comp in reversed(parts[:-1]):
        while i >= 0 and not _matches(comp, chain[i]):
            i -= 1
        if i < 0:
            return False
        i -= 1
    return True


def resolve_vars(value: str, variables: dict, depth: int = 0) -> str:
    if "var(" not in value or depth > 8:
        return value

    def repl(m):
        name = m.group(1).strip()
        fallback = m.group(2)
        if name in variables:
            return resolve_vars(variables[name], variables, depth + 1)
        return fallback.strip() if fallback else ""

    return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)", repl, value)


# ───────────────────────── primitives ─────────────────────────

@dataclass
class Prim:
    kind: str                    # rect | ellipse | line | path | text | poly
    order: int
    style: dict
    bbox: tuple = (0, 0, 0, 0)   # x, y, w, h (absolute)
    rx: float = 0.0
    points: list = field(default_factory=list)       # line/poly/path vertices
    segments: list = field(default_factory=list)     # path: list of ('L'|'C'|'Q'|'A', pts)
    closed: bool = False
    simple_polyline: bool = False
    text: str = ""
    lines: list = field(default_factory=list)        # text: [(x, y, str, w)]
    font_size: float = 0.0
    element: object = None
    matrix: Matrix = IDENTITY
    markup: str = ""
    attrs: dict = field(default_factory=dict)

    @property
    def x(self):
        return self.bbox[0]

    @property
    def y(self):
        return self.bbox[1]

    @property
    def w(self):
        return self.bbox[2]

    @property
    def h(self):
        return self.bbox[3]


@dataclass
class Model:
    width: float
    height: float
    view_x: float
    view_y: float
    prims: list
    paper: str
    title: str
    desc: str
    page_title: str
    page_eyebrow: str
    markers: dict
    svg_source: str


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse_path(d: str):
    """Return list of subpaths: each {'start':(x,y), 'segs':[(cmd, [pts...])], 'closed':bool}."""
    toks = PATH_TOKEN.findall(d or "")
    subpaths = []
    cur = None
    x = y = 0.0
    sx = sy = 0.0
    cmd = None
    last_ctrl = None
    i = 0

    def take(n):
        nonlocal i
        vals = [float(t) for t in toks[i:i + n]]
        i += n
        return vals

    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    cur["closed"] = True
                    cur["segs"].append(("L", [(sx, sy)]))
                x, y = sx, sy
                continue
        if cmd is None:
            break
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            nx, ny = take(2)
            if rel:
                nx += x
                ny += y
            x, y = nx, ny
            sx, sy = x, y
            cur = {"start": (x, y), "segs": [], "closed": False}
            subpaths.append(cur)
            cmd = "l" if rel else "L"
            continue
        if cur is None:
            cur = {"start": (x, y), "segs": [], "closed": False}
            subpaths.append(cur)
        if c == "L":
            nx, ny = take(2)
            if rel:
                nx += x
                ny += y
            cur["segs"].append(("L", [(nx, ny)]))
            x, y = nx, ny
        elif c == "H":
            (nx,) = take(1)
            if rel:
                nx += x
            cur["segs"].append(("L", [(nx, y)]))
            x = nx
        elif c == "V":
            (ny,) = take(1)
            if rel:
                ny += y
            cur["segs"].append(("L", [(x, ny)]))
            y = ny
        elif c == "C":
            v = take(6)
            if rel:
                v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y, v[4] + x, v[5] + y]
            cur["segs"].append(("C", [(v[0], v[1]), (v[2], v[3]), (v[4], v[5])]))
            last_ctrl = (v[2], v[3])
            x, y = v[4], v[5]
        elif c == "S":
            v = take(4)
            if rel:
                v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y]
            c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            cur["segs"].append(("C", [c1, (v[0], v[1]), (v[2], v[3])]))
            last_ctrl = (v[0], v[1])
            x, y = v[2], v[3]
        elif c == "Q":
            v = take(4)
            if rel:
                v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y]
            cur["segs"].append(("Q", [(v[0], v[1]), (v[2], v[3])]))
            last_ctrl = (v[0], v[1])
            x, y = v[2], v[3]
        elif c == "T":
            v = take(2)
            if rel:
                v = [v[0] + x, v[1] + y]
            c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            cur["segs"].append(("Q", [c1, (v[0], v[1])]))
            last_ctrl = c1
            x, y = v[0], v[1]
        elif c == "A":
            v = take(7)
            nx, ny = v[5], v[6]
            if rel:
                nx += x
                ny += y
            cur["segs"].append(("A", [(x, y), (nx, ny), tuple(v[:5])]))
            x, y = nx, ny
        else:
            i += 1
        if c not in "CSQT":
            last_ctrl = None
    return subpaths


def _flatten(start, segs, steps: int = 8):
    pts = [start]
    cur = start
    for kind, data in segs:
        if kind == "L":
            pts.append(data[0])
            cur = data[0]
        elif kind == "Q":
            (cx, cy), (ex, ey) = data
            for k in range(1, steps + 1):
                t = k / steps
                pts.append(((1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * cx + t * t * ex,
                            (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * cy + t * t * ey))
            cur = (ex, ey)
        elif kind == "C":
            (c1x, c1y), (c2x, c2y), (ex, ey) = data
            for k in range(1, steps + 1):
                t = k / steps
                mt = 1 - t
                pts.append((mt ** 3 * cur[0] + 3 * mt * mt * t * c1x + 3 * mt * t * t * c2x + t ** 3 * ex,
                            mt ** 3 * cur[1] + 3 * mt * mt * t * c1y + 3 * mt * t * t * c2y + t ** 3 * ey))
            cur = (ex, ey)
        elif kind == "A":
            (x0, y0), (ex, ey), (rx, ry, rot, large, sweep) = data
            pts.extend(_arc_points(x0, y0, rx, ry, rot, int(large), int(sweep), ex, ey, steps))
            cur = (ex, ey)
    return pts


def _arc_points(x1, y1, rx, ry, phi, fa, fs, x2, y2, steps):
    if rx == 0 or ry == 0:
        return [(x2, y2)]
    phi = math.radians(phi)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = x1p ** 2 / rx ** 2 + y1p ** 2 / ry ** 2
    if lam > 1:
        rx *= math.sqrt(lam)
        ry *= math.sqrt(lam)
    num_ = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    coef = math.sqrt(max(0, num_ / den)) if den else 0
    if fa == fs:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    out = []
    n = max(steps, int(abs(dt) / (math.pi / 16)))
    for k in range(1, n + 1):
        t = t1 + dt * k / n
        out.append((cx + rx * math.cos(t) * cp - ry * math.sin(t) * sp,
                    cy + rx * math.cos(t) * sp + ry * math.sin(t) * cp))
    return out


def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _poly_corners(start, segs):
    """For a path made of straight runs joined by small Q/A/C fillets (the rounded
    orthogonal elbows the skill mandates), return its waypoint list
    [start, corner..., end]. None when the path contains a real curve."""
    pts = [start]
    cur = start
    for kind, data in segs:
        if kind == "L":
            end = data[0]
            pts.append(end)
        else:
            end = data[1] if kind in ("Q", "A") else data[2]
            if math.hypot(end[0] - cur[0], end[1] - cur[1]) > 40:
                return None  # a real curve, not a fillet
            if kind == "Q":
                corner = data[0]
            else:
                prev = pts[-2] if len(pts) >= 2 else None
                if kind == "C":
                    c1 = data[0]
                    vertical_in = abs(c1[0] - cur[0]) < 0.5 and abs(c1[1] - cur[1]) >= 0.5
                elif prev is not None:
                    vertical_in = abs(prev[0] - cur[0]) < 0.5
                else:
                    vertical_in = True
                corner = (cur[0], end[1]) if vertical_in else (end[0], cur[1])
            pts.append(corner)
        cur = end
    if math.hypot(pts[-1][0] - cur[0], pts[-1][1] - cur[1]) > 0.5:
        pts.append(cur)
    clean = [pts[0]]
    for q in pts[1:]:
        if math.hypot(q[0] - clean[-1][0], q[1] - clean[-1][1]) > 0.5:
            clean.append(q)
    out = [clean[0]]
    for i in range(1, len(clean) - 1):
        a, b, c = out[-1], clean[i], clean[i + 1]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) > 1e-3:
            out.append(b)
    out.append(clean[-1])
    return out


# ───────────────────────── builder ─────────────────────────

def load_svg_text(path: Path) -> tuple[str, str]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".svg":
        return raw, ""
    return export_svg.export_svg_document(raw, path), raw


def _page_text(html: str, pattern: str) -> str:
    m = re.search(pattern, html, flags=re.S | re.I)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def build(path: Path) -> Model:
    svg_text, html = load_svg_text(path)
    root = ET.fromstring(svg_text.split("?>", 1)[-1] if svg_text.startswith("<?xml") else svg_text)
    css = "\n".join((el.text or "") for el in root.iter() if _local(el.tag) == "style")
    rules, variables = parse_css(css)
    vb = [float(v) for v in NUM_RE.findall(root.get("viewBox", "0 0 1000 600"))]
    vx, vy, vw, vh = (vb + [0, 0, 1000, 600])[:4] if len(vb) >= 4 else (0, 0, 1000, 600)

    prims: list[Prim] = []
    markers: dict = {}
    order = [0]
    title = desc = ""

    def element_style(el, chain, parent_style):
        style = {k: v for k, v in parent_style.items() if k in INHERITED}
        for k in STYLE_PROPS:
            if el.get(k) is not None:
                style[k] = el.get(k)
        for rule in rules:
            if rule_matches(rule, chain):
                for k, v in rule.decls.items():
                    if k in STYLE_PROPS:
                        style[k] = v
        inline = el.get("style")
        if inline:
            for decl in inline.split(";"):
                if ":" in decl:
                    k, v = decl.split(":", 1)
                    k = k.strip().lower()
                    if k == "font":
                        style.update(_expand_font(v))
                    elif k in STYLE_PROPS:
                        style[k] = v.strip()
        for k, v in list(style.items()):
            style[k] = resolve_vars(v, variables)
        for k in ("fill", "stroke"):
            if style.get(k, "").strip().lower() == "currentcolor":
                style[k] = style.get("color", DEFAULTS["fill"])
        return style

    def walk(el, chain, parent_style, matrix, hidden=False):
        nonlocal title, desc
        tag = _local(el.tag)
        info = (tag, el.get("id"), (el.get("class") or "").split())
        chain = chain + [info]
        if tag in ("defs", "clipPath", "mask", "pattern", "symbol", "style", "linearGradient",
                   "radialGradient", "filter", "metadata", "script"):
            if tag == "defs":
                for m in el.iter():
                    if _local(m.tag) == "marker" and m.get("id"):
                        poly = next((c for c in m.iter() if _local(c.tag) in ("polygon", "path")), None)
                        fill = poly.get("fill") if poly is not None else None
                        markers[m.get("id")] = parse_color(fill)
            return
        if tag == "title" and not title:
            title = (el.text or "").strip()
            return
        if tag == "desc" and not desc:
            desc = (el.text or "").strip()
            return
        style = element_style(el, chain, parent_style)
        if style.get("display") == "none" or style.get("visibility") == "hidden":
            return
        m = mat_mul(matrix, parse_transform(el.get("transform")))
        op = num(style.get("opacity"), 1.0) * num(parent_style.get("_opacity"), 1.0)
        style["_opacity"] = str(op)
        if tag == "svg" and len(chain) > 1:
            # nested <svg> (icons): its own viewport + viewBox scaling
            vbn = [float(v) for v in NUM_RE.findall(el.get("viewBox", ""))]
            sx_, sy_ = num(el.get("x")), num(el.get("y"))
            m = mat_mul(m, (1, 0, 0, 1, sx_, sy_))
            if len(vbn) == 4 and vbn[2] and vbn[3]:
                w_ = num(el.get("width"), vbn[2])
                h_ = num(el.get("height"), vbn[3])
                k = min(w_ / vbn[2], h_ / vbn[3])
                m = mat_mul(m, (k, 0, 0, k, -vbn[0] * k, -vbn[1] * k))
        if tag in ("g", "svg", "a", "switch"):
            for child in el:
                walk(child, chain, style, m)
            return
        order[0] += 1
        markup = ET.tostring(el, encoding="unicode")
        attrs = dict(el.attrib)
        if tag == "rect":
            x, y = num(el.get("x")), num(el.get("y"))
            w_raw, h_raw = el.get("width", "0"), el.get("height", "0")
            w = vw if w_raw.strip().endswith("%") else num(w_raw)
            h = vh if h_raw.strip().endswith("%") else num(h_raw)
            if w_raw.strip().endswith("%"):
                w = vw * num(w_raw) / 100
            if h_raw.strip().endswith("%"):
                h = vh * num(h_raw) / 100
            corners = [apply(m, x, y), apply(m, x + w, y), apply(m, x, y + h), apply(m, x + w, y + h)]
            rx = num(el.get("rx") or style.get("rx") or el.get("ry"), 0.0) * scale_of(m)
            prims.append(Prim("rect", order[0], style, _bbox(corners), rx=rx, element=el, matrix=m,
                              markup=markup, attrs=attrs))
        elif tag in ("circle", "ellipse"):
            cx, cy = num(el.get("cx")), num(el.get("cy"))
            rx = num(el.get("r")) if tag == "circle" else num(el.get("rx"))
            ry = num(el.get("r")) if tag == "circle" else num(el.get("ry"))
            pts = [apply(m, cx - rx, cy - ry), apply(m, cx + rx, cy + ry)]
            prims.append(Prim("ellipse", order[0], style, _bbox(pts), element=el, matrix=m,
                              markup=markup, attrs=attrs))
        elif tag == "line":
            p1 = apply(m, num(el.get("x1")), num(el.get("y1")))
            p2 = apply(m, num(el.get("x2")), num(el.get("y2")))
            prims.append(Prim("line", order[0], style, _bbox([p1, p2]), points=[p1, p2],
                              simple_polyline=True, element=el, matrix=m, markup=markup, attrs=attrs))
        elif tag in ("polyline", "polygon"):
            vals = [float(v) for v in NUM_RE.findall(el.get("points", ""))]
            pts = [apply(m, vals[i], vals[i + 1]) for i in range(0, len(vals) - 1, 2)]
            if pts:
                prims.append(Prim("poly", order[0], style, _bbox(pts), points=pts, closed=(tag == "polygon"),
                                  simple_polyline=(tag == "polyline"), element=el, matrix=m,
                                  markup=markup, attrs=attrs))
        elif tag == "path":
            subs = parse_path(el.get("d", ""))
            for sub in subs:
                start = apply(m, *sub["start"])
                segs = []
                for kind, data in sub["segs"]:
                    if kind == "A":
                        (x0, y0), (ex, ey), params = data
                        s = scale_of(m)
                        segs.append(("A", [apply(m, x0, y0), apply(m, ex, ey),
                                           (params[0] * s, params[1] * s, params[2], params[3], params[4])]))
                    else:
                        segs.append((kind, [apply(m, *p) for p in data]))
                flat = _flatten(start, segs)
                if len(flat) < 2:
                    continue
                corners = None if sub["closed"] else _poly_corners(start, segs)
                prims.append(Prim("path", order[0], style, _bbox(flat), points=corners or flat,
                                  segments=segs, closed=sub["closed"],
                                  simple_polyline=corners is not None and all(
                                      abs(a[0] - b[0]) < 0.6 or abs(a[1] - b[1]) < 0.6
                                      for a, b in zip(corners, corners[1:])),
                                  element=el, matrix=m, markup=markup, attrs=attrs))
        elif tag == "text":
            prims.append(_text_prim(el, chain, style, m, order[0], markup, element_style))
        elif tag in ("image", "foreignObject", "use"):
            x, y = num(el.get("x")), num(el.get("y"))
            w, h = num(el.get("width")), num(el.get("height"))
            prims.append(Prim("other", order[0], style, _bbox([apply(m, x, y), apply(m, x + w, y + h)]),
                              element=el, matrix=m, markup=markup, attrs=attrs))

    base_style = dict(DEFAULTS)
    if root.get("id"):
        pass
    walk(root, [], base_style, IDENTITY)

    # paper = the first full-bleed rect's fill
    paper = "#f5f5f5"
    for p in prims:
        if p.kind == "rect" and p.w >= vw * 0.98 and p.h >= vh * 0.98:
            c = parse_color(p.style.get("fill"))
            if c:
                paper = c[0]
                break
    page_title = _page_text(html, r"<h1[^>]*>(.*?)</h1>") if html else ""
    page_eyebrow = _page_text(html, r'<p class="(?:header-)?eyebrow"[^>]*>(.*?)</p>') if html else ""
    return Model(vw, vh, vx, vy, prims, paper, title, desc, page_title, page_eyebrow, markers, svg_text)


def _text_prim(el, chain, style, m, order, markup, element_style):
    size = num(style.get("font-size"), 16) * scale_of(m)
    lines = []
    x0 = num(el.get("x"))
    y0 = num(el.get("y"))
    cx, cy = x0, y0

    def ls_px(st, sz):
        v = (st.get("letter-spacing") or "0").strip()
        if v.endswith("em"):
            return num(v) * sz
        return num(v)

    def add(text, x, y, st):
        text = re.sub(r"\s+", " ", text or "")
        if not text.strip():
            return
        sz = num(st.get("font-size"), 16) * scale_of(m)
        w = text_width(text.strip(), sz, st.get("font-family", ""), num(st.get("font-weight"), 400) if str(st.get("font-weight")) not in ("bold",) else 700,
                       st.get("font-style", "normal"), ls_px(st, sz), st.get("text-transform", "none"))
        ax, ay = apply(m, x, y)
        lines.append({"x": ax, "y": ay, "text": text.strip(), "w": w, "size": sz,
                      "weight": num(st.get("font-weight"), 400) if str(st.get("font-weight")) != "bold" else 700,
                      "family": st.get("font-family", ""), "style": st.get("font-style", "normal"),
                      "fill": st.get("fill"), "anchor": st.get("text-anchor", "start"),
                      "transform": st.get("text-transform", "none"),
                      "letter_spacing": st.get("letter-spacing", "0")})

    # direct text
    if el.text and el.text.strip():
        add(el.text, cx, cy, style)
    for child in el:
        if _local(child.tag) != "tspan":
            continue
        cst = element_style(child, chain + [("tspan", child.get("id"), (child.get("class") or "").split())], style)
        if child.get("x") is not None:
            cx = num(child.get("x"))
        if child.get("y") is not None:
            cy = num(child.get("y"))
        cy += num(child.get("dy"))
        new_line = child.get("x") is not None or child.get("y") is not None or child.get("dy") is not None
        txt = "".join(child.itertext())
        if lines and not new_line:
            # inline tspan continues the previous run
            prev = lines[-1]
            prev["text"] = (prev["text"] + " " + txt.strip()).strip() if txt.strip() else prev["text"]
            prev["w"] += text_width(txt, prev["size"], cst.get("font-family", ""), num(cst.get("font-weight"), 400))
        else:
            add(txt, cx, cy, cst)
        if child.tail and child.tail.strip():
            prev = lines[-1] if lines else None
            if prev:
                prev["text"] += child.tail.strip()
                prev["w"] += text_width(child.tail.strip(), prev["size"], prev["family"], prev["weight"])
    # bbox
    boxes = []
    for ln in lines:
        asc, desc = vertical_extent(ln["text"], ln["size"])
        if ln["anchor"] == "middle":
            left = ln["x"] - ln["w"] / 2
        elif ln["anchor"] == "end":
            left = ln["x"] - ln["w"]
        else:
            left = ln["x"]
        ln["left"] = left
        ln["top"] = ln["y"] - asc
        ln["bottom"] = ln["y"] + desc
        boxes += [(left, ln["y"] - asc), (left + ln["w"], ln["y"] + desc)]
    bbox = _bbox(boxes) if boxes else (x0, y0, 0, 0)
    full = " ".join(ln["text"] for ln in lines)
    return Prim("text", order, style, bbox, text=full, lines=lines, font_size=size, element=el,
                matrix=m, markup=markup, attrs=dict(el.attrib))


if __name__ == "__main__":
    model = build(Path(sys.argv[1]))
    print(f"viewBox {model.width}x{model.height} paper={model.paper} title={model.title!r}")
    for p in model.prims:
        extra = p.text if p.kind == "text" else ""
        print(p.order, p.kind, tuple(round(v, 1) for v in p.bbox), extra[:40])

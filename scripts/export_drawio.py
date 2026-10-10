#!/usr/bin/env python3
"""Export a finished diagram (HTML or standalone SVG) to an editable draw.io file.

    python3 scripts/export_drawio.py my-diagram.html               # -> my-diagram.drawio
    python3 scripts/export_drawio.py my-diagram.html out.drawio --body-pt 16 --title-pt 20

What you get in draw.io (diagrams.net / draw.io Desktop):

* boxes, pills, tag chips  -> rectangle vertices (rx kept, tints flattened over
  the paper colour, so they stay opaque like the original mask+box pair)
* diamonds / triangles     -> rhombus / triangle vertices
* circles / ellipses       -> ellipse vertices
* text                     -> text cells in Sarabun (Geist Mono for technical
  values), parented to the box they sit in so they move with it; label masks
  become the text cell's own paper-coloured background
* orthogonal connectors    -> edges with waypoints, glued to the boxes they touch
  (exit/entry constraints), so moving a box drags its arrows along
* anything else (curves, bands, icons, free polygons) -> an embedded SVG image
  cell at the exact position, so nothing is silently dropped

Sizing follows the house rule for draw.io: node names become --body-pt (16) and
everything scales with them, the page title is added at --title-pt (20).
Fonts are referenced from Google Fonts (fontSource) so they render even where
Sarabun is not installed.

Standard library only. Prints a short fidelity ledger.
"""

from __future__ import annotations

import argparse
import base64
import html as htmlmod
import math
import re
import sys
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import quoteattr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svg_model as sm  # noqa: E402

FONT_SRC = {
    "sarabun": "https%3A%2F%2Ffonts.googleapis.com%2Fcss%3Ffamily%3DSarabun%3A400%2C400i%2C600%2C700",
    "mono": "https%3A%2F%2Ffonts.googleapis.com%2Fcss%3Ffamily%3DGeist%2BMono%3A400%2C500",
}


def r1(v: float) -> str:
    return f"{round(v, 1):g}"


class Exporter:
    def __init__(self, model: sm.Model, body_pt: float, title_pt: float, include_title: bool):
        self.m = model
        self.paper = model.paper
        self.cells: list[str] = []
        self.n = 1
        self.ledger = Counter()
        # node names = semibold text of at least 11px (tags/eyebrows are smaller)
        names = [ln["size"] for p in model.prims if p.kind == "text" for ln in p.lines
                 if ln["weight"] >= 600 and ln["size"] >= 11]
        base = Counter(round(v, 1) for v in names).most_common(1)[0][0] if names else 12.0
        self.s = max(1.0, min(2.0, body_pt / base))
        self.title_pt = title_pt
        self.include_title = include_title and bool(model.page_title)
        self.dy = (title_pt * 2.4) if self.include_title else 0.0
        self.ox = -model.view_x
        self.oy = -model.view_y

    # coordinates → draw.io page space
    def X(self, x):
        return (x + self.ox) * self.s

    def Y(self, y):
        return (y + self.oy) * self.s + self.dy

    def nid(self) -> str:
        self.n += 1
        return f"c{self.n}"

    # ── colours ──
    def fill_of(self, p, flatten=True):
        c = sm.parse_color(p.style.get("fill"))
        if not c:
            return "none", 100
        hexv, a = c
        a *= sm.num(p.style.get("fill-opacity"), 1.0)
        if a >= 0.999:
            return hexv, 100
        if flatten:
            return sm.blend(hexv, a, self.paper), 100
        return hexv, round(a * 100)

    def stroke_of(self, p):
        c = sm.parse_color(p.style.get("stroke"))
        if not c:
            return "none", 0.0
        hexv, a = c
        a *= sm.num(p.style.get("stroke-opacity"), 1.0)
        if a < 0.999:
            hexv = sm.blend(hexv, a, self.paper)
        width = sm.num(p.style.get("stroke-width"), 1.0) * sm.scale_of(p.matrix) * self.s
        return hexv, width

    def dash(self, p):
        d = p.style.get("stroke-dasharray")
        if not d or d.strip() == "none":
            return ""
        vals = [float(v) * self.s for v in sm.NUM_RE.findall(d)]
        return f"dashed=1;dashPattern={' '.join(r1(v / max(1e-6, self.stroke_of(p)[1] or 1)) for v in vals)};"

    def opacity(self, p):
        op = sm.num(p.style.get("_opacity"), 1.0)
        return f"opacity={round(op * 100)};" if op < 0.999 else ""

    # ── emit ──
    def vertex(self, style, x, y, w, h, value="", parent="1", cid=None):
        cid = cid or self.nid()
        self.cells.append(
            f'<mxCell id="{cid}" value={quoteattr(value)} style={quoteattr(style)} vertex="1" parent="{parent}">'
            f'<mxGeometry x="{r1(x)}" y="{r1(y)}" width="{r1(max(w, 1))}" height="{r1(max(h, 1))}" as="geometry"/></mxCell>'
        )
        return cid

    def edge(self, style, pts, src=None, tgt=None):
        cid = self.nid()
        a, b = pts[0], pts[-1]
        mids = "".join(f'<mxPoint x="{r1(x)}" y="{r1(y)}"/>' for x, y in pts[1:-1])
        st = f' source="{src[0]}"' if src else ""
        tt = f' target="{tgt[0]}"' if tgt else ""
        if src:
            style += f"exitX={src[1]:.4f};exitY={src[2]:.4f};exitDx=0;exitDy=0;exitPerimeter=0;"
        if tgt:
            style += f"entryX={tgt[1]:.4f};entryY={tgt[2]:.4f};entryDx=0;entryDy=0;entryPerimeter=0;"
        self.cells.append(
            f'<mxCell id="{cid}" style={quoteattr(style)} edge="1" parent="1"{st}{tt}>'
            f'<mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{r1(a[0])}" y="{r1(a[1])}" as="sourcePoint"/>'
            f'<mxPoint x="{r1(b[0])}" y="{r1(b[1])}" as="targetPoint"/>'
            + (f'<Array as="points">{mids}</Array>' if mids else "")
            + "</mxGeometry></mxCell>"
        )
        return cid

    # ── classification helpers ──
    def is_background(self, p):
        return p.kind == "rect" and p.w >= self.m.width * 0.98 and p.h >= self.m.height * 0.98

    def is_mask(self, p):
        if p.kind != "rect":
            return False
        fill, _ = self.fill_of(p, flatten=False)
        stroke, _ = self.stroke_of(p)
        return fill.lower() == self.paper.lower() and stroke == "none"

    @staticmethod
    def rhombus_or_triangle(p):
        pts = p.points[:-1] if len(p.points) > 1 and p.points[0] == p.points[-1] else p.points
        if len(pts) == 4:
            xs = sorted(set(round(q[0]) for q in pts))
            ys = sorted(set(round(q[1]) for q in pts))
            if len(xs) == 3 and len(ys) == 3:
                return "rhombus"
        if len(pts) == 3:
            return "triangle"
        return None

    def image_cell(self, p, parent_offset=(0, 0)):
        """Embed one primitive as an SVG image at its exact position."""
        pad = 4.0
        x, y, w, h = p.bbox
        x -= pad
        y -= pad
        w += 2 * pad
        h += 2 * pad
        el_markup = self._resolved_markup(p)
        a, b, c, d, e, f = p.matrix
        defs = ""
        if p.style.get("marker-end") or p.style.get("marker-start"):
            col = self.stroke_of(p)[0]
            defs = (f'<defs><marker id="m" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
                    f'<polygon points="0 0, 8 3, 0 6" fill="{col}"/></marker></defs>')
            el_markup = re.sub(r'marker-(end|start)="[^"]*"', r'marker-\1="url(#m)"', el_markup)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:g} {y:g} {w:g} {h:g}" '
               f'width="{w * self.s:g}" height="{h * self.s:g}">{defs}'
               f'<g transform="matrix({a:g},{b:g},{c:g},{d:g},{e:g},{f:g})">{el_markup}</g></svg>')
        data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        style = (f"shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;"
                 f"image=data:image/svg+xml,{data};{self.opacity(p)}")
        self.ledger["embedded as SVG image"] += 1
        return self.vertex(style, self.X(x), self.Y(y), w * self.s, h * self.s)

    def _resolved_markup(self, p):
        """Element markup with its computed style written back as attributes."""
        el = p.element
        tag = sm._local(el.tag)
        attrs = {k: v for k, v in el.attrib.items()
                 if k not in ("class", "style", "transform") and not k.startswith("data-")}
        for k in ("fill", "stroke", "stroke-width", "stroke-dasharray", "fill-opacity", "stroke-opacity",
                  "stroke-linecap", "stroke-linejoin", "marker-end", "marker-start"):
            if p.style.get(k):
                attrs[k] = p.style[k]
        attrs["opacity"] = p.style.get("opacity", "1")
        attr_s = " ".join(f'{k}={quoteattr(str(v))}' for k, v in attrs.items())
        return f"<{tag} {attr_s}/>"

    # ── main ──
    def run(self) -> str:
        prims = self.m.prims
        # 1) drop backgrounds and node masks (mask immediately covered by a same-geometry box)
        skip = set()
        for i, p in enumerate(prims):
            if self.is_background(p):
                skip.add(id(p))
                self.ledger["background → page colour"] += 1
        rects = [p for p in prims if p.kind == "rect" and id(p) not in skip]
        for i, p in enumerate(rects):
            if self.is_mask(p):
                for q in rects[i + 1:]:
                    if q.kind == "rect" and all(abs(u - v) < 0.6 for u, v in zip(p.bbox, q.bbox)):
                        skip.add(id(p))
                        self.ledger["node mask merged into box"] += 1
                        break
        # 2) label masks → absorbed by the text they back
        texts = [p for p in prims if p.kind == "text"]
        text_mask = {}
        for t in texts:
            cx = t.x + t.w / 2
            cy = t.y + t.h / 2
            cands = [r for r in rects if id(r) not in skip and r.order < t.order and self.is_mask(r)
                     and r.x - 1 <= cx <= r.x + r.w + 1 and r.y - 1 <= cy <= r.y + r.h + 1
                     and r.w < 260 and r.h < 40]
            if cands:
                r = min(cands, key=lambda r: r.w * r.h)
                if id(r) not in text_mask.values():
                    text_mask[id(t)] = r
                    skip.add(id(r))
                    self.ledger["label mask → text background"] += 1
        # 3) node boxes that can parent their texts (leaf boxes: contain no other box)
        boxes = [p for p in prims if id(p) not in skip and (
            (p.kind == "rect" and p.w >= 24 and p.h >= 16 and self.stroke_of(p)[0] != "none")
            or (p.kind == "poly" and p.closed and self.rhombus_or_triangle(p))
            or p.kind == "ellipse")]

        def contains(a, b):
            return (a.x <= b.x + 0.5 and a.y <= b.y + 0.5 and a.x + a.w >= b.x + b.w - 0.5
                    and a.y + a.h >= b.y + b.h - 0.5 and a is not b)

        leaf = [b for b in boxes if not any(contains(b, o) and o.w * o.h > 400 for o in boxes)]
        parent_of = {}
        for t in texts:
            if id(t) in text_mask:
                continue
            cx = t.x + t.w / 2
            cy = t.y + t.h / 2
            cands = [b for b in leaf if b.order < t.order and b.x <= cx <= b.x + b.w and b.y <= cy <= b.y + b.h]
            if cands:
                parent_of[id(t)] = min(cands, key=lambda b: b.w * b.h)
        # small chips (type tags) inside a leaf box also travel with it
        for p in prims:
            if p.kind == "rect" and id(p) not in skip and p not in leaf:
                cands = [b for b in leaf if contains(b, p) and b.order < p.order]
                if cands:
                    parent_of[id(p)] = min(cands, key=lambda b: b.w * b.h)

        # pre-assign ids so connectors (drawn before boxes) can glue to them
        cell_id = {id(b): self.nid() for b in leaf}
        geom = {}

        if self.include_title:
            left = min((p.x for p in prims if not self.is_background(p)), default=0)
            self.vertex(self.text_style("Sarabun", self.title_pt, 700, "#2d3142", "left") ,
                        self.X(left), self.title_pt * 0.4, 900, self.title_pt * 1.8,
                        htmlmod.escape(self.m.page_title))
            self.ledger["page title added"] += 1

        for p in prims:
            if id(p) in skip:
                continue
            pre = cell_id.get(id(p))
            if p.kind == "rect":
                parent = parent_of.get(id(p))
                cid = self.emit_rect(p, cell_id.get(id(parent)) if parent else None, geom.get(id(parent)), pre)
            elif p.kind == "ellipse":
                cid = self.emit_ellipse(p, pre)
            elif p.kind == "poly" and p.closed and self.rhombus_or_triangle(p):
                cid = self.emit_polyshape(p, self.rhombus_or_triangle(p), pre)
            elif p.kind in ("line", "path", "poly") and not p.closed and p.simple_polyline:
                self.emit_edge(p, leaf, cell_id)
                continue
            elif p.kind == "text":
                parent = parent_of.get(id(p))
                self.emit_text(p, text_mask.get(id(p)), cell_id.get(id(parent)) if parent else None,
                               geom.get(id(parent)))
                continue
            else:
                cid = self.image_cell(p)
            cell_id[id(p)] = cid
            geom[id(p)] = (self.X(p.x), self.Y(p.y))
        return self.document()

    # ── element emitters ──
    def emit_rect(self, p, parent_cell, parent_xy, cid=None):
        fill, fo = self.fill_of(p)
        stroke, sw = self.stroke_of(p)
        rx = p.rx
        style = "rounded=0;" if rx < 0.5 else f"rounded=1;absoluteArcSize=1;arcSize={r1(2 * rx * self.s)};"
        style += (f"whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                  f"strokeWidth={r1(sw) if stroke != 'none' else 1};{self.dash(p)}{self.opacity(p)}")
        x, y = self.X(p.x), self.Y(p.y)
        if parent_cell:
            x -= parent_xy[0]
            y -= parent_xy[1]
        self.ledger["rectangles"] += 1
        return self.vertex(style, x, y, p.w * self.s, p.h * self.s, parent=parent_cell or "1", cid=cid)

    def emit_ellipse(self, p, cid=None):
        fill, fo = self.fill_of(p, flatten=False)
        stroke, sw = self.stroke_of(p)
        style = (f"ellipse;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                 f"strokeWidth={r1(sw) if stroke != 'none' else 1};{self.dash(p)}{self.opacity(p)}")
        if fill != "none" and fo < 100:
            style += f"fillOpacity={fo};"
        self.ledger["ellipses"] += 1
        return self.vertex(style, self.X(p.x), self.Y(p.y), p.w * self.s, p.h * self.s, cid=cid)

    def emit_polyshape(self, p, shape, cid=None):
        fill, _ = self.fill_of(p)
        stroke, sw = self.stroke_of(p)
        style = f"{shape};whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth={r1(sw) if stroke != 'none' else 1};{self.dash(p)}{self.opacity(p)}"
        if shape == "triangle":
            pts = p.points
            cx = p.x + p.w / 2
            cy = p.y + p.h / 2
            apex = max(pts, key=lambda q: math.hypot(q[0] - cx, q[1] - cy))
            if abs(apex[1] - p.y) < 0.6:
                style += "direction=north;"
            elif abs(apex[1] - (p.y + p.h)) < 0.6:
                style += "direction=south;"
            elif abs(apex[0] - p.x) < 0.6:
                style += "direction=west;"
        self.ledger[f"{shape} shapes"] += 1
        return self.vertex(style, self.X(p.x), self.Y(p.y), p.w * self.s, p.h * self.s, cid=cid)

    def text_style(self, family, size, weight, color, align, italic=False):
        mono = "mono" in (family or "").lower()
        fam = "Geist Mono" if mono else "Sarabun"
        src = FONT_SRC["mono" if mono else "sarabun"]
        fs = (1 if weight >= 600 else 0) | (2 if italic else 0)
        return (f"text;html=1;align={align};verticalAlign=middle;spacing=0;whiteSpace=nowrap;"
                f"fontFamily={fam};fontSource={src};fontSize={r1(size)};fontStyle={fs};fontColor={color};"
                f"strokeColor=none;fillColor=none;")

    def emit_text(self, p, mask, parent_cell, parent_xy):
        lines = p.lines
        if not lines:
            return
        first = lines[0]
        anchor = first["anchor"]
        align = {"middle": "center", "end": "right"}.get(anchor, "left")
        col = sm.parse_color(first.get("fill") or p.style.get("fill"))
        color = col[0] if col else "#2d3142"
        alpha = (col[1] if col else 1.0) * sm.num(p.style.get("fill-opacity"), 1.0) * sm.num(p.style.get("_opacity"), 1.0)
        if alpha < 0.999:
            color = sm.blend(color, alpha, self.paper)
        size = first["size"] * self.s
        weight = first["weight"]
        italic = first["style"] == "italic"
        texts = []
        for ln in lines:
            t = ln["text"].upper() if ln["transform"] == "uppercase" else ln["text"]
            texts.append(htmlmod.escape(t))
        thai = any(sm.THAI_RE.search(ln["text"]) for ln in lines)
        value = "<br>".join(texts)
        if len(lines) > 1:
            pitch = (lines[-1]["y"] - lines[0]["y"]) / (len(lines) - 1) if len(lines) > 1 else size
            lh = max(1.6 if thai else 1.25, pitch / first["size"])
            value = f'<div style="line-height:{lh:.2f}">{value}</div>'
        style = self.text_style(first["family"], size, weight, color, align, italic)
        if mask is not None:
            x, y, w, h = self.X(mask.x), self.Y(mask.y), mask.w * self.s, mask.h * self.s
            style = style.replace("fillColor=none;", f"fillColor={self.paper};").replace(f"align={align}", "align=center")
            if mask.rx > 0.5:
                style += f"rounded=1;absoluteArcSize=1;arcSize={r1(2 * mask.rx * self.s)};"
        else:
            pad = 3 * self.s
            w = max(ln["w"] for ln in lines) * self.s + 2 * pad + 2
            # Centre the cell on the baselines, not on the glyph ink, so labels that
            # share a baseline stay aligned whatever marks they carry. draw.io lays a
            # Sarabun line box out with its baseline 0.418em below the box centre.
            b0, b1 = self.Y(lines[0]["y"]), self.Y(lines[-1]["y"])
            h = (b1 - b0) + size * 1.6 + 2 * pad
            top_px = (b0 + b1) / 2 - 0.418 * size - h / 2
            if anchor == "middle":
                cx = sum(ln["x"] for ln in lines) / len(lines)
                x = self.X(cx) - w / 2
            elif anchor == "end":
                x = self.X(max(ln["x"] for ln in lines)) - w + pad
            else:
                x = self.X(min(ln["x"] for ln in lines)) - pad
            y = top_px
        if parent_cell:
            x -= parent_xy[0]
            y -= parent_xy[1]
        self.ledger["text cells"] += 1
        self.vertex(style, x, y, w, h, value, parent=parent_cell or "1")

    def emit_edge(self, p, leaf, cell_id):
        stroke, sw = self.stroke_of(p)
        if stroke == "none":
            return
        pts = [(self.X(x), self.Y(y)) for x, y in p.points]
        end = "block" if p.style.get("marker-end") else "none"
        start = "block" if p.style.get("marker-start") else "none"
        style = (f"edgeStyle=none;rounded=1;html=1;endArrow={end};startArrow={start};"
                 f"endFill=1;startFill=1;endSize={r1(5 * self.s)};startSize={r1(5 * self.s)};"
                 f"strokeColor={stroke};strokeWidth={r1(sw)};{self.dash(p)}{self.opacity(p)}")
        src = self.glue(p.points[0], leaf, cell_id)
        tgt = self.glue(p.points[-1], leaf, cell_id)
        self.edge(style, pts, src, tgt)
        self.ledger["connectors"] += 1
        if src or tgt:
            self.ledger["connector ends glued to boxes"] += (1 if src else 0) + (1 if tgt else 0)

    def glue(self, pt, leaf, cell_id, tol=4.0):
        x, y = pt
        best = None
        for b in leaf:
            if id(b) not in cell_id:
                continue
            bx, by, bw, bh = b.bbox
            if not (bx - tol <= x <= bx + bw + tol and by - tol <= y <= by + bh + tol):
                continue
            dists = [abs(x - bx), abs(x - (bx + bw)), abs(y - by), abs(y - (by + bh))]
            if b.kind == "poly":   # rhombus: glue at the four vertices
                verts = [(bx + bw / 2, by), (bx + bw, by + bh / 2), (bx + bw / 2, by + bh), (bx, by + bh / 2)]
                dv = min(math.hypot(x - vx, y - vy) for vx, vy in verts)
                if dv > tol:
                    continue
                d = dv
            else:
                d = min(dists)
                if d > tol:
                    continue
            if best is None or d < best[0]:
                rx = min(1.0, max(0.0, (x - bx) / bw)) if bw else 0.5
                ry = min(1.0, max(0.0, (y - by) / bh)) if bh else 0.5
                # snap to the nearest edge
                if b.kind != "poly":
                    k = dists.index(min(dists))
                    rx, ry = [(0.0, ry), (1.0, ry), (rx, 0.0), (rx, 1.0)][k]
                best = (d, (cell_id[id(b)], rx, ry))
        return best[1] if best else None

    def document(self) -> str:
        w = self.m.width * self.s
        h = self.m.height * self.s + self.dy
        name = htmlmod.escape(self.m.page_title or self.m.title or "Diagram")
        body = "".join(self.cells)
        return (
            '<mxfile host="diagram-design" type="device">'
            f'<diagram id="dd-1" name={quoteattr(self.m.page_title or self.m.title or "Diagram")}>'
            f'<mxGraphModel dx="{int(w)}" dy="{int(h)}" grid="1" gridSize="4" guides="1" tooltips="1" connect="1" '
            f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(math.ceil(w))}" pageHeight="{int(math.ceil(h))}" '
            f'background="{self.paper}" math="0" shadow="0">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + body +
            "</root></mxGraphModel></diagram></mxfile>\n"
        ).replace("{name}", name)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="diagram .html or standalone .svg")
    ap.add_argument("output", type=Path, nargs="?", help="output .drawio (default: next to source)")
    ap.add_argument("--body-pt", type=float, default=16.0, help="node-name size in draw.io (default 16)")
    ap.add_argument("--title-pt", type=float, default=20.0, help="page title size (default 20; 18-20)")
    ap.add_argument("--no-title", action="store_true", help="do not add the page <h1> as a title cell")
    args = ap.parse_args(argv)
    if not args.source.is_file():
        print(f"error: source not found: {args.source}", file=sys.stderr)
        return 2
    try:
        model = sm.build(args.source)
    except Exception as exc:
        print(f"error: could not read diagram: {exc}", file=sys.stderr)
        return 2
    ex = Exporter(model, args.body_pt, args.title_pt, not args.no_title)
    xml = ex.run()
    out = args.output or args.source.with_suffix(".drawio")
    out.write_text(xml, encoding="utf-8")
    print(f"{out}  (scale ×{ex.s:.3g}: node names {args.body_pt:g}pt)")
    for k, v in sorted(ex.ledger.items()):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

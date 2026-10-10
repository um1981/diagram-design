#!/usr/bin/env python3
"""Measure label widths with the bundled Sarabun / Geist Mono metrics, and
check that every label in a finished diagram fits its box.

Thai has no reliable "characters x 0.6em" shortcut: combining vowels and tone
marks have zero advance, sara am is wide, and stacked marks rise to 1.25em above
the baseline. Use this instead of guessing.

Measure (sizes in px, the SVG user unit):

    python3 scripts/measure_text.py "อนุมัติใบสั่งซื้อ" --size 13 --weight 600
    python3 scripts/measure_text.py "PURCHASE ORDER" --size 9 --weight 600 --caps --tracking 0.14
    python3 scripts/measure_text.py "Port 443" --mono --size 9
    python3 scripts/measure_text.py --pad 12 "ใบสั่งซื้อ" "Vendor invoice" ...

Prints width, ascent/descent, and a suggested box width (text + 2*pad, rounded
up to the 4px grid) and label-mask height.

Check a finished diagram (static, no browser needed):

    python3 scripts/measure_text.py --check my-diagram.html

For every <text> line it finds the smallest box drawn *before* it that contains
its anchor (node, tag chip, label mask) and reports text that overflows that
box horizontally or vertically, plus Thai-specific violations: Thai below 12px,
Thai with letter-spacing or text-transform, multi-line Thai pitch under 1.6em.
Exit code 1 when anything is found.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svg_model as sm  # noqa: E402


def ceil4(v: float) -> int:
    return int(math.ceil(v / 4.0) * 4)


def measure_cli(args) -> int:
    family = "Geist Mono" if args.mono else "Sarabun"
    style = "italic" if args.italic else "normal"
    for text in args.text:
        ls = args.tracking * args.size
        w = sm.text_width(text, args.size, family, args.weight, style, ls,
                          "uppercase" if args.caps else "none")
        asc, desc = sm.vertical_extent(text.upper() if args.caps else text, args.size)
        thai = bool(sm.THAI_RE.search(text))
        mask_h = max(24, ceil4(asc + desc + 6)) if thai else ceil4(max(asc + desc + 4, args.size + 4))
        print(f"{text!r}: width {w:.1f}px  ascent {asc:.1f}  descent {desc:.1f}  "
              f"box ≥ {ceil4(w + 2 * args.pad)}px (pad {args.pad})  mask h {mask_h}px"
              + ("  [Thai: no tracking/caps, ≥12px, line pitch ≥ %dpx]" % math.ceil(args.size * 1.6) if thai else ""))
        if thai and (args.caps or args.tracking):
            print("  ! Thai text must not use --caps/--tracking (letter-spacing breaks mark positioning)")
        if thai and args.size < 12:
            print("  ! Thai text below the 12px floor")
    return 0


def check_file(path: Path) -> list[str]:
    model = sm.build(path)
    findings: list[str] = []
    boxes = [p for p in model.prims if p.kind == "rect"
             and not (p.w >= model.width * 0.95 and p.h >= model.height * 0.95)
             and p.w >= 8 and p.h >= 6]
    for t in model.prims:
        if t.kind != "text":
            continue
        thai_lines = [ln for ln in t.lines if sm.THAI_RE.search(ln["text"])]
        for ln in t.lines:
            label = ln["text"][:40]
            thai = bool(sm.THAI_RE.search(ln["text"]))
            if thai:
                if ln["size"] < 11.95:
                    findings.append(f"{path.name}: Thai text {label!r} is {ln['size']:g}px — floor is 12px")
                if ln["transform"] == "uppercase":
                    findings.append(f"{path.name}: Thai text {label!r} has text-transform:uppercase — remove it")
                if sm.num(ln["letter_spacing"]) not in (0.0,):
                    findings.append(f"{path.name}: Thai text {label!r} has letter-spacing — set it to 0")
            # container: smallest rect drawn before the text that contains the anchor
            ax = ln["left"] + ln["w"] / 2
            ay = ln["y"] - ln["size"] * 0.35
            cands = [b for b in boxes if b.order < t.order
                     and b.x - 0.5 <= ax <= b.x + b.w + 0.5 and b.y - 0.5 <= ay <= b.y + b.h + 0.5]
            if not cands:
                continue
            box = min(cands, key=lambda b: b.w * b.h)
            over_l = box.x - ln["left"]
            over_r = (ln["left"] + ln["w"]) - (box.x + box.w)
            over_t = box.y - ln["top"]
            over_b = ln["bottom"] - (box.y + box.h)
            tol = 0.5
            problems = []
            if over_l > tol or over_r > tol:
                problems.append(f"{max(over_l, over_r):.1f}px wider than its box")
            if over_t > tol + (0.15 * ln["size"] if not thai else 0):
                problems.append(f"marks/ascent rise {over_t:.1f}px above the box top")
            if over_b > tol:
                problems.append(f"descent drops {over_b:.1f}px below the box bottom")
            if problems:
                findings.append(
                    f"{path.name}: text {label!r} ({ln['size']:g}px) overflows box "
                    f"({box.x:g},{box.y:g} {box.w:g}x{box.h:g}): " + "; ".join(problems)
                    + f" — needs box ≥ {ceil4(ln['w'] + 8)}px wide"
                )
        if len(thai_lines) > 1:
            ys = sorted(ln["y"] for ln in t.lines)
            pitches = [b - a for a, b in zip(ys, ys[1:]) if b - a > 0.1]
            size = max(ln["size"] for ln in thai_lines)
            if pitches and min(pitches) < size * 1.58:
                findings.append(
                    f"{path.name}: multi-line Thai {thai_lines[0]['text'][:30]!r} has line pitch "
                    f"{min(pitches):g}px < 1.6em ({size * 1.6:.0f}px) — tone marks will touch the line above")
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="*", help="label(s) to measure")
    ap.add_argument("--size", type=float, default=12.0, help="font size in px (default 12)")
    ap.add_argument("--weight", type=float, default=400, help="400/500/600/700 (default 400)")
    ap.add_argument("--mono", action="store_true", help="Geist Mono instead of Sarabun")
    ap.add_argument("--italic", action="store_true")
    ap.add_argument("--caps", action="store_true", help="apply text-transform: uppercase")
    ap.add_argument("--tracking", type=float, default=0.0, help="letter-spacing in em (e.g. 0.14)")
    ap.add_argument("--pad", type=float, default=12.0, help="horizontal padding per side for the box suggestion")
    ap.add_argument("--check", nargs="+", metavar="FILE", help="check finished diagram(s) instead")
    args = ap.parse_args(argv)
    if args.check:
        total = []
        for f in args.check:
            try:
                total += check_file(Path(f))
            except Exception as exc:  # report, keep going
                total.append(f"{Path(f).name}: could not parse ({exc})")
        for line in total:
            print(line)
        print(f"Summary: {len(args.check)} file(s) checked, {len(total)} text finding(s).")
        return 1 if total else 0
    if not args.text:
        ap.error("pass text to measure, or --check FILE")
    return measure_cli(args)


if __name__ == "__main__":
    sys.exit(main())

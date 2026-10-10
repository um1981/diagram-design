#!/usr/bin/env python3
"""Render a diagram HTML file to PNG — runs automatically after every diagram.

    python3 scripts/export_png.py my-diagram.html              # -> my-diagram.png (2x)
    python3 scripts/export_png.py my-diagram.html out.png --scale 3
    python3 scripts/export_png.py my-diagram.html --engine resvg

Diagram only: the first top-level <svg> (header/cards are dropped, as in
references/export.md). The bundled fonts in assets/fonts/ (Sarabun, Geist Mono)
are always used, so the PNG is identical online or offline and Thai shapes
correctly.

Engines, tried in order with --engine auto (default):

1. chromium  — Playwright + Chromium (pixel-identical to the browser). Uses an
               installed Playwright browser, or a system Chromium/Chrome.
2. resvg     — the resvg-py wheel (Rust renderer with HarfBuzz-grade shaping;
               no browser, no system libraries). If it is missing the script
               runs `pip install resvg-py` once (disable with --no-install).

Exit codes: 0 ok, 2 bad input, 3 no engine available.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE.parent / "assets" / "fonts"
sys.path.insert(0, str(HERE))
import export_svg  # noqa: E402

FONT_FACES = [
    ("Sarabun", 400, "normal", "Sarabun-Regular.ttf"),
    ("Sarabun", 500, "normal", "Sarabun-Medium.ttf"),
    ("Sarabun", 600, "normal", "Sarabun-SemiBold.ttf"),
    ("Sarabun", 700, "normal", "Sarabun-Bold.ttf"),
    ("Sarabun", 400, "italic", "Sarabun-Italic.ttf"),
    ("Geist Mono", 400, "normal", "GeistMono-Regular.ttf"),
    ("Geist Mono", 500, "normal", "GeistMono-Medium.ttf"),
    ("Geist Mono", 600, "normal", "GeistMono-Medium.ttf"),
]


def font_face_css() -> str:
    rules = []
    for fam, weight, style, fname in FONT_FACES:
        url = (FONT_DIR / fname).resolve().as_uri()
        rules.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url('{url}') format('truetype');}}"
        )
    return "\n".join(rules)


# ───────────────────────── chromium ─────────────────────────

def _chromium_candidates() -> list[str | None]:
    cands: list[str | None] = [None]  # Playwright's own managed browser first
    for env in ("CHROME_PATH", "CHROMIUM_PATH", "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
        if os.environ.get(env):
            cands.append(os.environ[env])
    for pattern in ("/opt/pw-browsers/chromium*/chrome-linux*/chrome", "/opt/pw-browsers/chromium",
                    os.path.expanduser("~/.cache/ms-playwright/chromium*/chrome-linux*/chrome")):
        cands += sorted(glob.glob(pattern))
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        found = shutil.which(name)
        if found:
            cands.append(found)
    return cands


def render_chromium(src: Path, out: Path, scale: float) -> str:
    from playwright.sync_api import sync_playwright  # raises ImportError if absent

    html = src.read_text(encoding="utf-8")
    query = "?motion=static" if "data-motion-root" in html else ""
    last_err = None
    with sync_playwright() as p:
        for exe in _chromium_candidates():
            try:
                browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            except Exception as exc:  # try the next candidate
                last_err = exc
                continue
            try:
                page = browser.new_page(device_scale_factor=scale, viewport={"width": 1600, "height": 1000})
                # Offline-safe: block every network request; fonts come from the bundle.
                page.route(re.compile(r"^https?://"), lambda route: route.abort())
                page.goto(src.resolve().as_uri() + query, wait_until="domcontentloaded")
                page.add_style_tag(content=font_face_css())
                page.evaluate(
                    """async () => {
                        const specs = ['400 12px Sarabun','500 12px Sarabun','600 12px Sarabun',
                                       '700 12px Sarabun','italic 400 12px Sarabun','400 12px "Geist Mono"',
                                       '500 12px "Geist Mono"'];
                        await Promise.all(specs.map(s => document.fonts.load(s, 'กขค Abc')));
                        await document.fonts.ready;
                    }"""
                )
                svg = page.locator("svg").first
                # Render at exactly viewBox width so PNG = viewBox x scale, and
                # release clipping ancestors so wide presets are captured whole.
                svg.evaluate(
                    "el => { const vb = (el.getAttribute('viewBox') || '').split(/[\\s,]+/).map(Number);"
                    " if (vb.length === 4 && vb[2] > 0) { el.style.setProperty('width', vb[2] + 'px', 'important'); el.style.setProperty('height', vb[3] + 'px', 'important');"
                    " el.style.setProperty('min-width', '0', 'important'); el.style.setProperty('max-width', 'none', 'important'); }"
                    " for (let a = el.parentElement; a; a = a.parentElement)"
                    " a.style.setProperty('overflow', 'visible', 'important'); }"
                )
                box = svg.bounding_box()
                vb = svg.evaluate("el => (el.getAttribute('viewBox') || '').split(/[\\s,]+/).map(Number)")
                if box and len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
                    # exact viewBox x scale pixels (element screenshots round sub-pixel boxes outward)
                    page.screenshot(path=str(out), omit_background=True, full_page=True,
                                    clip={"x": round(box["x"]), "y": round(box["y"]),
                                          "width": vb[2], "height": vb[3]})
                else:
                    svg.screenshot(path=str(out), omit_background=True)
                return f"chromium ({exe or 'playwright-managed'})"
            finally:
                browser.close()
    raise RuntimeError(f"no launchable Chromium ({last_err})")


# ───────────────────────── resvg ─────────────────────────

def _resolve_css_vars(svg: str) -> str:
    """resvg's CSS engine has no var(); inline custom properties."""
    variables = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;}{]+)", svg))

    def sub(text: str, depth: int = 0) -> str:
        if depth > 8 or "var(" not in text:
            return text
        return sub(re.sub(
            r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)",
            lambda m: variables.get(m.group(1), m.group(2) or "").strip(),
            text,
        ), depth + 1)

    return sub(svg)


def render_resvg(src: Path, out: Path, scale: float, allow_install: bool) -> str:
    try:
        import resvg_py  # type: ignore
    except ImportError:
        if not allow_install:
            raise
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", "resvg-py"]
        if subprocess.run(cmd, capture_output=True).returncode != 0:
            subprocess.run(cmd + ["--break-system-packages"], capture_output=True, check=True)
        import importlib
        importlib.invalidate_caches()
        import resvg_py  # type: ignore
    raw = src.read_text(encoding="utf-8")
    svg = raw if src.suffix.lower() == ".svg" else export_svg.export_svg_document(raw, src)
    svg = re.sub(r"@import[^;]*;", "", svg)
    svg = _resolve_css_vars(svg)
    if svg.startswith("<?xml"):
        svg = svg.split("?>", 1)[1]
    png = resvg_py.svg_to_bytes(
        svg_string=svg,
        font_dirs=[str(FONT_DIR)],
        font_family="Sarabun",
        sans_serif_family="Sarabun",
        monospace_family="Geist Mono",
        zoom=scale,
        text_rendering="optimize_legibility",
    )
    out.write_bytes(bytes(png))
    return "resvg"


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="diagram .html (or a standalone .svg)")
    ap.add_argument("output", type=Path, nargs="?", help="output .png (default: next to source)")
    ap.add_argument("--scale", type=float, default=2.0, help="device scale factor 1-4 (default 2; print = 3)")
    ap.add_argument("--engine", choices=["auto", "chromium", "resvg"], default="auto")
    ap.add_argument("--no-install", action="store_true", help="never pip-install resvg-py")
    args = ap.parse_args(argv)

    src: Path = args.source
    if not src.is_file():
        print(f"error: source not found: {src}", file=sys.stderr)
        return 2
    if not 1 <= args.scale <= 4:
        print("error: --scale must be between 1 and 4 (redraw at a bigger preset instead)", file=sys.stderr)
        return 2
    out = args.output or src.with_suffix(".png")
    errors = []
    engines = ["chromium", "resvg"] if args.engine == "auto" else [args.engine]
    if src.suffix.lower() == ".svg" and "chromium" in engines:
        engines.remove("chromium")
        engines.append("resvg") if "resvg" not in engines else None
    for engine in engines:
        try:
            if engine == "chromium":
                used = render_chromium(src, out, args.scale)
            else:
                used = render_resvg(src, out, args.scale, not args.no_install)
            w, h = png_size(out)
            print(f"{out}  ({w}x{h}px, engine: {used})")
            return 0
        except Exception as exc:
            errors.append(f"{engine}: {type(exc).__name__}: {exc}".splitlines()[0][:300])
    print("error: no PNG engine available:\n  " + "\n  ".join(errors), file=sys.stderr)
    print("Deliver the HTML (and SVG via export_svg.py) and tell the user PNG export was unavailable.",
          file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())

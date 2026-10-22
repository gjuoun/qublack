"""Compare CJK cell/ink geometry across faces, using each face's own advance.

Reports, over the running-text character sample: mean ink width/height, CJK advance, derived
side bearing, ink aspect (h/w — 0.91 is the donor's flat shape, >1 reads tall-and-thin), and the
CJK-ink / Latin-x-height ratio that decides whether the Latin sits right next to the CJK.
"""
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

TEXT = (
    "只对 web-compat 那条。有 HTML，也没有 CSS 文件，另一个是 app.js。"
    "编译产物是 JSX → QuickJS 执行的 app.js + 二进制 app.pak，Tailwind 类名变成样式表。"
    "小字号正文：React、渲染器、应用代码、字体图集、图片都在 app.pak 里。"
)


def load(p):
    f = TTFont(p, lazy=True)
    for tag in ("vmtx", "vhea", "VORG"):
        if tag in f:
            del f[tag]
    return f


def measure(p):
    f = load(p)
    upm = f["head"].unitsPerEm
    gs, cmap, hm = f.getGlyphSet(), f.getBestCmap(), f["hmtx"].metrics
    hw, hh, ad, bear = [], [], [], []
    for ch in sorted(set(TEXT)):
        if ord(ch) < 0x2E80:
            continue
        gn = cmap.get(ord(ch))
        if not gn:
            continue
        bp = BoundsPen(gs)
        gs[gn].draw(bp)
        if not bp.bounds:
            continue
        x0, y0, x1, y1 = bp.bounds
        w, h = (x1 - x0) / upm, (y1 - y0) / upm
        adv = hm[gn][0] / upm
        hw.append(w)
        hh.append(h)
        ad.append(adv)
        bear.append((adv - w) / 2)
    # latin x-height
    gx = cmap.get(ord("x"))
    bp = BoundsPen(gs)
    gs[gx].draw(bp)
    xh = (bp.bounds[3] - bp.bounds[1]) / upm
    m = lambda v: sum(v) / len(v)
    return m(hw), m(hh), m(ad), m(bear), xh


print(f"{'face':38s}{'ink w':>7s}{'ink h':>7s}{'adv':>7s}{'bearing':>8s}{'h/w':>7s}{'CJK/x':>7s}")
for p in sys.argv[1:]:
    w, h, a, b, xh = measure(p)
    print(f"  {p.split('/')[-1][:36]:36s}{w:7.3f}{h:7.3f}{a:7.3f}{b:8.3f}{h/w:7.3f}{h/xh:7.2f}")

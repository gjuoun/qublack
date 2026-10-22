#!/usr/bin/env python3
"""Pack the release: eight TTFs + OFL + README into a deterministic zip, plus SHA256SUMS.

usage: pack_release.py --tag v1.0.0 [--fonts fonts] [--dist dist]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qublack_font import measure  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STYLES = ["Regular", "Italic", "Bold", "BoldItalic"]
FIXED_TIME = (2026, 10, 22, 0, 0, 0)

README = """黢黑 QuBlack — {version}
{underline}

一个为代码而生的双语字体家族：QuBlack Mono 严格 2:1 中英对齐（一个汉字 = 两个 ASCII 格，
实测 2.000），QuBlack Sans 是它的比例兄弟，用于文档、网页与界面。汉字来自思源黑体（经 Sarasa
Gothic），拉丁来自 Recursive Linear；整个家族可再分发、可商用，SIL OFL 1.1。

A bilingual family built for code: QuBlack Mono holds a strict 2:1 grid (one hanzi = two ASCII
cells, measured at 2.000); QuBlack Sans is its proportional sibling for documents, web and UI.
Hanzi come from Source Han Sans (via Sarasa Gothic), Latin from Recursive Linear. The whole
family is redistributable under the SIL Open Font License 1.1.

家族 / family
-------------
  QuBlack Mono  终端、代码     upm 833    汉字 1.200em   ASCII 0.600em   等宽 2:1
  QuBlack Sans  文档、网页、界面 upm 1000  汉字 1.000em   ASCII 0.600em

各四个字重：Regular / Italic / Bold / BoldItalic（8 个 TTF）。
四个 emoji 码位已从 cmap 剥离，彩色 emoji 走系统字体。

安装 / install
--------------
  macOS:   unzip -o {zipname} -d ~/Library/Fonts/
  Linux:   mkdir -p ~/.local/share/fonts && unzip -o {zipname} -d ~/.local/share/fonts/ && fc-cache -f
  网页:    font-family: "QuBlack Sans", sans-serif;
  终端:    font-family = "QuBlack Mono"

字体在进程启动时加载：浏览器、终端、Electron 客户端要完全退出重开才会用上新文件。

授权 / licence
--------------
SIL Open Font License 1.1 — 见包内 OFL.txt。本家族是衍生作品：汉字轮廓来自 Source Han Sans /
Sarasa Gothic（SIL OFL 1.1），拉丁来自 Recursive（SIL OFL 1.1），以新家族名发布。
见 https://github.com/gjuoun/qublack 的 NOTICE.md。
"""


def render_readme(version: str, zipname: str) -> str:
    return README.format(version=version, underline="=" * (len("黢黑 QuBlack — ") + len(version)), zipname=zipname)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v1.0.0")
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts")
    parser.add_argument("--dist", type=Path, default=REPO / "dist")
    args = parser.parse_args()

    version = args.tag.lstrip("v")
    faces = [args.fonts / f"QuBlack{family}-{style}.ttf" for family in ("Mono", "Sans") for style in STYLES]
    missing = [str(p) for p in faces if not p.exists()]
    if missing:
        raise SystemExit("missing faces: " + ", ".join(missing))

    args.dist.mkdir(parents=True, exist_ok=True)
    zipname = f"QuBlack-family-{version}.zip"
    zip_path = args.dist / zipname
    readme = render_readme(version, zipname)
    (args.dist / "README-release.txt").write_text(readme, encoding="utf-8")

    entries: list[tuple[str, bytes]] = [(p.name, p.read_bytes()) for p in faces]
    entries.append(("OFL.txt", (REPO / "LICENSE").read_bytes()))
    entries.append(("README.txt", readme.encode("utf-8")))
    entries.append(("NOTICE.md", (REPO / "NOTICE.md").read_bytes()))

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (args.dist / "SHA256SUMS").write_text(f"{digest}  {zipname}\n", encoding="utf-8")

    for path in faces:
        data = measure(path)
        print(f"  {path.name:30s} {path.stat().st_size:>10,} B  {data['glyphs']:>6} glyphs")
    print(f"packed {zip_path.name}: {zip_path.stat().st_size:,} B  sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

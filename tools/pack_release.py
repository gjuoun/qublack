#!/usr/bin/env python3
"""Pack the release: TTF + TTC + WOFF2, a deterministic zip and a SHA256SUMS over everything.

  TTF    eight standalone faces — the system-install format
  TTC    QuBlackMono.ttc / QuBlackSans.ttc — four faces per file, shared tables (smaller bundle)
  WOFF2  one full face per file for @font-face self-hosting (never WOFF1, no OTF: the outlines
         are glyf, and a CFF conversion would only lose hinting and size)

usage: pack_release.py --tag v1.0.4 [--fonts fonts] [--dist dist]
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qublack_font import measure  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STYLES = ["Regular", "Italic", "Bold", "BoldItalic"]
FAMILIES = ["Mono", "Sans"]
FIXED_TIME = (2026, 10, 22, 0, 0, 0)

README = """黢黑 Qu Black — {version}
{underline}

一个为代码而生的双语字体家族：Qu Black Mono 严格 2:1 中英对齐（一个汉字 = 两个 ASCII 格，
实测 2.000），Qu Black Sans 是它的比例兄弟，用于文档、网页与界面。汉字来自思源黑体（经 Sarasa
Gothic），拉丁来自 Recursive Linear；整个家族可再分发、可商用，SIL OFL 1.1。

A bilingual family built for code: Qu Black Mono holds a strict 2:1 grid (one hanzi = two ASCII
cells, measured at 2.000); Qu Black Sans is its proportional sibling for documents, web and UI.
Hanzi come from Source Han Sans (via Sarasa Gothic), Latin from Recursive Linear. The whole
family is redistributable under the SIL Open Font License 1.1.

格式 / formats
-------------
  TTF    QuBlack{{Mono,Sans}}-{{Regular,Italic,Bold,BoldItalic}}.ttf
         系统安装（macOS ~/Library/Fonts、Linux ~/.local/share/fonts、Windows 双击安装）。
         Installs into the OS; every app picks it up on the next launch.
  TTC    QuBlackMono.ttc / QuBlackSans.ttc
         每个文件含同一家族四体，共享 cmap/feature 等公共表，体积比四个 TTF 小。
         Four faces per file with shared tables — the smaller bundle, same outlines.
  WOFF2  QuBlack{{Mono,Sans}}-{{Regular,Italic,Bold,BoldItalic}}.woff2
         网页 @font-face 自托管，整面 brotli 压缩（约 8.6 MB/面）。WOFF1/EOT/OTF 不提供。
         Self-host with @font-face. WOFF2 only — not WOFF1, and no OTF (the outlines are glyf).

家族 / family
-------------
  Qu Black Mono  终端、代码     upm 833    汉字 1.200em   ASCII 0.600em   等宽 2:1
  Qu Black Sans  文档、网页、界面 upm 1000  汉字 1.000em   ASCII 0.600em

各四个字重：Regular / Italic / Bold / BoldItalic。彩色 emoji 走系统字体（cmap 占位符已剥离）。

安装 / install
--------------
  macOS:   unzip -o {zipname} -d ~/Library/Fonts/
  Linux:   mkdir -p ~/.local/share/fonts && unzip -o {zipname} -d ~/.local/share/fonts/ && fc-cache -f
  网页:    @font-face {{ font-family: "Qu Black Sans"; src: url("QuBlackSans-Regular.woff2") format("woff2"); }}
  终端:    font-family = "Qu Black Mono"

字体在进程启动时加载：浏览器、终端、Electron 客户端要完全退出重开才会用上新文件。

授权 / licence
--------------
SIL Open Font License 1.1 — 见包内 OFL.txt。本家族是衍生作品：汉字轮廓来自 Source Han Sans /
Sarasa Gothic（SIL OFL 1.1），拉丁来自 Recursive（SIL OFL 1.1），以新家族名发布。
见 https://github.com/gjuoun/qublack 的 NOTICE.md。
"""


def render_readme(version: str, zipname: str) -> str:
    title = "黢黑 Qu Black — " + version
    return README.format(version=version, underline="=" * len(title), zipname=zipname)


def build_ttc(family: str, faces: list[Path], out: Path) -> int:
    """Write one TTC: the four faces of a family, sharing every table whose bytes match."""
    ttc = TTCollection()
    ttc.fonts = [TTFont(str(face)) for face in faces]
    ttc.save(str(out))
    return out.stat().st_size


def build_woff2(face: Path, out: Path) -> int:
    font = TTFont(str(face))
    font.flavor = "woff2"
    font.save(str(out))
    return out.stat().st_size


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v1.0.4")
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts/ttf")
    parser.add_argument("--dist", type=Path, default=REPO / "dist")
    parser.add_argument("--skip-woff2", action="store_true", help="reuse existing .woff2 files")
    parser.add_argument("--vf", type=Path, default=REPO / "fonts/vf", help="dir with the variable faces")
    args = parser.parse_args()

    version = args.tag.lstrip("v")
    faces = [args.fonts / f"QuBlack{family}-{style}.ttf" for family in FAMILIES for style in STYLES]
    missing = [str(path) for path in faces if not path.exists()]
    if missing:
        raise SystemExit("missing faces: " + ", ".join(missing))

    args.dist.mkdir(parents=True, exist_ok=True)
    zipname = f"QuBlack-family-{version}.zip"
    zip_path = args.dist / zipname
    readme = render_readme(version, zipname)
    (args.dist / "README-release.txt").write_text(readme, encoding="utf-8")

    # TTC per family — four faces, shared tables.
    ttcs: list[Path] = []
    for family in FAMILIES:
        out = args.dist / f"QuBlack{family}.ttc"
        size = build_ttc(family, [args.fonts / f"QuBlack{family}-{style}.ttf" for style in STYLES], out)
        ttcs.append(out)
        print(f"  {out.name:24s} {size:>10,} B")

    # One full-face WOFF2 per face (brotli, ~60 s each).
    woff2: list[Path] = []
    for face in faces:
        out = args.dist / (face.stem + ".woff2")
        if args.skip_woff2 and out.exists():
            size = out.stat().st_size
        else:
            size = build_woff2(face, out)
        woff2.append(out)
        print(f"  {out.name:32s} {size:>10,} B")

    entries: list[tuple[str, bytes]] = [(path.name, path.read_bytes()) for path in faces]
    entries += [(path.name, path.read_bytes()) for path in ttcs]
    entries += [(path.name, path.read_bytes()) for path in woff2]

    # The static faces ship as standalone assets too, not only inside the zip.
    for path in faces:
        shutil.copy2(path, args.dist / path.name)

    # The two variable faces (wght 400-700) — standalone assets and zip members.
    vfs: list[Path] = (
        sorted(p for p in args.vf.glob("*.ttf") if "[wght]" in p.name) if args.vf.exists() else []
    )
    for path in vfs:
        shutil.copy2(path, args.dist / path.name)
    entries += [(path.name, path.read_bytes()) for path in vfs]

    entries.append(("OFL.txt", (REPO / "OFL.txt").read_bytes()))
    entries.append(("README.txt", readme.encode("utf-8")))
    entries.append(("NOTICE.md", (REPO / "NOTICE.md").read_bytes()))

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)

    # SHA256SUMS covers the zip and every standalone asset the release carries.
    sums = [(sha256(zip_path), zipname)]
    sums += [(sha256(path), path.name) for path in ttcs]
    sums += [(sha256(path), path.name) for path in woff2]
    sums += [(sha256(args.dist / path.name), path.name) for path in vfs]
    (args.dist / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for digest, name in sorted(sums, key=lambda item: item[1])),
        encoding="utf-8",
    )

    for path in faces:
        data = measure(path)
        print(f"  {path.name:30s} {path.stat().st_size:>10,} B  {data['glyphs']:>6} glyphs")
    print(f"packed {zip_path.name}: {zip_path.stat().st_size:,} B  sha256 {sha256(zip_path)}")
    print(f"assets: {len(faces)} TTF, {len(ttcs)} TTC, {len(woff2)} WOFF2, {len(vfs)} VF + zip + sums")
    return 0


if __name__ == "__main__":
    sys.exit(main())

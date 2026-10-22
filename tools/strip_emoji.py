#!/usr/bin/env python3
"""Strip Emoji=Yes codepoints from one face's cmap, in place, keeping a .bak-emoji copy.

The build already strips emoji, so this is the manual repair tool for a face that came from
elsewhere. The keep-list matches the build: ASCII, © ® ™, arrows, box drawing, blocks, geometric
shapes, braille and PUA.

usage: strip_emoji.py <face.ttf> [...]
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import emoji_codepoints, keep_codepoint  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def strip(path: Path, emoji: set[int]) -> int:
    backup = path.with_suffix(path.suffix + ".bak-emoji")
    if not backup.exists():
        shutil.copy2(path, backup)
    font = TTFont(str(path))
    for tag in ("vmtx", "vhea", "VORG"):
        if tag in font:
            del font[tag]
    removed = 0
    for table in font["cmap"].tables:
        for cp in list(table.cmap):
            if cp in emoji and not keep_codepoint(cp):
                del table.cmap[cp]
                removed += 1
    font.save(str(path))
    return removed


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    emoji = emoji_codepoints(REPO)
    for argument in sys.argv[1:]:
        path = Path(argument)
        print(f"{path.name}: removed {strip(path, emoji)} emoji cmap entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())

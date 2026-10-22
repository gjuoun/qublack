"""Where the hanzi-adjacent symbols belong — one target shared by the build and the audit.

Two references disagree in a 2:1 cell: hanzi-flush is perfect in Chinese but oversized in English;
cap-relative is the reverse. Delta 8 blended the brackets; delta 10 extended the same treatment to
every census mark that measured more than 6 points off Sarasa.
"""

from __future__ import annotations

import os

from fontTools.ttLib import TTFont

QUOTES = ('"', "'")
BRACKETS = ['"', "'", "(", ")", "[", "]", "{", "}", "/", "\\", "|"]
MARKS = ["`", "*", "!", "%", "&", "?", "@", "$", "#", "<", ">", "^", "+", ":", ";", "-", "=", "_"]
# Comma, period and tilde were ruled normal against the 6-point trigger, but the bold faces still
# sat 4-8 points out; the nudge is sub-percent and lets the census hold one 2-point line.
BASELINE_MARKS = [",", ".", "~"]
FIXED_SYMBOLS = BRACKETS + MARKS + BASELINE_MARKS

# Every printable ASCII punctuation mark, the common Latin-1 symbols and the arrows.
ASCII_PUNCTUATION = list("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
LATIN1 = list("§¶°±×÷•")
ARROWS = list("←↑→↓↔")
CENSUS = ASCII_PUNCTUATION + LATIN1 + ARROWS

QUOTE_BLEND = float(os.environ.get("QUBLACK_QUOTE_BLEND", "0.75"))
SYMBOL_BLEND = float(os.environ.get("QUBLACK_SYMBOL_BLEND", "0.9"))


def blend_for(char: str) -> float:
    return QUOTE_BLEND if char in QUOTES else SYMBOL_BLEND


def _ink_units(glyph) -> tuple[float, float, float]:
    top, bottom = float(glyph.yMax), float(glyph.yMin)
    return top, bottom, top - bottom


def boxes(font: TTFont) -> tuple[float, float, float, float]:
    """(hanzi top, hanzi height, cap top, cap height) in font units."""
    han = font["glyf"][font.getBestCmap()[ord("汉")]]
    cap = font["glyf"][font.getBestCmap()[ord("H")]]
    han.recalcBounds(font["glyf"])
    cap.recalcBounds(font["glyf"])
    han_top, _, han_h = _ink_units(han)
    cap_top, _, cap_h = _ink_units(cap)
    return han_top, han_h, cap_top, cap_h


def target(font: TTFont, reference: TTFont, char: str) -> tuple[float, float] | None:
    """(ink top, ink height) in font units, blended between the two references."""
    ref_han_top, ref_han_h, ref_cap_top, ref_cap_h = boxes(reference)
    han_top, han_h, cap_top, cap_h = boxes(font)
    ref_name = reference.getBestCmap().get(ord(char))
    if ref_name is None:
        return None
    ref_glyph = reference["glyf"][ref_name]
    ref_glyph.recalcBounds(reference["glyf"])
    ref_top, _, ref_height = _ink_units(ref_glyph)

    blend = blend_for(char)
    han_target_top = han_top - ((ref_han_top - ref_top) / ref_han_h) * han_h
    han_target_height = (ref_height / ref_han_h) * han_h
    cap_target_top = cap_top - ((ref_cap_top - ref_top) / ref_cap_h) * cap_h
    cap_target_height = (ref_height / ref_cap_h) * cap_h

    return (
        han_target_top * blend + cap_target_top * (1 - blend),
        han_target_height * blend + cap_target_height * (1 - blend),
    )

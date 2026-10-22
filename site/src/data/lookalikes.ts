export interface LookalikeRow {
  glyphs: string[];
  label: string;
  /** What to look for, in one line. */
  note: string;
}

/** Latin confusables first, then the Chinese near-forms a font has to keep apart. */
export const LOOKALIKES: LookalikeRow[] = [
  {
    glyphs: ["0", "O", "o"],
    label: "zero / upper-o / lower-o",
    note: "slashed zero in the mono face",
  },
  {
    glyphs: ["1", "l", "I", "|", "i"],
    label: "one / lower-l / upper-i / bar / dotted-i",
    note: "five different silhouettes",
  },
  { glyphs: ["5", "S", "s"], label: "five / upper-s / lower-s", note: "flat top vs. spine" },
  { glyphs: ["rn", "m"], label: "r+n / m", note: "the classic identifier trap" },
  { glyphs: ["vv", "w"], label: "v+v / w", note: "count the vertices" },
  { glyphs: ["8", "B"], label: "eight / upper-b", note: "closed counters differ" },
  { glyphs: ["未", "末"], label: "未 (wèi) / 末 (mò)", note: "the top stroke is longer in 末" },
  {
    glyphs: ["己", "已", "巳"],
    label: "己 (jǐ) / 已 (yǐ) / 巳 (sì)",
    note: "how far the middle stroke opens",
  },
  { glyphs: ["田", "由", "甲"], label: "田 / 由 / 甲", note: "which way the vertical escapes" },
  { glyphs: ["人", "入"], label: "人 (rén) / 入 (rù)", note: "the left stroke's lean" },
  { glyphs: ["日", "曰"], label: "日 (rì) / 曰 (yuē)", note: "height of the box" },
  { glyphs: ["干", "于", "千"], label: "干 / 于 / 千", note: "one hook, one lean" },
];

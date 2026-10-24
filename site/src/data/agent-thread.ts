/**
 * The conversation the homepage specimen renders: a real-shaped agent exchange. Every agent turn
 * is **markdown**, because that is what agent output looks like in the wild — a bold verdict, a
 * bulleted explanation, a fenced code block, inline identifiers. The container renders it with
 * Qu Black: prose in the sans face, code and identifiers in the mono face, no syntax colours.
 */

export interface ChatMessage {
  role: "user" | "agent";
  /** Markdown source, rendered by site/src/lib/markdown.ts. */
  markdown: string;
  /** Small meta line: model / duration / mode. */
  meta: string;
}

export const THREAD: ChatMessage[] = [
  {
    role: "user",
    meta: "you · 14:02",
    markdown: "我们的 checkout 页在 Safari 上错位了，价格那一列会被挤出去。能看一下吗？",
  },
  {
    role: "agent",
    meta: "agent · 4s · 3 files",
    markdown: [
      "**Found it.** 价格列少了 `minmax(0, …)`，一个长中文商品名就把 grid track 顶出了视口。",
      "",
      "Qu Black Mono 里 **汉字 = 2 个 ASCII 格**，所以两条轨道同样宽：",
      "",
      "```text",
      "汉汉 | aaaa",
      "国国 | bbbb",
      "```",
      "",
      "修法是把两条轨道都设成可收缩的：",
      "",
      "```tsx",
      '- <div className="grid grid-cols-[1fr_auto]">',
      '+ <div className="grid grid-cols-[minmax(0,1fr)_auto]">',
      "```",
    ].join("\n"),
  },
  {
    role: "user",
    meta: "you · 14:05",
    markdown: "改完跑测试，顺便把中文断行也修了。",
  },
  {
    role: "agent",
    meta: "agent · 9s · tests green",
    markdown: [
      "**Tests green.** `bun test checkout` → 12 passed.",
      "",
      "- 全角标点不留在行首",
      "- `图`、`国` 这类全角字不会被拆成两半",
      "",
      "```css",
      ".chat-bubble {",
      "  word-break: normal;",
      "  overflow-wrap: anywhere;",
      "  line-height: 1.78; /* 中文行高不套拉丁的 1.5 */",
      "}",
      "```",
    ].join("\n"),
  },
];

/** Canned markdown replies for the input box — streamed, one per send, in order. */
export const REPLIES: string[] = [
  [
    "**收到。** 所有字符落在同一张网格上：`汉` 占 2 格，`a` 占 1 格。",
    "",
    "```text",
    "汉汉 | aaaa",
    "国国 | bbbb",
    "```",
  ].join("\n"),
  "**Fixed.** 只动渲染层：`font-family` 换成 Qu Black，行高按中英分别设，其余不动。",
  "**Tests pass** — 12 passed, 0 failed. 要我把同样的修正补到移动端断点吗？",
];

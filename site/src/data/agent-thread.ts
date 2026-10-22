/**
 * The conversation the homepage specimen renders: a real-shaped agent exchange, English and
 * Chinese and code in the same answer. It exists so the container is a live specimen — the mono
 * face carries the code and the inline identifiers, the sans face carries the prose.
 */

export interface ChatBlock {
  kind: "text" | "code";
  /** Text, or the exact code for a code block. */
  body: string;
  /** Language label for a code block. */
  lang?: string;
}

export interface ChatMessage {
  role: "user" | "agent";
  blocks: ChatBlock[];
  /** Small meta line: model / duration / mode. */
  meta: string;
}

export const THREAD: ChatMessage[] = [
  {
    role: "user",
    meta: "you · 14:02",
    blocks: [
      {
        kind: "text",
        body: "我们的 checkout 页在 Safari 上错位了，价格那一列会被挤出去。能看一下吗？",
      },
    ],
  },
  {
    role: "agent",
    meta: "agent · 4s · 3 files",
    blocks: [
      {
        kind: "text",
        body: "Found it: the price column has no minmax(0, …), so a long 中文 product name pushes the track past the viewport. 汉字在等宽网格里是 1.200em，英文只有 0.600em —— 按字符数估宽就会差一倍。",
      },
      {
        kind: "code",
        lang: "tsx",
        body: `- <div className="grid grid-cols-[1fr_auto]">
+ <div className="grid grid-cols-[minmax(0,1fr)_auto]">`,
      },
    ],
  },
  {
    role: "user",
    meta: "you · 14:05",
    blocks: [{ kind: "text", body: "改完跑测试，顺便把中文断行也修了。" }],
  },
  {
    role: "agent",
    meta: "agent · 9s · tests green",
    blocks: [
      {
        kind: "text",
        body: "`bun test checkout` → 12 passed. 断行也一并收紧了：全角标点不留在行首，`图`、`国` 这类字不会被拆成两半。",
      },
      {
        kind: "code",
        lang: "css",
        body: `.chat-bubble {
  word-break: normal;
  overflow-wrap: anywhere;
  line-height: 1.78; /* 中文行高不套拉丁的 1.5 */
}`,
      },
    ],
  },
];

/** Canned replies for the input box — streamed, one per send, in order. */
export const REPLIES: string[] = [
  "收到。QuBlack Mono 让 汉字 与 ASCII 落在同一张网格上：一个汉字正好两个字符宽，所以 agent 的表格、diff 和日志不会错位。",
  "Fixed. 这次改动只碰渲染层：font-family 换成 QuBlack，行高按中英分别设，其余不动。",
  "Tests pass — 12 passed, 0 failed. 需要我把同样的修正补到移动端断点吗？",
];

import { expect, test } from "bun:test";
import { renderInline, renderMarkdown } from "./markdown.ts";

test("a fenced block becomes one flat code plate, never a highlighted one", () => {
  const html = renderMarkdown("before\n\n```tsx\nconst a = 1;\n```\n");
  expect(html).toContain('<pre data-md-code="tsx"><code>const a = 1;</code></pre>');
  expect(html).not.toContain("<span");
});

test("an unterminated fence still renders as code (streaming in progress)", () => {
  const html = renderMarkdown("```css\n.a { color: red; }");
  expect(html).toContain('<pre data-md-code="css"><code>.a { color: red; }</code></pre>');
});

test("bold renders as a strong tag", () => {
  expect(renderInline("**Tests green.** done")).toBe(
    "<strong data-md-bold>Tests green.</strong> done",
  );
});

test("inline code is code, and bold inside it stays literal", () => {
  expect(renderInline("run `**not bold**` now")).toBe(
    "run <code data-md-inline-code>**not bold**</code> now",
  );
});

test("markup in the source is escaped, not executed", () => {
  const html = renderMarkdown('**Summary** <img src=x onerror="alert(1)"> & done');
  expect(html).toContain("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");
  expect(html).not.toContain("<img");
  expect(html).toContain("&amp; done");
});

test("bullets and headings keep their structure", () => {
  const html = renderMarkdown("## Notes\n- one\n- two\n");
  expect(html).toContain("<p data-md-heading>Notes</p>");
  expect(html).toContain("<ul data-md-list><li>one</li><li>two</li></ul>");
});

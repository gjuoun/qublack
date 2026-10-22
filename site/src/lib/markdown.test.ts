import { expect, test } from "bun:test";
import { dedent, renderInline, renderMarkdown } from "./markdown.ts";

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

test("template indentation on later lines is stripped (the ghost-indent bug)", () => {
  // Exactly the leak shape: first line at column 0, the rest carrying a template's indent.
  const source = ["```tsx", '- <div className="a">', '    + <div className="b">', "```"].join("\n");
  const html = renderMarkdown(source);
  expect(html).toContain(
    "<code>- &lt;div className=&quot;a&quot;&gt;\n+ &lt;div className=&quot;b&quot;&gt;</code>",
  );
  expect(html).not.toContain("\n    +");
});

test("a uniformly indented block keeps its own indent", () => {
  expect(dedent(["    a", "    b"])).toEqual(["    a", "    b"]);
});

test("nested code keeps its relative indentation", () => {
  const body = ["}", "  word-break: normal;", "  overflow-wrap: anywhere;", "", "}"];
  expect(dedent([".chat-bubble {", ...body])).toEqual([".chat-bubble {", ...body]);
});

test("a block that closes at the left margin is left exactly as written", () => {
  const lines = ["rule {", "      color: red;", "        margin: 0;", "}"];
  expect(dedent(lines)).toEqual(lines);
});

test("a leaked block with real nesting keeps its relative indent", () => {
  const lines = ["rule {", "    color: red;", "        margin: 0;"];
  expect(dedent(lines)).toEqual(["rule {", "color: red;", "    margin: 0;"]);
});

test("bullets and headings keep their structure", () => {
  const html = renderMarkdown("## Notes\n- one\n- two\n");
  expect(html).toContain("<p data-md-heading>Notes</p>");
  expect(html).toContain("<ul data-md-list><li>one</li><li>two</li></ul>");
});

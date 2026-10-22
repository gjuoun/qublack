/**
 * A deliberately small markdown renderer for the agent specimen.
 *
 * Agent output in the wild is markdown, and the container has to prove QuBlack keeps its 2:1 grid
 * under markdown typography. So this renders exactly the subset an agent reply uses — fenced code,
 * bold, inline code, headings and bullets — and nothing else:
 *
 * - **No syntax highlighting.** A fenced block is one flat greyscale plate in QuBlack Mono; colour
 *   would compete with the typeface the page is selling.
 * - **Everything is escaped first**, so the returned string is safe for set:html / innerHTML even
 *   when the source came from an input box.
 * - **An unterminated fence still renders as code**, which is what streaming looks like mid-answer.
 */

const escapeHtml = (value: string): string =>
  value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const FENCE = /^```(\w*)\s*$/;
const HEADING = /^(#{1,4})\s+(.*)$/;
const BULLET = /^\s*[-*]\s+/;

/** Inline markdown: `code` first (its content is never bolded), then **bold**. */
export function renderInline(text: string): string {
  return text
    .split(/(`[^`]+?`)/)
    .map((part) => {
      if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) {
        return `<code data-md-inline-code>${escapeHtml(part.slice(1, -1))}</code>`;
      }
      return escapeHtml(part).replace(/\*\*([^*]+)\*\*/g, "<strong data-md-bold>$1</strong>");
    })
    .join("");
}

export function renderMarkdown(source: string): string {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";

    const fence = FENCE.exec(line);
    if (fence) {
      const language = fence[1] ?? "";
      const body: string[] = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index] ?? "")) {
        body.push(lines[index] ?? "");
        index += 1;
      }
      index += 1; // the closing fence, or one past the end while streaming
      out.push(`<pre data-md-code="${language}"><code>${escapeHtml(body.join("\n"))}</code></pre>`);
      continue;
    }

    const heading = HEADING.exec(line);
    if (heading) {
      out.push(`<p data-md-heading>${renderInline(heading[2] ?? "")}</p>`);
      index += 1;
      continue;
    }

    if (BULLET.test(line)) {
      const items: string[] = [];
      while (index < lines.length && BULLET.test(lines[index] ?? "")) {
        items.push(`<li>${renderInline((lines[index] ?? "").replace(BULLET, ""))}</li>`);
        index += 1;
      }
      out.push(`<ul data-md-list>${items.join("")}</ul>`);
      continue;
    }

    if (line.trim() === "") {
      index += 1;
      continue;
    }

    const paragraph: string[] = [];
    while (
      index < lines.length &&
      (lines[index] ?? "").trim() !== "" &&
      !FENCE.test(lines[index] ?? "") &&
      !HEADING.test(lines[index] ?? "") &&
      !BULLET.test(lines[index] ?? "")
    ) {
      paragraph.push(lines[index] ?? "");
      index += 1;
    }
    out.push(`<p data-md-p>${renderInline(paragraph.join("\n"))}</p>`);
  }

  return out.join("");
}

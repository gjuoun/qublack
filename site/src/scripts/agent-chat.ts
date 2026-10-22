/**
 * The hero's agent container: send a message, get a streamed markdown reply.
 *
 * The reply is markdown source rendered through the same renderer the page used at build time, so
 * what streams in is exactly what a finished agent turn looks like — partial fences included. All
 * rendering goes through site/src/lib/markdown.ts, which escapes the source first.
 */

import { renderMarkdown } from "../lib/markdown.ts";

interface ChatMessage {
  role: "user" | "agent";
  markdown: string;
  meta: string;
}

const form = document.getElementById("agent-form") as HTMLFormElement | null;
const input = document.getElementById("agent-input") as HTMLInputElement | null;
const thread = document.getElementById("agent-thread");
const dataNode = document.getElementById("agent-thread-data");

if (form && input && thread && dataNode) {
  const payload = JSON.parse(dataNode.textContent ?? "{}") as { replies?: string[] };
  const replies = payload.replies ?? [];
  const bodyClass =
    "text-[0.84rem] leading-[1.62] [&>*+*]:mt-[0.45rem] " +
    "[&_[data-md-p]]:m-0 " +
    "[&_[data-md-bold]]:font-bold [&_[data-md-bold]]:text-foreground " +
    "[&_[data-md-heading]]:m-0 [&_[data-md-heading]]:font-bold [&_[data-md-heading]]:text-[0.92rem] " +
    "[&_[data-md-inline-code]]:rounded-[4px] [&_[data-md-inline-code]]:bg-bf-border/25 " +
    "[&_[data-md-inline-code]]:px-[0.3em] [&_[data-md-inline-code]]:py-[0.05em] " +
    "[&_[data-md-inline-code]]:font-code [&_[data-md-inline-code]]:text-[0.9em] " +
    "[&_[data-md-list]]:my-0 [&_[data-md-list]]:ml-[1.05rem] [&_[data-md-list]]:list-disc [&_[data-md-list]]:p-0 " +
    "[&_pre[data-md-code]]:mt-0 [&_pre[data-md-code]]:mb-0 [&_pre[data-md-code]]:max-w-full " +
    "[&_pre[data-md-code]]:overflow-x-auto " +
    "[&_pre[data-md-code]]:rounded-[9px] [&_pre[data-md-code]]:border [&_pre[data-md-code]]:border-bf-border/80 " +
    "[&_pre[data-md-code]]:bg-bf-bg/70 [&_pre[data-md-code]]:px-[0.6rem] [&_pre[data-md-code]]:py-[0.5rem] " +
    "[&_pre[data-md-code]]:font-code [&_pre[data-md-code]]:text-[0.72rem] [&_pre[data-md-code]]:leading-[1.55] " +
    "[&_pre[data-md-code]]:text-bf-fg";

  let replyIndex = 0;
  let busy = false;

  const count = (): number => thread.querySelectorAll("[data-message]").length;
  const mark = (): void => {
    document.documentElement.dataset.agentMessages = String(count());
  };
  mark();

  // The specimen opens on its newest turn, not on a clip mid-message: the thread is taller than
  // its 460px viewport by design, so park it at the bottom once the fonts have settled.
  const toBottom = (): void => {
    thread.scrollTop = thread.scrollHeight;
  };
  toBottom();
  requestAnimationFrame(toBottom);
  document.fonts?.ready.then(toBottom);

  const bubble = (role: "user" | "agent"): { wrapper: HTMLElement; body: HTMLElement } => {
    const wrapper = document.createElement("div");
    wrapper.dataset.message = role;
    wrapper.className = [
      "min-w-0 max-w-[92%] rounded-[14px] border px-[0.75rem] py-[0.6rem]",
      role === "user"
        ? "ml-auto border-bf-border bg-bf-border/12"
        : "mr-auto border-bf-border bg-bf-border-muted",
    ].join(" ");
    const meta = document.createElement("p");
    meta.className =
      "m-0 mb-[0.3rem] font-code text-[0.62rem] tracking-[0.06em] text-bf-fg-muted uppercase";
    meta.textContent = role === "user" ? "you · now" : "agent · streaming";
    const body = document.createElement("div");
    body.className = bodyClass;
    body.dataset.messageBody = "";
    wrapper.append(meta, body);
    thread.append(wrapper);
    thread.scrollTop = thread.scrollHeight;
    return { wrapper, body };
  };

  const send = (text: string): void => {
    const mine = bubble("user");
    mine.body.innerHTML = renderMarkdown(text);
    mark();

    const reply = bubble("agent");
    const caret = document.createElement("span");
    caret.dataset.caret = "";
    caret.className = "ml-[0.1em] inline-block animate-blink text-bf-fg-muted";
    caret.textContent = "▍";
    reply.body.append(caret);
    document.documentElement.dataset.agentStreaming = "true";

    const answer = replies[replyIndex % replies.length] ?? "…";
    replyIndex += 1;
    let cursor = 0;
    const tick = window.setInterval(() => {
      cursor += 2;
      const partial = answer.slice(0, cursor);
      reply.body.innerHTML = renderMarkdown(partial);
      reply.body.append(caret);
      thread.scrollTop = thread.scrollHeight;
      if (cursor >= answer.length) {
        window.clearInterval(tick);
        reply.body.innerHTML = renderMarkdown(answer);
        const meta = reply.wrapper.querySelector("p");
        if (meta) meta.textContent = "agent · just now";
        document.documentElement.dataset.agentStreaming = "false";
        mark();
        busy = false;
      }
    }, 16);
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || busy) return;
    busy = true;
    input.value = "";
    send(text);
  });
}

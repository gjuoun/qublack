/**
 * The hero's agent container: send a message, get a streamed reply. The thread data is baked into
 * the page by agent-chat.astro, so nothing here touches the network.
 */

interface ChatBlock {
  kind: "text" | "code";
  body: string;
  lang?: string;
}

interface ChatMessage {
  role: "user" | "agent";
  blocks: ChatBlock[];
  meta: string;
}

const form = document.getElementById("agent-form") as HTMLFormElement | null;
const input = document.getElementById("agent-input") as HTMLInputElement | null;
const thread = document.getElementById("agent-thread");
const dataNode = document.getElementById("agent-thread-data");
if (form && input && thread && dataNode) {
  const payload = JSON.parse(dataNode.textContent ?? "{}") as {
    replies?: string[];
  };
  const replies = payload.replies ?? [];
  let replyIndex = 0;
  let busy = false;

  const count = (): number => thread.querySelectorAll("[data-message]").length;
  const mark = (): void => {
    document.documentElement.dataset.agentMessages = String(count());
  };
  mark();

  const bubble = (role: "user" | "agent"): HTMLElement => {
    const wrapper = document.createElement("div");
    wrapper.dataset.message = role;
    wrapper.className = [
      "max-w-[92%] rounded-[14px] border px-[0.75rem] py-[0.6rem]",
      role === "user"
        ? "ml-auto border-bf-blue/35 bg-bf-blue/10"
        : "mr-auto border-bf-border bg-bf-border-muted",
    ].join(" ");
    const meta = document.createElement("p");
    meta.className =
      "m-0 mb-[0.3rem] font-code text-[0.62rem] tracking-[0.06em] text-bf-dim uppercase";
    meta.textContent = role === "user" ? "you · now" : "agent · streaming";
    wrapper.append(meta);
    thread.append(wrapper);
    thread.scrollTop = thread.scrollHeight;
    return wrapper;
  };

  const send = (text: string): void => {
    const mine = bubble("user");
    const mineBody = document.createElement("p");
    mineBody.dataset.messageText = "";
    mineBody.className = "m-0 text-[0.84rem] leading-[1.62]";
    mineBody.textContent = text;
    mine.append(mineBody);
    mark();

    const reply = bubble("agent");
    const body = document.createElement("p");
    body.dataset.messageText = "";
    body.className = "m-0 text-[0.84rem] leading-[1.62]";
    body.dataset.stream = "";
    reply.append(body);
    document.documentElement.dataset.agentStreaming = "true";

    const answer = replies[replyIndex % replies.length] ?? "…";
    replyIndex += 1;
    let cursor = 0;
    const tick = window.setInterval(() => {
      cursor += 2;
      body.textContent = answer.slice(0, cursor);
      thread.scrollTop = thread.scrollHeight;
      if (cursor >= answer.length) {
        window.clearInterval(tick);
        body.textContent = answer;
        const meta = reply.querySelector("p");
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

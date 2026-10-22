import { expect, test } from "bun:test";
import { REPLIES, THREAD } from "./agent-thread.ts";

const sources = THREAD.map((message) => message.markdown).join("\n");

test("the thread mixes both languages and real code", () => {
  expect(sources).toMatch(/[\u4e00-\u9fff]/);
  expect(sources).toMatch(/[A-Za-z]{4,}/);
  expect(
    THREAD.filter((message) => message.markdown.includes("```")).length,
  ).toBeGreaterThanOrEqual(2);
});

test("agent turns are markdown: a bold verdict and a fenced block each", () => {
  const agents = THREAD.filter((message) => message.role === "agent");
  expect(agents.length).toBe(2);
  for (const message of agents) {
    expect(message.markdown).toMatch(/\*\*[^*]+\*\*/);
    expect(message.markdown).toMatch(/```\w*\n[\s\S]+```/);
  }
});

test("user and agent both speak, and the first word is the visitor's", () => {
  expect(THREAD[0]?.role).toBe("user");
  expect(new Set(THREAD.map((message) => message.role))).toEqual(new Set(["user", "agent"]));
});

test("every message carries meta and markdown", () => {
  for (const message of THREAD) {
    expect(message.meta.length).toBeGreaterThan(0);
    expect(message.markdown.length).toBeGreaterThan(10);
  }
});

test("the canned replies are markdown too, and rotate", () => {
  expect(REPLIES.length).toBeGreaterThanOrEqual(2);
  expect(REPLIES.filter((reply) => reply.includes("**")).length).toBeGreaterThanOrEqual(2);
  expect(REPLIES.some((reply) => reply.includes("```"))).toBe(true);
});

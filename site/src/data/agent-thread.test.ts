import { expect, test } from "bun:test";
import { REPLIES, THREAD } from "./agent-thread.ts";

test("the specimen thread mixes both languages and real code", () => {
  const text = THREAD.flatMap((message) => message.blocks.map((block) => block.body)).join("\n");
  expect(text).toMatch(/[\u4e00-\u9fff]/);
  expect(text).toMatch(/[A-Za-z]{4,}/);
  expect(THREAD.filter((message) => message.blocks.some((block) => block.kind === "code")).length).toBeGreaterThanOrEqual(2);
});

test("user and agent both speak, and the first word is the visitor's", () => {
  expect(THREAD[0]?.role).toBe("user");
  expect(new Set(THREAD.map((message) => message.role))).toEqual(new Set(["user", "agent"]));
});

test("every message carries meta and at least one block", () => {
  for (const message of THREAD) {
    expect(message.meta.length).toBeGreaterThan(0);
    expect(message.blocks.length).toBeGreaterThan(0);
  }
});

test("there is a canned reply to stream", () => {
  expect(REPLIES.length).toBeGreaterThanOrEqual(2);
  expect(REPLIES.every((reply) => reply.length > 20)).toBe(true);
});

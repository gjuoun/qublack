import { expect, test } from "bun:test";
import { HOW_TO_TABS } from "./how-to.ts";
import { DOWNLOAD_URL, ZIP_NAME } from "./site.ts";

const cards = HOW_TO_TABS.flatMap((tab) => tab.cards);
const withCode = cards.filter((card) => card.code !== undefined);
const code = withCode.map((card) => card.code ?? "");

test("four routes in: OS, web, terminals, frameworks", () => {
  expect(HOW_TO_TABS.map((tab) => tab.id)).toEqual(["os", "web", "terminals", "frameworks"]);
  for (const tab of HOW_TO_TABS) {
    expect(tab.label.length).toBeGreaterThan(1);
    expect(tab.blurb.length).toBeGreaterThan(40);
    expect(tab.cards.length).toBeGreaterThanOrEqual(2);
  }
});

test("every card is either copyable or a GUI recipe, never both empty", () => {
  for (const card of cards) {
    const hasCode = (card.code ?? "").trim().length > 0;
    const hasSteps = (card.steps ?? []).length > 0;
    expect(hasCode || hasSteps).toBe(true);
    expect(hasCode && hasSteps).toBe(false);
    expect(card.title.length).toBeGreaterThan(1);
  }
  expect(new Set(cards.map((card) => card.id)).size).toBe(cards.length);
});

test("install commands use the current release asset, not a hardcoded tag", () => {
  const install = HOW_TO_TABS.find((tab) => tab.id === "os")?.cards ?? [];
  expect(install.length).toBe(3);
  for (const card of install) {
    expect(card.code).toContain(DOWNLOAD_URL);
    expect(card.code).toContain(ZIP_NAME);
  }
  // The URL is assembled from VERSION/ZIP_NAME at import time, so a version bump moves it here.
  for (const card of install) expect(card.code).not.toContain("releases/tag/");
});

test("snippets name the published families exactly", () => {
  const families = new Set(code.flatMap((snippet) => snippet.match(/QuBlack (Mono|Sans)/g) ?? []));
  expect([...families].sort()).toEqual(["QuBlack Mono", "QuBlack Sans"]);
  for (const snippet of code) {
    expect(snippet.startsWith("\n")).toBe(false);
    expect(snippet.endsWith("\n")).toBe(false);
  }
});

test("Ghostty is the first terminal, and the terminal notes keep the 1.2x cell honest", () => {
  const terminals = HOW_TO_TABS.find((tab) => tab.id === "terminals");
  expect(terminals?.cards[0]?.id).toBe("ghostty");
  expect(terminals?.blurb).toContain("1.200em");
  expect(terminals?.blurb).toContain("1.2x");
  const kitty = terminals?.cards.find((card) => card.id === "kitty");
  expect(kitty?.code).toContain("bold_italic_font QuBlack Mono Bold Italic");
});

test("both families are taught, not just the mono one", () => {
  const sans = (code.join("\n").match(/QuBlack Sans/g) ?? []).length;
  const mono = (code.join("\n").match(/QuBlack Mono/g) ?? []).length;
  expect(sans).toBeGreaterThanOrEqual(6);
  expect(mono).toBeGreaterThan(sans);

  const web = new Map(
    (HOW_TO_TABS.find((tab) => tab.id === "web")?.cards ?? []).map((card) => [
      card.id,
      card.code ?? "",
    ]),
  );
  const faces = web.get("faces") ?? "";
  expect(faces).toContain('font-family: "QuBlack Mono"');
  expect(faces).toContain('font-family: "QuBlack Sans"');
  expect(faces).toContain("body {");
  expect(faces).toContain('"QuBlack Sans", -apple-system');
  expect(faces).toContain('"QuBlack Mono", ui-monospace');
  const stack = web.get("stack") ?? "";
  expect(stack).toContain("--font-mono:");
  expect(stack).toContain("--font-sans:");

  const terminals = HOW_TO_TABS.find((tab) => tab.id === "terminals");
  expect(terminals?.blurb).toContain("not a terminal face");
});

test("framework snippets wire Sans for body and Mono for code", () => {
  const frameworks = new Map(
    (HOW_TO_TABS.find((tab) => tab.id === "frameworks")?.cards ?? []).map((card) => [
      card.id,
      card.code ?? "",
    ]),
  );
  for (const id of ["next", "astro"]) {
    expect(frameworks.get(id)).toContain("--font-qublack-sans");
    expect(frameworks.get(id)).toContain("--font-qublack-mono");
    expect(frameworks.get(id)).toContain("QuBlack Sans");
  }
  const vite = frameworks.get("vite") ?? "";
  expect(vite).toContain("--font-sans:");
  expect(vite).toContain("--font-mono:");
  expect(vite).toContain("QuBlack Sans");
  const tailwind = frameworks.get("tailwind") ?? "";
  expect(tailwind).toContain("--font-sans:");
  expect(tailwind).toContain("--font-mono:");
});

test("framework snippets cover the five environments the card asks for", () => {
  const frameworks = HOW_TO_TABS.find((tab) => tab.id === "frameworks")?.cards ?? [];
  expect(frameworks.map((card) => card.id)).toEqual([
    "next",
    "astro",
    "vite",
    "tailwind",
    "vscode",
  ]);
  const byId = new Map(frameworks.map((card) => [card.id, card.code ?? ""]));
  expect(byId.get("next")).toContain("next/font/local");
  expect(byId.get("astro")).toContain("fontProviders.local()");
  expect(byId.get("tailwind")).toContain("--font-mono:");
  expect(byId.get("vscode")).toContain('"editor.fontFamily"');
});

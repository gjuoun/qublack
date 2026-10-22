import { expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const BG_DIR = join(import.meta.dir, "components/bg");

test("every React component in components/bg exports a BG-prefixed symbol", () => {
  for (const file of readdirSync(BG_DIR).filter((name) => name.endsWith(".tsx"))) {
    const source = readFileSync(join(BG_DIR, file), "utf8");
    expect(source).toMatch(/export function BG[A-Z]/);
  }
});

test("bg component file names are kebab-case", () => {
  for (const file of readdirSync(BG_DIR)) {
    expect(file).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*\.(astro|tsx)$/);
  }
});

import { expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

// Every colour on the site comes from palette/qublack.json through the --bf-* variables that
// Base.astro writes onto <html>. A hex literal in a component means someone bypassed the palette.
const BG_DIR = join(import.meta.dir, "components/bg");
const HEX = /#[0-9a-fA-F]{3,8}\b/;

test("no bg component paints with a hex literal", () => {
  for (const file of readdirSync(BG_DIR)) {
    const source = readFileSync(join(BG_DIR, file), "utf8");
    const lines = source.split("\n").filter((line) => HEX.test(line) && !line.includes("mask"));
    expect({ file, lines }).toEqual({ file, lines: [] });
  }
});

test("no bg component calls rgb() or hsl() directly", () => {
  for (const file of readdirSync(BG_DIR)) {
    const source = readFileSync(join(BG_DIR, file), "utf8");
    expect(source).not.toMatch(/\b(rgba?|hsla?)\(/);
  }
});

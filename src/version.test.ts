import { expect, test } from "bun:test";
import { RELEASE_TAG, VERSION } from "./version.ts";

test("the release tag follows the version", () => {
  expect(RELEASE_TAG).toBe(`v${VERSION}`);
});

test("the version matches package.json", async () => {
  const pkg = (await Bun.file(new URL("../package.json", import.meta.url)).json()) as {
    version: string;
  };
  expect(pkg.version).toBe(VERSION);
});

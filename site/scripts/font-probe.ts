/**
 * Load every built TTF into Chrome through the FontFace API and prove it renders.
 *
 * This is the OTS gate: Chrome parses TrueType with OTS, so a face that carries an illegal glyph
 * flag (the v1.0.3 OVERLAP_SIMPLE failure) or a broken table rejects at `face.load()`. A face that
 * loads but silently falls back to the system font would pass a name-only test, so the probe also
 * draws `汉一|a` on a canvas and requires the ink box to differ from the generic fallback.
 *
 * `--self-test` rebuilds the same faces with OVERLAP_SIMPLE set on every point — exactly what the
 * build now clears — and asserts that the probe rejects all of them. That is the guard's self-harm
 * check: it proves the assertion can go red.
 *
 * usage: bun run site/scripts/font-probe.ts <fonts-dir> [--self-test]
 */
import { mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";
import puppeteer from "puppeteer-core";

const args = process.argv.slice(2);
const selfTest = args.includes("--self-test");
const variation = args.includes("--vf");
const fontsDir = resolve(args.find((arg) => !arg.startsWith("--")) ?? "fonts");
const chromePath =
  process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

type FaceResult = {
  name: string;
  loaded: boolean;
  error: string;
  custom: Signature;
  fallback: Signature;
};
type Signature = { width: number; height: number; ink: number };

function facesIn(dir: string): string[] {
  return readdirSync(dir)
    .filter((name) => name.endsWith(".ttf"))
    .sort();
}

/** Set OVERLAP_SIMPLE (flag bit 6) on every point, which Chrome's OTS rejects on all but the first. */
function corrupt(source: string, target: string): void {
  const script = [
    "import sys",
    "from fontTools.ttLib import TTFont",
    "font = TTFont(sys.argv[1])",
    "for name in font.getGlyphOrder():",
    '    glyph = font["glyf"][name]',
    '    flags = getattr(glyph, "flags", None)',
    '    if flags is None or getattr(glyph, "numberOfContours", 0) <= 0:',
    "        continue",
    "    for index in range(len(flags)):",
    "        flags[index] = int(flags[index]) | 0x40",
    "font.save(sys.argv[2])",
  ].join("\n");
  const run = Bun.spawnSync(["python3", "-c", script, source, target]);
  if (run.exitCode !== 0) {
    throw new Error(`could not corrupt ${basename(source)}: ${run.stderr.toString()}`);
  }
}

function serve(root: string) {
  return Bun.serve({
    port: 0,
    fetch(request) {
      const name = decodeURIComponent(new URL(request.url).pathname.slice(1));
      if (name === "favicon.ico") {
        return new Response(null, { status: 204 });
      }
      if (name === "" || name === "index.html") {
        return new Response("<!doctype html><title>font probe</title>", {
          headers: { "content-type": "text/html" },
        });
      }
      const path = join(root, name);
      if (!path.startsWith(root)) {
        return new Response("forbidden", { status: 403 });
      }
      return new Response(Bun.file(path), { headers: { "access-control-allow-origin": "*" } });
    },
  });
}

async function probe(url: string, names: string[]): Promise<FaceResult[]> {
  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none"],
  });
  try {
    const page = await browser.newPage();
    await page.goto(url);
    return await page.evaluate(
      async (targets: { name: string; url: string }[]) => {
        const measure = (family: string): Signature => {
          const canvas = document.createElement("canvas");
          canvas.width = 900;
          canvas.height = 220;
          const context = canvas.getContext("2d")!;
          context.fillStyle = "#fff";
          context.fillRect(0, 0, canvas.width, canvas.height);
          context.fillStyle = "#000";
          context.font = `96px "${family}"`;
          context.fillText("汉一|a", 20, 140);
          const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
          let minX = canvas.width,
            minY = canvas.height,
            maxX = 0,
            maxY = 0,
            ink = 0;
          for (let y = 0; y < canvas.height; y += 1) {
            for (let x = 0; x < canvas.width; x += 1) {
              if (data[(y * canvas.width + x) * 4] < 128) {
                ink += 1;
                minX = Math.min(minX, x);
                minY = Math.min(minY, y);
                maxX = Math.max(maxX, x);
                maxY = Math.max(maxY, y);
              }
            }
          }
          return { width: maxX - minX, height: maxY - minY, ink };
        };

        const fallback = measure("sans-serif");
        const results = [];
        for (const target of targets) {
          const result = {
            name: target.name,
            loaded: false,
            error: "",
            custom: { width: 0, height: 0, ink: 0 },
            fallback,
          };
          try {
            const buffer = await (await fetch(target.url)).arrayBuffer();
            const face = new FontFace(`probe-${target.name}-${Date.now()}`, buffer);
            await face.load();
            document.fonts.add(face);
            result.custom = measure(face.family);
            result.loaded = true;
          } catch (error) {
            result.error = String(error);
          }
          results.push(result);
        }
        return results;
      },
      names.map((name) => ({
        name,
        url: `${url}/${name}`,
      })),
    );
  } finally {
    await browser.close();
  }
}

type VariationResult = { name: string; loaded: boolean; error: string; inks: number[] };

const WEIGHTS = [400, 550, 700];

/** Render one face at three axis values through FontFace variation settings, count ink pixels. */
async function probeVariations(url: string, names: string[]): Promise<VariationResult[]> {
  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none"],
  });
  try {
    const page = await browser.newPage();
    await page.goto(url);
    return await page.evaluate(
      async (targets: { name: string; url: string }[], weights: number[]) => {
        const ink = (family: string): number => {
          const canvas = document.createElement("canvas");
          canvas.width = 900;
          canvas.height = 220;
          const context = canvas.getContext("2d")!;
          context.fillStyle = "#fff";
          context.fillRect(0, 0, canvas.width, canvas.height);
          context.fillStyle = "#000";
          context.font = `96px "${family}"`;
          context.fillText("汉一|a", 20, 140);
          const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
          let count = 0;
          for (let i = 0; i < data.length; i += 4) {
            if (data[i] < 128) count += 1;
          }
          return count;
        };
        const results = [];
        for (const target of targets) {
          const result = { name: target.name, loaded: false, error: "", inks: [] as number[] };
          try {
            const buffer = await (await fetch(target.url)).arrayBuffer();
            for (const weight of weights) {
              const face = new FontFace(`var-${target.name}-${weight}`, buffer.slice(0), {
                variationSettings: `"wght" ${weight}`,
              } as FontFaceDescriptors);
              await face.load();
              document.fonts.add(face);
              result.inks.push(ink(face.family));
            }
            result.loaded = true;
          } catch (error) {
            result.error = String(error);
          }
          results.push(result);
        }
        return results;
      },
      names.map((name) => ({ name, url: `${url}/${name}` })),
      WEIGHTS,
    );
  } finally {
    await browser.close();
  }
}

function monotone(result: VariationResult): boolean {
  if (!result.loaded || result.inks.length !== WEIGHTS.length) return false;
  const [light, middle, heavy] = result.inks;
  return light > 0 && light < middle && middle < heavy;
}

function distinct(result: FaceResult): boolean {
  const { custom, fallback } = result;
  if (custom.ink === 0) return false;
  return (
    Math.abs(custom.width - fallback.width) > 2 ||
    Math.abs(custom.height - fallback.height) > 2 ||
    Math.abs(custom.ink - fallback.ink) / Math.max(custom.ink, fallback.ink) > 0.02
  );
}

/** Drop fvar from a copy: the axis is declared nowhere, so all three weights must render alike. */
function stripAxis(source: string, target: string): void {
  const script = [
    "import sys",
    "from fontTools.ttLib import TTFont",
    "font = TTFont(sys.argv[1])",
    'if "fvar" in font:',
    '    del font["fvar"]',
    'if "STAT" in font:',
    '    del font["STAT"]',
    "font.save(sys.argv[2])",
  ].join("\n");
  const run = Bun.spawnSync(["python3", "-c", script, source, target]);
  if (run.exitCode !== 0) {
    throw new Error(`could not strip the axis from ${basename(source)}: ${run.stderr.toString()}`);
  }
}

async function mainVariations(): Promise<number> {
  const names = facesIn(fontsDir).filter((name) => name.includes("[wght]"));
  if (names.length === 0) {
    console.error(`no variable faces in ${fontsDir}`);
    return 2;
  }

  const server = serve(fontsDir);
  try {
    const results = await probeVariations(`http://127.0.0.1:${server.port}`, names);
    for (const result of results) {
      const detail = result.loaded
        ? `ink ${result.inks.join(" < ")} at wght ${WEIGHTS.join("/")}`
        : result.error.slice(0, 120);
      console.log(`${monotone(result) ? "PASS" : "FAIL"}  ${result.name}: ${detail}`);
    }
    const good = results.filter(monotone);
    console.log(
      `${good.length === results.length ? "PASS" : "FAIL"} ${good.length}/${results.length} VF faces: wght 400/550/700 distinct, stem width monotone`,
    );
    return good.length === results.length ? 0 : 1;
  } finally {
    server.stop(true);
  }
}

async function runVariationSelfTest(): Promise<number> {
  const dir = mkdtempSync(join(tmpdir(), "qublack-vf-probe-"));
  const names = facesIn(fontsDir).filter((name) => name.includes("[wght]"));
  console.log(`[self-test] stripping the axis from ${names.length} faces into ${dir}`);
  for (const name of names) {
    stripAxis(join(fontsDir, name), join(dir, name));
  }
  const server = serve(dir);
  try {
    const results = await probeVariations(`http://127.0.0.1:${server.port}`, facesIn(dir));
    const rejected = results.filter((result) => !monotone(result));
    for (const result of results) {
      console.log(
        `${monotone(result) ? "FAIL" : "PASS"}  ${result.name}: ${
          monotone(result) ? "axis-less face still varied" : `flat at ${result.inks.join("/")}`
        }`,
      );
    }
    const ok = rejected.length === results.length;
    console.log(
      `${ok ? "PASS" : "FAIL"} negative control rejected (${rejected.length}/${results.length} axis-less copies fail)`,
    );
    return ok ? 0 : 1;
  } finally {
    server.stop(true);
  }
}

async function main(): Promise<number> {
  const names = facesIn(fontsDir);
  if (names.length === 0) {
    console.error(`no faces in ${fontsDir}`);
    return 2;
  }

  const server = serve(fontsDir);
  try {
    const results = await probe(`http://127.0.0.1:${server.port}`, names);
    const good = results.filter((result) => result.loaded && distinct(result));
    for (const result of results) {
      const state = result.loaded ? (distinct(result) ? "PASS" : "FAIL (fallback drawn)") : "FAIL";
      const detail = result.loaded
        ? `ink ${result.custom.ink} vs fallback ${result.fallback.ink}`
        : result.error.slice(0, 120);
      console.log(`${state}  ${result.name}: ${detail}`);
    }
    const ok = good.length === results.length;
    console.log(
      `${ok ? "PASS" : "FAIL"} ${good.length}/${results.length} faces load and render in Chrome`,
    );
    return ok ? 0 : 1;
  } finally {
    server.stop(true);
  }
}

async function runSelfTest(): Promise<number> {
  const dir = mkdtempSync(join(tmpdir(), "qublack-probe-"));
  const names = facesIn(fontsDir);
  console.log(`[self-test] corrupting ${names.length} faces into ${dir}`);
  for (const name of names) {
    corrupt(join(fontsDir, name), join(dir, name));
    console.log(`[self-test] corrupted ${name}`);
  }
  const server = serve(dir);
  try {
    const results = await probe(`http://127.0.0.1:${server.port}`, facesIn(dir));
    const rejected = results.filter((result) => !result.loaded);
    for (const result of results) {
      console.log(
        `${result.loaded ? "FAIL" : "PASS"}  ${result.name}: ${
          result.loaded ? "corrupted face was accepted" : result.error.slice(0, 90)
        }`,
      );
    }
    const ok = rejected.length === results.length;
    console.log(
      `${ok ? "PASS" : "FAIL"} negative control rejected (${rejected.length}/${results.length} corrupted faces fail)`,
    );
    return ok ? 0 : 1;
  } finally {
    server.stop(true);
  }
}

process.exit(
  variation
    ? selfTest
      ? await runVariationSelfTest()
      : await mainVariations()
    : selfTest
      ? await runSelfTest()
      : await main(),
);

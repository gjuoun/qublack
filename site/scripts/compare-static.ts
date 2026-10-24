/** Three-way side-by-side shot of the Latin ink: shipped VF, static face, rebuilt VF.
 *
 * The faces are loaded from the files themselves over file:// (no Font Book install), so the
 * screenshot proves the artifacts that were just built. Same sample text and sizes in every
 * column; the whole page is rendered at deviceScaleFactor 2 so 12 px text is rasterised at 24 ppem,
 * the size the ink gate measures.
 *
 * usage: bun run site/scripts/compare-static.ts --before <vf.ttf> --static <face.ttf> --after <vf.ttf> --out <png>
 */
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const args = process.argv.slice(2);
function flag(name: string): string | undefined {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
}

const before = flag("--before");
const staticFace = flag("--static");
const after = flag("--after");
const out = flag("--out");
if (!before || !staticFace || !after || !out) {
  console.error(
    "usage: compare-static.ts --before <vf.ttf> --static <face.ttf> --after <vf.ttf> --out <png>",
  );
  process.exit(2);
}

const sample = [
  "// 构建日志：@Qu Black 2:1 网格，l i I | 1 与 {}[]() 对齐检查",
  "const total = items.filter(x => x.qty > 0).length; // {a:1,b:2} → sum",
  'if (err?.code === "E_NO_ENTRY" && retry < 3) return null; // !?;:.',
  "async function 渲染(节点: Node[]) { await 等待(200); } // 汉字 + English",
  "$ npm run build --filter=site && bun test src/site  ✓ 12 passed",
  "Δx=0.25; δ≈1e-9; ① ② ③ §¶°± ←↑→↓ 漢字混排对齐测试",
].join("\n");

const work = mkdtempSync(join(tmpdir(), "qublack-compare-"));
const faces = [
  { key: "before", label: "VF v1.2.0 (shipped)", file: before, path: join(work, "before.ttf") },
  { key: "static", label: "Static (reference)", file: staticFace, path: join(work, "static.ttf") },
  { key: "after", label: "VF (rebuilt)", file: after, path: join(work, "after.ttf") },
];
for (const face of faces) copyFileSync(resolve(face.file), face.path);

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  @font-face { font-family: QF-before; src: url(before.ttf) format("truetype"); }
  @font-face { font-family: QF-static; src: url(static.ttf) format("truetype"); }
  @font-face { font-family: QF-after;  src: url(after.ttf)  format("truetype"); }
  body { background:#1e1e2e; color:#d9d9d4; margin:0; padding:24px; font-synthesis:none;
         display:grid; grid-template-columns:repeat(3, 1fr); gap:18px; width:2400px; }
  .col { min-width:0; overflow:hidden; }
  .label { font:600 13px -apple-system, sans-serif; color:#8be9fd; letter-spacing:.5px; margin:0 0 6px; }
  .label b { color:#ff79c6; }
  .sub { font:500 11px -apple-system, sans-serif; color:#6272a4; margin:12px 0 4px; }
  pre { margin:0; padding:12px 14px; background:#282a36; border-radius:8px; white-space:pre;
        line-height:1.5; font-size:12px; }
  pre.big { font-size:16px; }
  .before pre { font-family: QF-before, ui-monospace, monospace; }
  .static pre { font-family: QF-static, ui-monospace, monospace; }
  .after  pre { font-family: QF-after,  ui-monospace, monospace; }
</style></head><body>
  ${faces
    .map(
      (face) => `
    <div class="col ${face.key}">
      <div class="label"><b>${face.label}</b> — 12px</div>
      <pre>${sample}</pre>
      <div class="sub">16px</div>
      <pre class="big">${sample}</pre>
    </div>`,
    )
    .join("")}
</body></html>`;

writeFileSync(join(work, "index.html"), html);

const chromePath =
  process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: true,
  args: [
    "--allow-file-access-from-files",
    "--font-render-hinting=none",
    "--disable-lcd-text",
    "--hide-scrollbars",
  ],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 2450, height: 900, deviceScaleFactor: 2 });
  await page.goto(pathToFileURL(join(work, "index.html")).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  const checks = await page.evaluate(() => ({
    before: document.fonts.check('12px "QF-before"'),
    static: document.fonts.check('12px "QF-static"'),
    after: document.fonts.check('12px "QF-after"'),
  }));
  console.log("fonts.check:", JSON.stringify(checks));
  if (!checks.before || !checks.static || !checks.after) {
    console.error("FONT NOT RESOLVED — screenshot would be fallback");
    process.exit(1);
  }
  await new Promise((done) => setTimeout(done, 300));
  const target = resolve(out);
  mkdirSync(dirname(target), { recursive: true });
  await page.screenshot({ path: target as `${string}.png`, fullPage: true });
  console.log(`saved ${target}`);
} finally {
  await browser.close();
  rmSync(work, { recursive: true, force: true });
}

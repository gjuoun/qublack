/**
 * Drive a built / preview / production page with the locally installed Chrome and assert the
 * behavior the plan promises. No browser download: puppeteer-core + the system Chrome.
 *
 * usage: bun run site/scripts/smoke.ts <url>
 */

import puppeteer from "puppeteer-core";

const url = process.argv[2] ?? "http://localhost:4321";
const chromePath =
  process.env.CHROME_PATH ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

let failures = 0;
const pass = (message: string) => console.log(`PASS  ${message}`);
const fail = (message: string) => {
  failures += 1;
  console.log(`FAIL  ${message}`);
};

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });

await page.evaluateOnNewDocument(() => {
  (window as unknown as { __cls: number }).__cls = 0;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries() as unknown as {
      value: number;
      hadRecentInput: boolean;
    }[]) {
      if (!entry.hadRecentInput) {
        (window as unknown as { __cls: number }).__cls += entry.value;
      }
    }
  }).observe({ type: "layout-shift", buffered: true });
});

await page.goto(url, { waitUntil: "load", timeout: 60_000 });
await page.waitForSelector("#hero-specimen");
await page.evaluate(() => document.fonts.ready.then(() => undefined));

// Baseline the first-paint font payload before any interaction: the chat input below is typed
// into, and those characters legitimately pull extra shards that are not part of a cold load.
const initialFonts = await page.evaluate(() => {
  const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
  const woff2 = resources.filter((entry) => entry.name.endsWith(".woff2"));
  return {
    bytes: woff2.reduce((sum, entry) => sum + (entry.transferSize || entry.encodedBodySize), 0),
    shards: woff2.length,
  };
});

// 1. The hero is genuinely editable: type, commit with Enter, text survives.
await page.click("#hero-specimen");
await page.evaluate(() => {
  const hero = document.getElementById("hero-specimen");
  if (!hero) return;
  const range = document.createRange();
  range.selectNodeContents(hero);
  const selection = window.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
});
await page.keyboard.type("黢黑 TEST");
await page.keyboard.press("Enter");
const heroText = await page.evaluate(
  () => document.getElementById("hero-specimen")?.textContent ?? "",
);
heroText.includes("黢黑 TEST")
  ? pass("hero edit: typed text committed with Enter")
  : fail(`hero edit: text is ${JSON.stringify(heroText)}`);

// 2. Keyboard: B sets bold, M sets mono.
await page.keyboard.press("b");
const bold = await page.evaluate(() => ({
  weight: document.documentElement.dataset.specimenWeight,
  computed: getComputedStyle(document.querySelector("[data-specimen]") as Element).fontWeight,
}));
bold.weight === "bold" && bold.computed === "700"
  ? pass("key B: specimen is bold (computed 700)")
  : fail(`key B: dataset ${bold.weight}, computed ${bold.computed}`);

await page.keyboard.press("m");
const mono = await page.evaluate(() => ({
  family: document.documentElement.dataset.specimenFamily,
  computed: getComputedStyle(document.querySelector("[data-specimen]") as Element).fontFamily,
}));
mono.family === "mono" && mono.computed.includes("QuBlack Mono")
  ? pass("key M: specimen switched to QuBlack Mono")
  : fail(`key M: dataset ${mono.family}, computed ${mono.computed}`);

// 3. Arrow navigation moves the page to the next section.
const before = await page.evaluate(() => window.scrollY);
await page.keyboard.press("ArrowDown");
await new Promise((resolve) => setTimeout(resolve, 900));
const after = await page.evaluate(() => ({
  y: window.scrollY,
  section: document.documentElement.dataset.specimenSection,
}));
after.y > before && after.section === "ascii"
  ? pass(`ArrowDown: section ${after.section}, scrollY ${before} -> ${after.y}`)
  : fail(`ArrowDown: section ${after.section}, scrollY ${before} -> ${after.y}`);

// 4. Content: ASCII cells, lookalike rows, the measured ratio, the release link.
const counts = await page.evaluate(() => ({
  ascii: document.querySelectorAll("[data-ascii-char]").length,
  lookalikes: document.querySelectorAll("[data-lookalike]").length,
  ratio: document.getElementById("ratio-value")?.textContent?.trim() ?? "",
  download: [...document.querySelectorAll("a[href*='releases']")].map((a) =>
    a.getAttribute("href"),
  ),
}));
counts.ascii === 95 ? pass("ASCII table: 95 cells") : fail(`ASCII table: ${counts.ascii} cells`);
counts.lookalikes >= 12
  ? pass(`lookalikes: ${counts.lookalikes} rows`)
  : fail(`lookalikes: ${counts.lookalikes} rows`);
counts.ratio === "2.000"
  ? pass("2:1 grid: ratio cell reads 2.000")
  : fail(`2:1 grid: ratio cell reads ${JSON.stringify(counts.ratio)}`);
counts.download.some((href) => href?.includes("/releases/tag/v1.0.0"))
  ? pass("download: links the v1.0.0 release")
  : fail(`download: release links are ${JSON.stringify(counts.download)}`);

// 5. The hero's agent container: a real thread, code in the mono face, a streamed reply.
const chat = await page.evaluate(() => {
  const thread = document.getElementById("agent-thread");
  const code = thread?.querySelector<HTMLElement>("[data-message-code]");
  return {
    messages: thread?.querySelectorAll("[data-message]").length ?? 0,
    codeBlocks: thread?.querySelectorAll("[data-message-code]").length ?? 0,
    codeFont: code ? getComputedStyle(code).fontFamily : "",
    title: document.title,
  };
});
chat.messages >= 4
  ? pass(`agent chat: ${chat.messages} messages in the initial thread`)
  : fail(`agent chat: ${chat.messages} messages`);
chat.codeBlocks >= 2 && chat.codeFont.includes("QuBlack Mono")
  ? pass(`agent chat: ${chat.codeBlocks} code blocks render in QuBlack Mono`)
  : fail(`agent chat: ${chat.codeBlocks} code blocks, font ${chat.codeFont}`);
chat.title.includes("for your agent")
  ? pass('positioning: the title says "a modern font for your agent"')
  : fail(`positioning: title is ${JSON.stringify(chat.title)}`);

const beforeSend = chat.messages;
await page.click("#agent-input");
await page.type("#agent-input", "把 2:1 对齐再跑一遍");
await page.keyboard.press("Enter");
await page
  .waitForFunction(
    (target) => Number(document.documentElement.dataset.agentMessages ?? 0) >= target,
    { timeout: 8_000 },
    beforeSend + 2,
  )
  .then(() =>
    pass(`agent chat: message sent, streamed reply appended (${beforeSend} -> ${beforeSend + 2})`),
  )
  .catch(() => fail(`agent chat: no reply after sending (still ${beforeSend})`));

// 6. Fonts: both families resolve, the initial payload stays small, nothing shifts.
const fonts = await page.evaluate(() => {
  const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
  const woff2 = resources.filter((entry) => entry.name.endsWith(".woff2"));
  return {
    mono: document.fonts.check('400 16px "QuBlack Mono"'),
    sans: document.fonts.check('400 16px "QuBlack Sans"'),
    bytes: woff2.reduce((sum, entry) => sum + (entry.transferSize || entry.encodedBodySize), 0),
    shards: woff2.length,
    cls: (window as unknown as { __cls: number }).__cls,
  };
});
fonts.mono && fonts.sans
  ? pass("fonts: QuBlack Mono and QuBlack Sans both resolve")
  : fail(`fonts: mono=${fonts.mono} sans=${fonts.sans}`);
initialFonts.bytes < 400_000
  ? pass(
      `font payload: ${(initialFonts.bytes / 1024).toFixed(0)} KB over ${initialFonts.shards} shards on load (< 400 KB)`,
    )
  : fail(
      `font payload: ${(initialFonts.bytes / 1024).toFixed(0)} KB over ${initialFonts.shards} shards on load`,
    );
fonts.cls < 0.1
  ? pass(`CLS: ${fonts.cls.toFixed(3)} (< 0.1)`)
  : fail(`CLS: ${fonts.cls.toFixed(3)}`);

await browser.close();
process.exit(failures ? 1 : 0);

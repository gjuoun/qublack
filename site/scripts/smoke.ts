/**
 * Drive a built / preview / production page with the locally installed Chrome and assert the
 * behavior the plan promises. No browser download: puppeteer-core + the system Chrome.
 *
 * usage: bun run site/scripts/smoke.ts <url>
 */

import puppeteer from "puppeteer-core";
import { VERSION } from "../src/data/site";

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
// The How-to tabs are a React island: Astro drops the ssr attribute once it hydrates. Wait for it,
// otherwise the first click lands on inert markup and silently does nothing.
await page.waitForFunction(
  () => {
    const island = document.querySelector("[data-howto-tabs]")?.closest("astro-island");
    return island !== null && !island.hasAttribute("ssr");
  },
  { timeout: 20_000 },
);

// The chat specimen must open on its newest turn, not mid-message. A thread whose messages fit
// the box is already at its newest turn (they ride the input row since delta 9e), so only a
// scrollable thread has to prove it is parked at the end.
const mountScroll = await page.evaluate(() => {
  const thread = document.getElementById("agent-thread") as HTMLElement | null;
  if (!thread) return null;
  return {
    gap: Math.max(0, Math.round(thread.scrollHeight - thread.scrollTop - thread.clientHeight)),
    scrolled: thread.scrollTop > 0,
    fits: thread.scrollHeight <= thread.clientHeight + 2,
  };
});
mountScroll && (mountScroll.scrolled || mountScroll.fits) && mountScroll.gap <= 2
  ? pass(
      `agent chat: opens on its newest message (${mountScroll.scrolled ? "scrolled to the end" : "messages fit the box"}, tail gap ${mountScroll.gap}px)`,
    )
  : fail(`agent chat: mount scroll ${JSON.stringify(mountScroll)}`);

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
mono.family === "mono" && mono.computed.includes("Qu Black Mono")
  ? pass("key M: specimen switched to Qu Black Mono")
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
const heroCopy = await page.evaluate(() => ({
  lead: document.querySelector("#specimen p.bf-lead")?.textContent ?? "",
  ctaHeights: [
    ...(document.querySelector("#specimen a[href='#download']")?.parentElement?.children ?? []),
  ].map((child) => Math.round(child.getBoundingClientRect().height * 10) / 10),
}));
heroCopy.lead.includes("measured 2:1")
  ? pass('copy: the hero reads "measured 2:1" with its space')
  : fail(`copy: hero lead is ${JSON.stringify(heroCopy.lead.slice(0, 120))}`);
Math.max(...heroCopy.ctaHeights) - Math.min(...heroCopy.ctaHeights) <= 2
  ? pass(`copy: the CTA row shares one height (${heroCopy.ctaHeights.join("/")}px)`)
  : fail(`copy: CTA heights ${JSON.stringify(heroCopy.ctaHeights)}`);

counts.download.some((href) => href?.includes(`/releases/tag/v${VERSION}`))
  ? pass(`download: links the v${VERSION} release`)
  : fail(`download: release links are ${JSON.stringify(counts.download)}`);

// The hero's copy-CSS pill is gone: the How-to section below the fold owns the instructions.
const heroCopyButtons = await page.evaluate(
  () => document.querySelectorAll("#specimen [data-copy]").length,
);
heroCopyButtons === 0
  ? pass("copy: the hero no longer carries a copy CSS button")
  : fail(`copy: the hero still has ${heroCopyButtons} copy buttons`);

// The How-to block: four tabs, every plate carrying a copy button whose payload is the plate.
const howto = await page.evaluate(() => {
  const panelOf = (card: Element | null) =>
    card?.closest<HTMLElement>("[data-howto-panel]")?.dataset.howtoPanel ?? "";
  const cards = [...document.querySelectorAll("[data-howto-card]")];
  const plates = [...document.querySelectorAll<HTMLElement>("[data-howto-code]")];
  return {
    tabs: [...document.querySelectorAll<HTMLElement>("[data-howto-tab]")].map(
      (tab) => tab.dataset.howtoTab ?? "",
    ),
    panels: [...document.querySelectorAll<HTMLElement>("[data-howto-panel]")].map(
      (panel) => panel.dataset.howtoPanel ?? "",
    ),
    cards: cards.length,
    plates: plates.length,
    steps: document.querySelectorAll("[data-howto-steps]").length,
    perTab: [...document.querySelectorAll<HTMLElement>("[data-howto-panel]")].map(
      (panel) => panel.querySelectorAll("[data-howto-card]").length,
    ),
    mismatched: plates
      .filter((plate) => {
        const card = plate.closest("[data-howto-card]");
        const button = card?.querySelector("[data-copy]");
        const text = plate.querySelector("code")?.textContent ?? "";
        return !button || button.getAttribute("data-copy") !== text;
      })
      .map((plate) => plate.dataset.howtoCode ?? "?"),
    cardsWithNoCopyOrSteps: cards
      .filter(
        (card) => !card.querySelector("[data-copy]") && !card.querySelector("[data-howto-steps]"),
      )
      .map((card) => panelOf(card) + "/" + card.getAttribute("data-howto-card")),
  };
});
JSON.stringify(howto.tabs) === JSON.stringify(["os", "web", "terminals", "frameworks"]) &&
howto.panels.length === 4
  ? pass(`how-to: four tabs (${howto.tabs.join(" · ")}), one panel each`)
  : fail(`how-to: tabs ${JSON.stringify(howto.tabs)}, panels ${JSON.stringify(howto.panels)}`);
howto.cards === 14 && howto.plates === 13 && howto.steps === 1
  ? pass(
      `how-to: ${howto.cards} cards across ${howto.perTab.join("/")} per tab, ${howto.plates} code plates, 1 GUI recipe`,
    )
  : fail(
      `how-to: ${howto.cards} cards, ${howto.plates} plates, ${howto.steps} step lists (${howto.perTab.join("/")})`,
    );
howto.mismatched.length === 0 && howto.cardsWithNoCopyOrSteps.length === 0
  ? pass("how-to: every copy button carries its plate, every card is actionable")
  : fail(
      `how-to: payload mismatches ${JSON.stringify(howto.mismatched)}, empty cards ${JSON.stringify(howto.cardsWithNoCopyOrSteps)}`,
    );

// Switching tabs swaps the visible panel, and the copy button inherits Base.astro's toast.
const visiblePanels = () =>
  page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("[data-howto-panel]")]
      .filter((panel) => panel.getBoundingClientRect().height > 0)
      .map((panel) => panel.dataset.howtoPanel ?? ""),
  );
const beforePanels = await visiblePanels();
// A real mouse click, not element.click(): Radix Tabs selects on mousedown, not on click.
await page.click('[data-howto-tab="terminals"]');
await new Promise((resolve) => setTimeout(resolve, 150));
// The active pill cross-fades its ink over 200ms, so a fixed sleep samples the interpolation —
// Chrome reports that mid-value as oklab(...) and it drifts run to run. Wait for the trigger's own
// transition to stop, then assert the settled style (the thresholds below are unchanged).
await page
  .waitForFunction(
    () => {
      const tab = document.querySelector('[data-howto-tab="terminals"]');
      if (!tab || tab.getAttribute("data-state") !== "active") return false;
      if (tab.getAnimations().some((animation) => animation.playState === "running")) return false;
      const state = window as unknown as { __ink?: string; __still?: number };
      const ink = getComputedStyle(tab).color;
      state.__still = ink === state.__ink ? (state.__still ?? 0) + 1 : 0;
      state.__ink = ink;
      return (state.__still ?? 0) >= 3;
    },
    { polling: "raf", timeout: 4_000 },
  )
  .catch(() => undefined);
const tabSwitch = await page.evaluate(async () => {
  const after = [...document.querySelectorAll<HTMLElement>("[data-howto-panel]")]
    .filter((panel) => panel.getBoundingClientRect().height > 0)
    .map((panel) => panel.dataset.howtoPanel ?? "");
  const terminals = document.querySelector<HTMLElement>('[data-howto-tab="terminals"]');
  const copy = document.querySelector<HTMLElement>('[data-howto-card="ghostty"] [data-copy]');
  copy?.click();
  await new Promise((resolve) => setTimeout(resolve, 80));
  const toast = document.getElementById("toast")?.textContent ?? "";
  const shown = document.getElementById("toast")?.classList.contains("show") ?? false;
  const style = terminals ? getComputedStyle(terminals) : null;
  return {
    after,
    active: terminals?.getAttribute("data-state") ?? "",
    toast,
    shown,
    payload: copy?.getAttribute("data-copy") ?? "",
    fill: style?.backgroundImage ?? "",
    color: style?.color ?? "",
  };
});
const tabState = { before: beforePanels, ...tabSwitch };
JSON.stringify(tabState.before) === JSON.stringify(["os"]) &&
JSON.stringify(tabState.after) === JSON.stringify(["terminals"]) &&
tabState.active === "active"
  ? pass("how-to: switching to Terminals hides the OS panel and marks the tab active")
  : fail(
      `how-to: panels ${JSON.stringify(tabState.before)} -> ${JSON.stringify(tabState.after)}, tab state ${tabState.active}`,
    );
tabState.fill.startsWith("linear-gradient") && tabState.color === "rgb(37, 41, 37)"
  ? pass(`how-to: the active tab carries the blue fill and the dark ink (${tabState.color})`)
  : fail(`how-to: active tab fill is ${tabState.fill}, ink ${tabState.color}`);
tabState.shown &&
tabState.toast.startsWith("copied") &&
tabState.toast.includes(tabState.payload.slice(0, 20))
  ? pass("how-to: a snippet copy button writes the plate to the clipboard and fires the toast")
  : fail(`how-to: toast ${JSON.stringify(tabSwitch.toast)} shown=${tabSwitch.shown}`);

// 5. The hero's agent container: markdown rendered in Qu Black — bold, inline code and a
// colourless code plate — plus a streamed reply.
const chat = await page.evaluate(() => {
  const thread = document.getElementById("agent-thread");
  const code = thread?.querySelector<HTMLElement>("pre[data-md-code]");
  const codeText = code?.querySelector("code");
  const bold = thread?.querySelector<HTMLElement>("[data-md-bold]");
  const inline = thread?.querySelector<HTMLElement>("[data-md-inline-code]");
  const colour = (element: Element | null | undefined) =>
    element ? getComputedStyle(element).color : "";
  return {
    messages: thread?.querySelectorAll("[data-message]").length ?? 0,
    codeBlocks: thread?.querySelectorAll("pre[data-md-code]").length ?? 0,
    codeFont: code ? getComputedStyle(code).fontFamily : "",
    boldWeight: bold ? getComputedStyle(bold).fontWeight : "",
    boldText: bold?.textContent ?? "",
    inlineFont: inline ? getComputedStyle(inline).fontFamily : "",
    codeUniform: codeText ? colour(code) === colour(codeText) : false,
    codeSpans: code ? code.querySelectorAll("span").length : -1,
    title: document.title,
  };
});
chat.messages >= 4
  ? pass(`agent chat: ${chat.messages} messages in the initial thread`)
  : fail(`agent chat: ${chat.messages} messages`);
chat.codeBlocks >= 3 && chat.codeFont.includes("Qu Black Mono")
  ? pass(`agent chat: ${chat.codeBlocks} markdown code plates render in Qu Black Mono`)
  : fail(`agent chat: ${chat.codeBlocks} code plates, font ${chat.codeFont}`);
chat.codeUniform && chat.codeSpans === 0
  ? pass("agent chat: code plate is one greyscale slab (no syntax colours)")
  : fail(`agent chat: code colours uniform=${chat.codeUniform}, spans=${chat.codeSpans}`);
chat.boldWeight === "700" && chat.boldText.includes("Found it")
  ? pass(`agent chat: **bold** renders at weight ${chat.boldWeight}`)
  : fail(`agent chat: bold weight ${chat.boldWeight}, text ${JSON.stringify(chat.boldText)}`);
chat.inlineFont.includes("Qu Black Mono")
  ? pass("agent chat: inline code renders in Qu Black Mono")
  : fail(`agent chat: inline code font ${chat.inlineFont}`);

// The ghost-indent bug: every rendered code line starts at the same x, and only intentional
// nesting carries indentation. Measured from the rendered glyphs, not from the source.
const indentation = await page.evaluate(() => {
  const plates = [...document.querySelectorAll<HTMLElement>("#agent-thread pre[data-md-code]")];
  const diff = plates.find((plate) => (plate.textContent ?? "").includes("grid-cols-[1fr_auto]"));
  const css = plates.find((plate) => (plate.textContent ?? "").includes("word-break"));
  const lineStarts = (plate: HTMLElement | undefined) => {
    const code = plate?.querySelector("code");
    const node = code?.firstChild;
    if (!code || !node) return { lefts: [] as number[], leading: [] as number[] };
    const text = code.textContent ?? "";
    const lefts: number[] = [];
    const leading: number[] = [];
    let offset = 0;
    for (const line of text.split("\n")) {
      const range = document.createRange();
      range.setStart(node, offset);
      range.setEnd(node, offset + Math.max(1, line.length));
      lefts.push(Math.round(range.getBoundingClientRect().left));
      leading.push(line.length - line.trimStart().length);
      offset += line.length + 1;
    }
    return { lefts, leading };
  };
  return { diff: lineStarts(diff), css: lineStarts(css) };
});
const diffAligned =
  indentation.diff.lefts.length === 2 &&
  new Set(indentation.diff.lefts).size === 1 &&
  indentation.diff.leading.every((spaces) => spaces === 0);
diffAligned
  ? pass(
      `agent chat: diff lines share one left edge (${indentation.diff.lefts[0]}px), no ghost indent`,
    )
  : fail(
      `agent chat: diff lefts ${JSON.stringify(indentation.diff.lefts)}, leading ${JSON.stringify(indentation.diff.leading)}`,
    );
const cssNesting = indentation.css.leading.slice(1, -1);
cssNesting.length > 0 && cssNesting.every((spaces) => spaces === 2)
  ? pass("agent chat: intentional 2-space css nesting survived the dedent")
  : fail(`agent chat: css leading spaces ${JSON.stringify(indentation.css.leading)}`);

const sizing = await page.evaluate(() => {
  const input = document.getElementById("agent-input") as HTMLElement | null;
  const body = document.querySelector("#agent-thread [data-message-body]") as HTMLElement | null;
  return {
    input: input ? Number.parseFloat(getComputedStyle(input).fontSize) : 0,
    // The placeholder must inherit the input size — muted colour, never a smaller type size.
    placeholder: input
      ? Number.parseFloat(getComputedStyle(input, "::placeholder").fontSize) || 0
      : 0,
    body: body ? Number.parseFloat(getComputedStyle(body).fontSize) : 0,
  };
});
sizing.input > 0 && sizing.input === sizing.body
  ? pass(`agent chat: input is exactly the message body size (${sizing.input}px)`)
  : fail(`agent chat: input ${sizing.input}px vs body ${sizing.body}px`);
sizing.placeholder === 0 || sizing.placeholder === sizing.input
  ? pass(`agent chat: placeholder keeps the input size (${sizing.input}px)`)
  : fail(`agent chat: placeholder ${sizing.placeholder}px vs input ${sizing.input}px`);

// Alignment audit (delta 3): the specimen header, the control strip, the lookalike table and the
// CTA row are measured in the DOM, not eyeballed. Tolerance is 2px everywhere.
const alignment = await page.evaluate(() => {
  const box = (el: Element) => el.getBoundingClientRect();
  const cy = (el: Element) => (box(el).top + box(el).bottom) / 2;
  const spread = (values: number[]) => Math.max(...values) - Math.min(...values);
  const header = document.querySelector("[data-specimen-header]")!;
  const groups = [...document.querySelectorAll("[data-control-group]")];
  const metrics = document.querySelector("[data-control-metrics]")!;
  const chips = [...document.querySelectorAll("#specimen [data-control]")];
  const labels = [...document.querySelectorAll("[data-testid=lookalike-label]")];
  // The hero CTA row: Download the release + How to use (v1.0.4 replaced the old #download
  // button, so the audit anchors on the row itself rather than on one button's href).
  const ctas = [...document.querySelector("[data-cta-row]")!.children];
  const sameRow = ctas.filter((cta) => Math.abs(box(cta).top - box(ctas[0]!).top) < 1);
  return {
    headerDelta: Math.abs(cy(header.children[0]!) - cy(header.children[1]!)),
    groupGaps: groups.slice(1).map((group, index) => box(group).left - box(groups[index]!).right),
    metricsDelta: Math.abs(cy(metrics) - cy(groups[0]!)),
    chipDelta: spread(chips.map(cy)),
    labelSpread: spread(labels.map((label) => box(label).left)),
    labelCount: labels.length,
    ctaGaps: sameRow.slice(1).map((cta, index) => box(cta).left - box(sameRow[index]!).right),
    ctaRowWidths: [...new Set(ctas.map((cta) => Math.round(box(cta).top)))].length,
  };
});
alignment.headerDelta <= 2
  ? pass(`alignment: specimen header is centred (${alignment.headerDelta.toFixed(1)}px apart)`)
  : fail(`alignment: header centres are ${alignment.headerDelta.toFixed(1)}px apart`);
Math.max(...alignment.groupGaps) - Math.min(...alignment.groupGaps) <= 2
  ? pass(
      `alignment: control groups share one gap (${alignment.groupGaps.map((gap) => gap.toFixed(1)).join("/")}px)`,
    )
  : fail(`alignment: group gaps ${JSON.stringify(alignment.groupGaps)}`);
alignment.chipDelta <= 2 && alignment.metricsDelta <= 2
  ? pass(
      `alignment: controls and metrics share one centreline (chips ±${alignment.chipDelta.toFixed(1)}px, metrics ${alignment.metricsDelta.toFixed(1)}px)`,
    )
  : fail(
      `alignment: chips ${alignment.chipDelta.toFixed(1)}px, metrics ${alignment.metricsDelta.toFixed(1)}px`,
    );
alignment.labelCount >= 12 && alignment.labelSpread <= 2
  ? pass(
      `alignment: lookalike labels sit on one column (${alignment.labelSpread.toFixed(1)}px spread)`,
    )
  : fail(`alignment: ${alignment.labelCount} labels, spread ${alignment.labelSpread.toFixed(1)}px`);
// One two-column grid for the whole site: every section that is two-up splits on the same line.
const seam = await page.evaluate(() => {
  const grids = [...document.querySelectorAll("[data-two-column]")].map((grid) => {
    const children = [...grid.children].map((child) => child.getBoundingClientRect());
    const twoUp = children.length === 2 && Math.abs(children[0]!.top - children[1]!.top) < 2;
    return {
      id: grid.closest("section")?.id ?? "?",
      twoUp,
      gap: Number.parseFloat(getComputedStyle(grid).columnGap) || 0,
      rightStart: twoUp ? children[1]!.left : null,
    };
  });
  const twoUp = grids.filter((grid) => grid.twoUp);
  const starts = twoUp.map((grid) => grid.rightStart!);
  return {
    sections: grids.length,
    twoUp: twoUp.length,
    gaps: [...new Set(twoUp.map((grid) => grid.gap))],
    startSpread: starts.length > 1 ? Math.max(...starts) - Math.min(...starts) : 0,
    start: starts[0] ?? 0,
  };
});
seam.twoUp >= 4 &&
Math.max(...seam.gaps) - Math.min(...seam.gaps) <= 2 &&
Math.abs(seam.gaps[0]! - 16) <= 2 &&
seam.startSpread <= 2
  ? pass(
      `alignment: ${seam.twoUp}/${seam.sections} sections share one seam (gutter ${seam.gaps[0]}px, right column at ${Math.round(seam.start)}px, spread ${seam.startSpread.toFixed(1)}px)`,
    )
  : fail(
      `alignment: seam gaps ${JSON.stringify(seam.gaps)}, start spread ${seam.startSpread.toFixed(1)}px`,
    );

const groupLabels = await page.evaluate(() =>
  [...document.querySelectorAll("[data-control-group] > span")].map((label) =>
    Math.round(label.getBoundingClientRect().width),
  ),
);
Math.max(...groupLabels) - Math.min(...groupLabels) <= 2
  ? pass(`alignment: control labels share one width (${groupLabels[0]}px)`)
  : fail(`alignment: control label widths ${JSON.stringify(groupLabels)}`);

const typography = await page.evaluate(() => {
  const baselineDelta = (row: Element) => {
    const glyph = row.querySelector("[data-lookalike-glyphs] span")!;
    const label = row.querySelector("[data-testid=lookalike-label]") as HTMLElement;
    const text = label.firstChild!;
    const range = document.createRange();
    range.setStart(text, 0);
    range.setEnd(text, 1);
    return glyph.getBoundingClientRect().bottom - range.getBoundingClientRect().bottom;
  };
  const deltas = [...document.querySelectorAll("[data-lookalike]")].map(baselineDelta);
  const cells = [...document.querySelectorAll("[data-stat-grid] > div")];
  const labelSizes = [
    ...new Set(cells.map((cell) => getComputedStyle(cell.querySelector("dt")!).fontSize)),
  ];
  const valueSizes = [
    ...new Set(cells.map((cell) => getComputedStyle(cell.querySelector("dd")!).fontSize)),
  ];
  const buttonInk = (element: Element) => {
    const style = getComputedStyle(element);
    const canvas = document.createElement("canvas").getContext("2d")!;
    canvas.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const metrics = canvas.measureText(element.textContent ?? "");
    const box = element.getBoundingClientRect();
    const centre = (box.top + box.bottom) / 2;
    const inkCentre =
      centre -
      (metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent) / 2 +
      (metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent) / 2;
    return Math.abs(inkCentre - centre);
  };
  return {
    baselineSpread: Math.max(...deltas) - Math.min(...deltas),
    baselineRows: deltas.length,
    labelSizes,
    valueSizes,
    copyOffset: buttonInk(document.querySelector("[data-howto-card='macos'] [data-copy]")!),
    sendOffset: buttonInk(document.querySelector("#agent-form button")!),
  };
});
typography.baselineRows >= 12 && typography.baselineSpread <= 2
  ? pass(
      `alignment: lookalike baselines agree across ${typography.baselineRows} rows (±${typography.baselineSpread.toFixed(1)}px)`,
    )
  : fail(`alignment: lookalike baseline spread ${typography.baselineSpread.toFixed(1)}px`);
typography.labelSizes.length === 1 && typography.valueSizes.length === 1
  ? pass(
      `alignment: both grid cards use one stat style (${typography.labelSizes[0]} / ${typography.valueSizes[0]})`,
    )
  : fail(
      `alignment: stat sizes ${JSON.stringify(typography.labelSizes)} / ${JSON.stringify(typography.valueSizes)}`,
    );
typography.copyOffset <= 2 && typography.sendOffset <= 2
  ? pass(
      `alignment: how-to copy and send stay centred (ink offset ${typography.copyOffset.toFixed(1)} / ${typography.sendOffset.toFixed(1)}px)`,
    )
  : fail(
      `alignment: button ink offsets ${typography.copyOffset.toFixed(1)} / ${typography.sendOffset.toFixed(1)}px`,
    );

alignment.ctaGaps.every((gap) => Math.abs(gap - 9.6) <= 2)
  ? pass(
      `alignment: CTA gaps are even (${alignment.ctaGaps.map((gap) => gap.toFixed(1)).join("/")}px; ${alignment.ctaRowWidths - 1} button wraps to a second row) — measured, unchanged`,
    )
  : fail(`alignment: CTA gaps ${JSON.stringify(alignment.ctaGaps)}`);

// Mobile containment: nothing may stick out past the viewport, at any of the three audited widths.
// document.scrollWidth is not the test — an ancestor clips the overflow, so each element is measured.
const scanOverflow = async (width: number) => {
  await page.setViewport({ width, height: width === 390 ? 844 : 900 });
  await page.reload({ waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  return page.evaluate(() => {
    const limit = window.innerWidth + 1;
    // An element wider than the viewport is fine when it lives inside a horizontal scroller —
    // that is the code plate doing its job. Anything else sticking out is a real overflow.
    const inScroller = (element: Element): boolean => {
      let node = element.parentElement;
      while (node && node !== document.body) {
        const style = getComputedStyle(node);
        if (
          (style.overflowX === "auto" || style.overflowX === "scroll") &&
          node.scrollWidth > node.clientWidth
        ) {
          return true;
        }
        node = node.parentElement;
      }
      return false;
    };
    const offenders = [...document.querySelectorAll("*")]
      .map((element) => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ element, rect }) => rect.width > 0 && rect.right > limit && !inScroller(element))
      .slice(0, 6)
      .map(
        ({ element, rect }) =>
          `${element.tagName.toLowerCase()}.${String(element.className).split(" ")[0]}@${Math.round(rect.right)}`,
      );
    const plates = [...document.querySelectorAll<HTMLElement>("#agent-thread pre[data-md-code]")];
    return {
      innerWidth: window.innerWidth,
      offenders,
      scrolls: plates.filter((plate) => plate.scrollWidth > plate.clientWidth).length,
      clipped: plates.filter((plate) => getComputedStyle(plate).overflowX !== "auto").length,
      threadFits:
        document.getElementById("agent-thread")!.scrollWidth <=
        document.getElementById("agent-thread")!.clientWidth,
      keysWrap: getComputedStyle(document.querySelector("[data-control-metrics]")!).whiteSpace,
      // Tablet ASCII: no cell label may be ellipsized away.
      asciiTruncated: [...document.querySelectorAll("#ascii-grid > div")].filter((cell) => {
        const label = cell.lastElementChild as HTMLElement;
        return label.scrollWidth > label.clientWidth + 1;
      }).length,
      asciiColumns: getComputedStyle(
        document.getElementById("ascii-grid")!,
      ).gridTemplateColumns.split(" ").length,
      // The How-to tab strip: never clipped, one row where it fits, uniform pill heights.
      howtoListFits: (() => {
        const list = document.querySelector<HTMLElement>("[data-howto-tabs]");
        return list ? list.scrollWidth <= list.clientWidth + 1 : false;
      })(),
      howtoRows: new Set(
        [...document.querySelectorAll("[data-howto-tab]")].map((tab) =>
          Math.round(tab.getBoundingClientRect().top),
        ),
      ).size,
      howtoHeights: [
        ...new Set(
          [...document.querySelectorAll("[data-howto-tab]")].map((tab) =>
            Math.round(tab.getBoundingClientRect().height),
          ),
        ),
      ],
      howtoCards: document.querySelectorAll("[data-howto-card]").length,
      // The top bar is trimmed to three items: the install guide, the download, the repo.
      navItems: [...document.querySelectorAll("#site-header nav a, #site-header nav button")]
        .filter((item) => item.getBoundingClientRect().width > 0)
        .map((item) => item.textContent?.trim() ?? ""),
      navFits: (() => {
        const nav = document.querySelector<HTMLElement>("#site-header nav");
        return nav ? nav.scrollWidth <= nav.clientWidth + 1 : false;
      })(),
      // Hero: the left column and the chat card must end on the same line when two-up. The card is
      // taken out of flow at >=1180px precisely so the left column keeps setting that line.
      heroBottoms: (() => {
        const grid = document.querySelector("#specimen [data-two-column]");
        if (!grid) return null;
        const kids = [...grid.children].map((child) => child.getBoundingClientRect());
        const twoUp = kids.length === 2 && Math.abs(kids[0]!.top - kids[1]!.top) < 2;
        return twoUp ? Math.round(Math.abs(kids[0]!.bottom - kids[1]!.bottom) * 10) / 10 : null;
      })(),
      // Chat tail (delta 9e): the bubbles ride the input row. The newest bubble must end exactly
      // one inter-message gap above the form, and the form must stay pinned to the card's bottom
      // edge. Where the copy column hands the card spare height (two-up only), the spare has to
      // pool ABOVE the first bubble — which is why the probe grows the card by 240px: the thread
      // never underflows on its own at these three widths, so this is the only honest way to see
      // whether spare height parks at the top (a dead zone) or is absorbed by the anchor.
      chatTail: (() => {
        const thread = document.getElementById("agent-thread");
        const form = document.getElementById("agent-form");
        const card = document.getElementById("agent-chat");
        const messages = [...(thread?.querySelectorAll<HTMLElement>("[data-message]") ?? [])];
        if (!thread || !form || !card || messages.length < 2) return null;
        const box = (element: Element) => element.getBoundingClientRect();
        const newest = messages[messages.length - 1]!;
        const gaps = messages
          .slice(1)
          .map((message, index) => box(message).top - box(messages[index]!).bottom);
        const inter = gaps.slice().sort((a, b) => a - b)[Math.floor(gaps.length / 2)]!;
        const tail = box(form).top - box(newest).bottom;
        // The card's 1px border is outside its padding box; the form must sit on that edge.
        const pinned =
          box(card).bottom -
          Number.parseFloat(getComputedStyle(card).borderBottomWidth) -
          box(form).bottom;
        const clientBefore = thread.clientHeight;
        const previous = card.style.height;
        card.style.height = `${box(card).height + 240}px`;
        const grown = thread.clientHeight - clientBefore;
        const paddingTop = Number.parseFloat(getComputedStyle(thread).paddingTop);
        const spare = box(messages[0]!).top - (box(thread).top + paddingTop);
        const spareTail = box(form).top - box(messages[messages.length - 1]!).bottom;
        card.style.height = previous;
        const round = (value: number) => Math.round(value * 10) / 10;
        return {
          inter: round(inter),
          tail: round(tail),
          pinned: round(pinned),
          grown: Math.round(grown),
          spare: grown > 40 ? round(spare) : null,
          spareTail: grown > 40 ? round(spareTail) : null,
        };
      })(),
      // Download: the zip list and the install/sha block must end on the same line when two-up.
      downloadBottoms: (() => {
        const grid = document.querySelector("#download [data-two-column]");
        if (!grid) return null;
        const kids = [...grid.children].map((child) => child.getBoundingClientRect());
        const twoUp = kids.length === 2 && Math.abs(kids[0]!.top - kids[1]!.top) < 2;
        return twoUp ? Math.round(Math.abs(kids[0]!.bottom - kids[1]!.bottom) * 10) / 10 : null;
      })(),
    };
  });
};
for (const width of [390, 834, 1440]) {
  const audit = await scanOverflow(width);
  audit.offenders.length === 0
    ? pass(`containment ${width}px: no element extends past the viewport`)
    : fail(`containment ${width}px: ${audit.offenders.join(", ")}`);
  if (width === 390) {
    audit.scrolls >= 1 && audit.clipped === 0
      ? pass(
          `containment 390px: ${audit.scrolls} long code plates scroll horizontally (overflow-x auto)`,
        )
      : fail(`containment 390px: ${audit.scrolls} scrolling plates, ${audit.clipped} clipped`);
    audit.threadFits
      ? pass("containment 390px: the chat thread no longer overflows its own box")
      : fail("containment 390px: the chat thread is still wider than its box");
    audit.keysWrap === "normal"
      ? pass("containment 390px: the keys helper is allowed to wrap")
      : fail(`containment 390px: keys helper white-space is ${audit.keysWrap}`);
  }
  if (width === 834) {
    audit.asciiTruncated === 0
      ? pass(`containment 834px: no ASCII label is ellipsized (${audit.asciiColumns} columns)`)
      : fail(`containment 834px: ${audit.asciiTruncated} ASCII labels truncate`);
  }
  audit.howtoListFits &&
  audit.howtoCards === 14 &&
  Math.max(...audit.howtoHeights) - Math.min(...audit.howtoHeights) <= 1
    ? pass(
        `how-to ${width}px: the tab strip fits (no clipping), ${audit.howtoRows} row(s), pill heights ${audit.howtoHeights.join("/")}px`,
      )
    : fail(
        `how-to ${width}px: fits=${audit.howtoListFits}, ${audit.howtoCards} cards, heights ${JSON.stringify(audit.howtoHeights)}`,
      );
  const NAV = ["How to use", "Download", "GitHub"];
  JSON.stringify(audit.navItems) === JSON.stringify(NAV) && audit.navFits
    ? pass(`nav ${width}px: exactly three items (${audit.navItems.join(" · ")}), nothing clipped`)
    : fail(`nav ${width}px: ${JSON.stringify(audit.navItems)}, fits=${audit.navFits}`);
  audit.heroBottoms === null
    ? pass(`hero ${width}px: one column, so bottom alignment does not apply`)
    : audit.heroBottoms <= 2
      ? pass(
          `hero ${width}px: the chat card ends on the left column's line (${audit.heroBottoms}px apart)`,
        )
      : fail(`hero ${width}px: the columns end ${audit.heroBottoms}px apart`);
  const tail = audit.chatTail;
  const tailOk =
    tail !== null && Math.abs(tail.tail - tail.inter) <= 4 && Math.abs(tail.pinned) <= 1;
  tailOk
    ? pass(
        `chat ${width}px: the newest bubble ends one gap above the input (${tail!.tail}px vs ${tail!.inter}px), form pinned to the card bottom (${tail!.pinned}px)`,
      )
    : fail(`chat ${width}px: tail ${JSON.stringify(tail)}`);
  if (tail && tail.spare !== null) {
    tail.spare > 1 && tail.spareTail !== null && Math.abs(tail.spareTail - tail.inter) <= 4
      ? pass(
          `chat ${width}px: spare height (${tail.spare}px) pools above the first bubble; the tail stays one gap (${tail.spareTail}px)`,
        )
      : fail(
          `chat ${width}px: spare height parked wrong — ${tail.spare}px above the first bubble, tail ${tail.spareTail}px`,
        );
  } else {
    pass(`chat ${width}px: no spare height at this width, so there is nothing to park`);
  }
  if (width === 1440) {
    audit.heroBottoms !== null && audit.heroBottoms <= 2
      ? pass(`hero 1440px: two-up and flush (${audit.heroBottoms}px apart)`)
      : fail(`hero 1440px: bottoms differ by ${audit.heroBottoms}px`);
    audit.howtoRows === 1
      ? pass("how-to 1440px: four tabs on one row")
      : fail(`how-to 1440px: ${audit.howtoRows} tab rows`);
    audit.downloadBottoms !== null && audit.downloadBottoms <= 2
      ? pass(`download 1440px: both blocks end on one line (${audit.downloadBottoms}px apart)`)
      : fail(`download 1440px: bottoms differ by ${audit.downloadBottoms}px`);
  }
}
await page.setViewport({ width: 1440, height: 900 });
await page.reload({ waitUntil: "load" });
await page.evaluate(() => document.fonts.ready.then(() => undefined));

// The editable specimen compensates Mono's upm-833 cell: font-size × 0.833 so one hanzi keeps
// the same optical size, and nothing outside the specimen (ASCII table, 2:1 proof) rescales.
await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
const specimenOptics = () =>
  page.evaluate(() => {
    const hero = document.getElementById("hero-specimen")!;
    const sample = document.getElementById("specimen-sample")!;
    const cell = document.querySelector("#ascii-grid span")!;
    const context = document.createElement("canvas").getContext("2d")!;
    const family =
      document.documentElement.dataset.specimenFamily === "mono"
        ? "Qu Black Mono"
        : "Qu Black Sans";
    const size = Number.parseFloat(getComputedStyle(hero).fontSize);
    context.font = `${size}px "${family}"`;
    const metrics = context.measureText("汉");
    return {
      size,
      sampleSize: Number.parseFloat(getComputedStyle(sample).fontSize),
      hanInk: metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent,
      asciiCell: Number.parseFloat(getComputedStyle(cell).fontSize),
    };
  });
await page.keyboard.press("s");
const opticalSans = await specimenOptics();
await page.keyboard.press("n");
const opticalMono = await specimenOptics();
const opticalRatio = opticalMono.size / opticalSans.size;
const inkDelta = Math.abs(opticalMono.hanInk - opticalSans.hanInk) / opticalSans.hanInk;
Math.abs(opticalRatio - 0.833) <= 0.01
  ? pass(
      `specimen optics: mono font-size is ${(opticalRatio * 100).toFixed(1)}% of sans (833/1000)`,
    )
  : fail(`specimen optics: ratio ${opticalRatio.toFixed(4)}`);
inkDelta <= 0.02
  ? pass(`specimen optics: hanzi ink height equal within ${(inkDelta * 100).toFixed(2)}% (< 2%)`)
  : fail(`specimen optics: hanzi ink differs by ${(inkDelta * 100).toFixed(2)}%`);
opticalMono.asciiCell === opticalSans.asciiCell
  ? pass(`specimen optics: the ASCII table keeps its real size (${opticalSans.asciiCell}px)`)
  : fail(`specimen optics: ascii cell ${opticalSans.asciiCell}px -> ${opticalMono.asciiCell}px`);

// The delta's own threshold: below ~1020px the hero is one column and the chat owns the row.
await page.setViewport({ width: 1024, height: 900 });
await page.reload({ waitUntil: "load" });
const narrow = await page.evaluate(() => {
  const chat = document.getElementById("agent-chat")!.getBoundingClientRect();
  const wrap = document.querySelector("#specimen .bf-wrap")!.getBoundingClientRect();
  const heading = document.querySelector("#specimen h1")!.getBoundingClientRect();
  // 1024 is above the 900px two-up breakpoint, so the download columns must share a bottom too.
  const download = [...document.querySelector("#download [data-two-column]")!.children].map(
    (child) => child.getBoundingClientRect(),
  );
  return {
    chat: Math.round(chat.width),
    wrap: Math.round(wrap.width),
    singleColumn: Math.round(chat.x) === Math.round(heading.x),
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    downloadDelta:
      download.length === 2 && Math.abs(download[0]!.top - download[1]!.top) < 2
        ? Math.round(Math.abs(download[0]!.bottom - download[1]!.bottom) * 10) / 10
        : null,
  };
});
narrow.singleColumn && narrow.chat === narrow.wrap && narrow.overflow === 0
  ? pass(`agent chat: 1024px is one column and full width (${narrow.chat}px = wrap)`)
  : fail(
      `agent chat: 1024px single=${narrow.singleColumn}, chat ${narrow.chat} vs wrap ${narrow.wrap}`,
    );
narrow.downloadDelta !== null && narrow.downloadDelta <= 2
  ? pass(`download 1024px: both blocks end on one line (${narrow.downloadDelta}px apart)`)
  : fail(`download 1024px: bottoms differ by ${narrow.downloadDelta}px`);

// The hero's exact two-up breakpoint: the chat card must already be flush at 1180px, not just 1440.
await page.setViewport({ width: 1180, height: 900 });
await page.reload({ waitUntil: "load" });
await page.evaluate(() => document.fonts.ready.then(() => undefined));
const heroEdge = await page.evaluate(() => {
  const kids = [...document.querySelector("#specimen [data-two-column]")!.children].map((child) =>
    child.getBoundingClientRect(),
  );
  const twoUp = kids.length === 2 && Math.abs(kids[0]!.top - kids[1]!.top) < 2;
  return {
    twoUp,
    delta: Math.round(Math.abs(kids[0]!.bottom - kids[1]!.bottom) * 10) / 10,
  };
});
heroEdge.twoUp && heroEdge.delta <= 2
  ? pass(`hero 1180px: flush at the two-up breakpoint (${heroEdge.delta}px apart)`)
  : fail(`hero 1180px: twoUp=${heroEdge.twoUp}, delta ${heroEdge.delta}px`);

await page.setViewport({ width: 390, height: 844 });
await page.reload({ waitUntil: "load" });
// Every other viewport probe awaits the faces after a reload, and the header row is measured text,
// so this one must too or it grades a fallback face (145.2px vs 138.7px for the same label).
await page.evaluate(() => document.fonts.ready.then(() => undefined));
const mobile = await page.evaluate(() => {
  const chat = document.getElementById("agent-chat")!.getBoundingClientRect();
  const wrap = document.querySelector("#specimen .bf-wrap")!.getBoundingClientRect();
  const header = document.querySelector("[data-specimen-header]")!;
  const centre = (el: Element) => {
    const box = el.getBoundingClientRect();
    return (box.top + box.bottom) / 2;
  };
  return {
    chat: Math.round(chat.width),
    wrap: Math.round(wrap.width),
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    headerDelta: Math.abs(centre(header.children[0]!) - centre(header.children[1]!)),
  };
});
mobile.chat === mobile.wrap && mobile.overflow === 0
  ? pass(`agent chat: full width on 390px (${mobile.chat}px = wrap), no overflow`)
  : fail(
      `agent chat: 390px chat ${mobile.chat} vs wrap ${mobile.wrap}, overflow ${mobile.overflow}`,
    );
mobile.headerDelta <= 2
  ? pass(
      `alignment: specimen header stays centred on 390px (${mobile.headerDelta.toFixed(1)}px apart)`,
    )
  : fail(`alignment: 390px header centres are ${mobile.headerDelta.toFixed(1)}px apart`);
await page.setViewport({ width: 1440, height: 900 });
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
    mono: document.fonts.check('400 16px "Qu Black Mono"'),
    sans: document.fonts.check('400 16px "Qu Black Sans"'),
    bytes: woff2.reduce((sum, entry) => sum + (entry.transferSize || entry.encodedBodySize), 0),
    shards: woff2.length,
    cls: (window as unknown as { __cls: number }).__cls,
  };
});
fonts.mono && fonts.sans
  ? pass("fonts: Qu Black Mono and Qu Black Sans both resolve")
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

// The chat input row shares the message thread's horizontal rails: its content box sits on the
// same left/right lines as the thread's (one padding source, asserted at every smoke viewport).
const rails = await page.evaluate(() => {
  const thread = document.getElementById("agent-thread");
  const form = document.getElementById("agent-form");
  const rail = (el: HTMLElement | null) => (el ? getComputedStyle(el).paddingLeft : "");
  return {
    threadLeft: rail(thread),
    formLeft: rail(form),
    threadRight: thread ? getComputedStyle(thread).paddingRight : "",
    formRight: form ? getComputedStyle(form).paddingRight : "",
  };
});
rails.threadLeft === rails.formLeft && rails.threadRight === rails.formRight
  ? pass(`agent chat: input row rides the thread rails (${rails.formLeft} / ${rails.formRight})`)
  : fail(
      `agent chat: input row rails ${rails.formLeft}/${rails.formRight} vs thread ${rails.threadLeft}/${rails.threadRight}`,
    );

// The download CTA is a direct zip link labelled with the release version.
const cta = await page.evaluate(() => {
  const section = document.getElementById("download");
  const buttons = [...(section?.querySelectorAll("a") ?? [])];
  const dl = buttons.find((a) => a.textContent?.includes("Download v"));
  return {
    label: dl?.textContent?.trim() ?? "",
    href: dl?.getAttribute("href") ?? "",
    releaseBtnGone: !buttons.some((a) => a.textContent?.includes("Open the release")),
  };
});
cta.label && cta.href.includes("/releases/tag/") && cta.releaseBtnGone
  ? pass(`download CTA: "${cta.label}" → ${cta.href}`)
  : fail(
      `download CTA: label="${cta.label}" href=${cta.href} releaseBtnGone=${cta.releaseBtnGone}`,
    );

// Anchor navigation lands the section just under the sticky header — one scroll offset source
// (the sections' scroll-mt), not two (html scroll-padding used to stack a second 6rem).
await page.evaluate(() => {
  document.querySelector<HTMLAnchorElement>('a[href="#download"]')?.click();
});
// The jump is a smooth scroll on a ~7500px page: it is not even moving 100ms in and is still
// 619px short at 900ms (settles at 30px by ~1.5s). Wait for the scroll to end — scrollend fires
// only when it does — and grade the landing, not the animation. The 3s guard covers a jump that
// needs no scrolling at all.
await page.evaluate(
  () =>
    new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, 3_000);
      if (!("onscrollend" in window)) return;
      window.addEventListener(
        "scrollend",
        () => {
          clearTimeout(timer);
          resolve();
        },
        { once: true },
      );
    }),
);
const landing = await page.evaluate(() => {
  const sec = document.getElementById("download")!.getBoundingClientRect();
  const header = document.querySelector("header, nav")!.getBoundingClientRect();
  return { gap: +(sec.top - header.bottom).toFixed(0) };
});
landing.gap >= 0 && landing.gap <= 48
  ? pass(`anchors: #download lands ${landing.gap}px under the header (single scroll offset)`)
  : fail(`anchors: #download lands ${landing.gap}px under the header (expected 0-48px)`);

await browser.close();
process.exit(failures ? 1 : 0);

import { DOWNLOAD_URL } from "./site.ts";

/** One copyable unit inside a tab: a config file, a shell block, or a GUI path. */
export interface HowToCard {
  /** Stable id — also the smoke-test handle ([data-howto-card="…"]). */
  id: string;
  title: string;
  /** Where the snippet goes, printed above the plate. */
  path?: string;
  /** The copyable payload. Omitted for GUI-only cards. */
  code?: string;
  /** Numbered GUI steps, for tools with no supported settings file for fonts. */
  steps?: string[];
  note?: string;
}

export interface HowToTab {
  id: string;
  label: string;
  blurb: string;
  cards: HowToCard[];
}

// The release ships one zip (flat: eight TTFs + OFL.txt + README.txt + NOTICE.md), and no
// individual TTF assets — every web snippet therefore self-hosts the files it unzips.
const MACOS = [
  "curl -fL -o /tmp/qublack.zip " + DOWNLOAD_URL,
  "mkdir -p ~/Library/Fonts",
  "unzip -o /tmp/qublack.zip '*.ttf' -d ~/Library/Fonts/",
].join("\n");

const LINUX = [
  "curl -fL -o /tmp/qublack.zip " + DOWNLOAD_URL,
  "mkdir -p ~/.local/share/fonts",
  "unzip -o /tmp/qublack.zip '*.ttf' -d ~/.local/share/fonts/",
  "fc-cache -f ~/.local/share/fonts && fc-list | grep -i 'qu black'",
].join("\n");

// curl.exe and tar.exe ship with Windows 10 1803+, so this needs no PowerShell quoting.
const WINDOWS = [
  "curl.exe -fL -o qublack.zip " + DOWNLOAD_URL,
  "tar -xf qublack.zip",
  "explorer .",
].join("\n");

const FACES = [
  "/* Eight faces ship in the zip — four per family. Qu Black Mono is for code and terminals; */",
  "/* Qu Black Sans is for prose and UI. Both carry the same hanzi, so mixed text never falls back. */",
  "@font-face {",
  '  font-family: "Qu Black Mono";',
  '  src: url("/fonts/QuBlackMono-Regular.ttf") format("truetype");',
  "  font-weight: 400;",
  "  font-style: normal;",
  "  font-display: swap;",
  "}",
  "",
  "@font-face {",
  '  font-family: "Qu Black Mono";',
  '  src: url("/fonts/QuBlackMono-Bold.ttf") format("truetype");',
  "  font-weight: 700;",
  "  font-style: normal;",
  "  font-display: swap;",
  "}",
  "",
  "@font-face {",
  '  font-family: "Qu Black Mono";',
  '  src: url("/fonts/QuBlackMono-Italic.ttf") format("truetype");',
  "  font-weight: 400;",
  "  font-style: italic;",
  "  font-display: swap;",
  "}",
  "",
  "@font-face {",
  '  font-family: "Qu Black Mono";',
  '  src: url("/fonts/QuBlackMono-BoldItalic.ttf") format("truetype");',
  "  font-weight: 700;",
  "  font-style: italic;",
  "  font-display: swap;",
  "}",
  "",
  "@font-face {",
  '  font-family: "Qu Black Sans";',
  '  src: url("/fonts/QuBlackSans-Regular.ttf") format("truetype");',
  "  font-weight: 400;",
  "  font-style: normal;",
  "  font-display: swap;",
  "}",
  "",
  "@font-face {",
  '  font-family: "Qu Black Sans";',
  '  src: url("/fonts/QuBlackSans-Bold.ttf") format("truetype");',
  "  font-weight: 700;",
  "  font-style: normal;",
  "  font-display: swap;",
  "}",
  "",
  "@font-face {",
  '  font-family: "Qu Black Sans";',
  '  src: url("/fonts/QuBlackSans-Italic.ttf") format("truetype");',
  "  font-weight: 400;",
  "  font-style: italic;",
  "  font-display: swap;",
  "}",
  "",
  "@font-face {",
  '  font-family: "Qu Black Sans";',
  '  src: url("/fonts/QuBlackSans-BoldItalic.ttf") format("truetype");',
  "  font-weight: 700;",
  "  font-style: italic;",
  "  font-display: swap;",
  "}",
  "",
  "/* prose and UI: Sans */",
  "body {",
  '  font-family: "Qu Black Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;',
  "}",
  "",
  "/* code and terminals: Mono */",
  "code, pre, kbd, samp {",
  '  font-family: "Qu Black Mono", ui-monospace, SFMono-Regular, Menlo, monospace;',
  "  font-variant-ligatures: none; /* the family ships no coding ligatures */",
  "}",
].join("\n");

const STACK = [
  ":root {",
  '  --font-mono: "Qu Black Mono", ui-monospace, SFMono-Regular, Menlo, monospace;',
  '  --font-sans: "Qu Black Sans", ui-sans-serif, system-ui, -apple-system, sans-serif;',
  "}",
].join("\n");

const GHOSTTY = [
  "# ~/.config/ghostty/config",
  "font-family = Qu Black Mono",
  "font-size = 12",
].join("\n");

const KITTY = [
  "# ~/.config/kitty/kitty.conf",
  "font_family      Qu Black Mono",
  "bold_font        Qu Black Mono Bold",
  "italic_font      Qu Black Mono Italic",
  "bold_italic_font Qu Black Mono Bold Italic",
  "font_size        12.0",
].join("\n");

const ALACRITTY = [
  "# ~/.config/alacritty/alacritty.toml",
  "[font]",
  "size = 12.0",
  "",
  "[font.normal]",
  'family = "Qu Black Mono"',
  'style = "Regular"',
  "",
  "[font.bold]",
  'family = "Qu Black Mono"',
  'style = "Bold"',
  "",
  "[font.italic]",
  'family = "Qu Black Mono"',
  'style = "Italic"',
  "",
  "[font.bold_italic]",
  'family = "Qu Black Mono"',
  'style = "Bold Italic"',
].join("\n");

const NEXT = [
  "// app/fonts.ts — the TTFs live next to this file, not in public/",
  'import localFont from "next/font/local";',
  "",
  "// prose and UI — Qu Black Sans",
  "export const qublackSans = localFont({",
  "  src: [",
  '    { path: "./fonts/QuBlackSans-Regular.ttf", weight: "400", style: "normal" },',
  '    { path: "./fonts/QuBlackSans-Bold.ttf", weight: "700", style: "normal" },',
  '    { path: "./fonts/QuBlackSans-Italic.ttf", weight: "400", style: "italic" },',
  '    { path: "./fonts/QuBlackSans-BoldItalic.ttf", weight: "700", style: "italic" },',
  "  ],",
  '  variable: "--font-qublack-sans",',
  '  display: "swap",',
  '  fallback: ["system-ui", "-apple-system", "sans-serif"],',
  "});",
  "",
  "// code and terminals — Qu Black Mono",
  "export const qublackMono = localFont({",
  "  src: [",
  '    { path: "./fonts/QuBlackMono-Regular.ttf", weight: "400", style: "normal" },',
  '    { path: "./fonts/QuBlackMono-Bold.ttf", weight: "700", style: "normal" },',
  '    { path: "./fonts/QuBlackMono-Italic.ttf", weight: "400", style: "italic" },',
  '    { path: "./fonts/QuBlackMono-BoldItalic.ttf", weight: "700", style: "italic" },',
  "  ],",
  '  variable: "--font-qublack-mono",',
  '  display: "swap",',
  '  fallback: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],',
  "});",
  "",
  "// app/layout.tsx: <body className={`${qublackSans.variable} ${qublackMono.variable}`}>",
  "// globals.css:   body { font-family: var(--font-qublack-sans); }",
  "//                code, pre { font-family: var(--font-qublack-mono); }",
].join("\n");

const ASTRO = [
  "// astro.config.mjs — Astro 6+",
  'import { defineConfig, fontProviders } from "astro/config";',
  "",
  "export default defineConfig({",
  "  fonts: [",
  "    // prose and UI",
  "    {",
  "      provider: fontProviders.local(),",
  '      name: "Qu Black Sans",',
  '      cssVariable: "--font-qublack-sans",',
  '      fallbacks: ["system-ui", "sans-serif"],',
  "      options: {",
  "        variants: [",
  '          { src: ["./src/assets/fonts/QuBlackSans-Regular.ttf"], weight: "400", style: "normal" },',
  '          { src: ["./src/assets/fonts/QuBlackSans-Bold.ttf"], weight: "700", style: "normal" },',
  '          { src: ["./src/assets/fonts/QuBlackSans-Italic.ttf"], weight: "400", style: "italic" },',
  '          { src: ["./src/assets/fonts/QuBlackSans-BoldItalic.ttf"], weight: "700", style: "italic" },',
  "        ],",
  "      },",
  "    },",
  "    // code and terminals",
  "    {",
  "      provider: fontProviders.local(),",
  '      name: "Qu Black Mono",',
  '      cssVariable: "--font-qublack-mono",',
  '      fallbacks: ["ui-monospace", "monospace"],',
  "      options: {",
  "        variants: [",
  '          { src: ["./src/assets/fonts/QuBlackMono-Regular.ttf"], weight: "400", style: "normal" },',
  '          { src: ["./src/assets/fonts/QuBlackMono-Bold.ttf"], weight: "700", style: "normal" },',
  '          { src: ["./src/assets/fonts/QuBlackMono-Italic.ttf"], weight: "400", style: "italic" },',
  '          { src: ["./src/assets/fonts/QuBlackMono-BoldItalic.ttf"], weight: "700", style: "italic" },',
  "        ],",
  "      },",
  "    },",
  "  ],",
  "});",
  "",
  '// src/layouts/Base.astro: import { Font } from "astro:assets";',
  '// <Font cssVariable="--font-qublack-sans" />  (body)',
  '// <Font cssVariable="--font-qublack-mono" />  (code)',
].join("\n");

const VITE = [
  "/* src/index.css — the TTFs sit in public/fonts/, which Vite serves at / */",
  "/* prose and UI */",
  "@font-face {",
  '  font-family: "Qu Black Sans";',
  '  src: url("/fonts/QuBlackSans-Regular.ttf") format("truetype");',
  "  font-weight: 400;",
  "  font-style: normal;",
  "  font-display: swap;",
  "}",
  "",
  "/* code and terminals */",
  "@font-face {",
  '  font-family: "Qu Black Mono";',
  '  src: url("/fonts/QuBlackMono-Regular.ttf") format("truetype");',
  "  font-weight: 400;",
  "  font-style: normal;",
  "  font-display: swap;",
  "}",
  "",
  ":root {",
  '  --font-sans: "Qu Black Sans", ui-sans-serif, system-ui, sans-serif;',
  '  --font-mono: "Qu Black Mono", ui-monospace, SFMono-Regular, Menlo, monospace;',
  "}",
  "",
  "body { font-family: var(--font-sans); }",
  "code, pre { font-family: var(--font-mono); }",
].join("\n");

const TAILWIND = [
  "/* app.css — Tailwind v4 */",
  '@import "tailwindcss";',
  "",
  "@theme {",
  '  --font-sans: "Qu Black Sans", ui-sans-serif, system-ui, sans-serif;',
  '  --font-mono: "Qu Black Mono", ui-monospace, SFMono-Regular, Menlo, monospace;',
  "}",
  "",
  "/* font-sans is the body default; font-mono is for code, pre and terminals. */",
].join("\n");

const VSCODE = [
  "{",
  '  "editor.fontFamily": "\'Qu Black Mono\', ui-monospace, Menlo, monospace",',
  '  "editor.fontLigatures": false,',
  '  "terminal.integrated.fontFamily": "Qu Black Mono"',
  "}",
].join("\n");

export const HOW_TO_TABS: HowToTab[] = [
  {
    id: "os",
    label: "OS",
    blurb:
      "Unzip once and let the system index the family. Every app picks it up on its next launch; a running terminal or editor keeps the old font until it restarts.",
    cards: [
      {
        id: "macos",
        title: "macOS",
        code: MACOS,
        note: "Font Book loads ~/Library/Fonts immediately. The '*.ttf' filter keeps OFL.txt and the README out of the folder.",
      },
      {
        id: "windows",
        title: "Windows",
        path: "PowerShell",
        code: WINDOWS,
        note: "Then select the eight .ttf files in the window that opens, right-click and choose Install for all users (Install for me only needs no admin rights).",
      },
      {
        id: "linux",
        title: "Linux",
        code: LINUX,
        note: "~/.local/share/fonts is per user; use /usr/local/share/fonts for every account. fc-list should print eight Qu Black entries.",
      },
    ],
  },
  {
    id: "web",
    label: "HTML / CSS",
    blurb:
      "Self-host the TTFs from the zip — a font URL you control beats a cross-origin hotlink. On Vite and Astro that directory is public/fonts/; the URLs below are root-relative.",
    cards: [
      {
        id: "faces",
        title: "@font-face",
        path: "fonts.css",
        code: FACES,
        note: "Eight blocks — four faces per family. Point code and terminals at Qu Black Mono, prose and UI at Qu Black Sans; both cover the same CJK blocks, so a mixed paragraph never falls back.",
      },
      {
        id: "stack",
        title: "Family stack",
        path: "tokens.css",
        code: STACK,
        note: "Two tokens, two jobs: --font-mono for code and terminals, --font-sans for body copy and UI. Keep a real monospace last in the mono stack so blocked webfonts still align; 汉字 need no fallback, both families cover the CJK blocks.",
      },
    ],
  },
  {
    id: "terminals",
    label: "Terminals",
    blurb:
      "Qu Black Mono is the terminal face. Its em is 833 units, so at the same font-size it draws 1.2x a 1000-upm mono (hanzi 1.200em, ASCII 0.600em) — divide your current size by 1.2 if the text jumps. Qu Black Sans is not a terminal face: terminals are monospace-only, so Sans belongs in prose and UI.",
    cards: [
      {
        id: "ghostty",
        title: "Ghostty",
        path: "~/.config/ghostty/config",
        code: GHOSTTY,
        note: "Validated with ghostty +validate-config. super+shift+, reloads the config; ghostty +list-fonts shows whether the family is installed.",
      },
      {
        id: "iterm2",
        title: "iTerm2",
        steps: [
          "Settings → Profiles → Text → Font → Select… → Qu Black Mono → 12.",
          "Leave Use ligatures off: the family ships no coding ligatures.",
          "Leave Use a different font for non-ASCII text off, so 汉字 stay in Qu Black Mono.",
        ],
        note: "iTerm2 has no supported settings file for fonts, so this one is a GUI pick. Repeat it for every profile you use.",
      },
      {
        id: "kitty",
        title: "kitty",
        path: "~/.config/kitty/kitty.conf",
        code: KITTY,
        note: "kitty resolves faces by full name, and those are the names inside the zip (Qu Black Mono Bold, …). Open a new window after installing the family.",
      },
      {
        id: "alacritty",
        title: "Alacritty",
        path: "~/.config/alacritty/alacritty.toml",
        code: ALACRITTY,
        note: "Every style is set explicitly: the bold and italic defaults point at the system monospace, so leaving them out would mix a second family in.",
      },
    ],
  },
  {
    id: "frameworks",
    label: "Frameworks",
    blurb: "The same eight TTFs inside your build, wired into the tools that render your code.",
    cards: [
      {
        id: "next",
        title: "Next.js",
        path: "app/fonts.ts",
        code: NEXT,
        note: "next/font/local fingerprints and self-hosts the files. Keep the TTFs in the app directory rather than public/, then point your body token at var(--font-qublack-sans) and your code token at var(--font-qublack-mono).",
      },
      {
        id: "astro",
        title: "Astro",
        path: "astro.config.mjs",
        code: ASTRO,
        note: "Local src paths resolve from the project root, and the Font component is what emits the @font-face blocks — one per family. Loading a single face with CSS instead is fine too; this site does exactly that.",
      },
      {
        id: "vite",
        title: "Vite / React",
        path: "src/index.css",
        code: VITE,
        note: "public/fonts/QuBlackSans-Regular.ttf and QuBlackMono-Regular.ttf resolve to /fonts/… in dev and in the build; add the Bold and Italic blocks the same way.",
      },
      {
        id: "tailwind",
        title: "Tailwind",
        path: "app.css",
        code: TAILWIND,
        note: "Tailwind v4 reads these keys directly: font-mono and font-sans now resolve to Qu Black. On v3 the same keys go under theme.extend.fontFamily in tailwind.config.js.",
      },
      {
        id: "vscode",
        title: "VS Code",
        path: "settings.json",
        code: VSCODE,
        note: "The editor value quotes the family name because it contains a space; the terminal key takes the bare name. VS Code does not load webfonts, so install the family first.",
      },
    ],
  },
];

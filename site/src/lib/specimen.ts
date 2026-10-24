/**
 * The specimen's keyboard/state model, kept pure so it can be tested without a browser.
 *
 * The page is a specimen first and a document second: B/L switch weight, M/N/S switch family,
 * I toggles italic, arrows walk the sections and 1–9 jump to one. None of that fires while the
 * visitor is editing text in the hero.
 *
 * Family switching is an optical decision, not just a font-family swap: Qu Black Mono sits on
 * upm 833 (hanzi 1.200em) while Qu Black Sans sits on upm 1000 (hanzi 1.000em), so at one font size
 * the mono hanzi renders 20% larger. The editable specimen therefore scales its own font-size by
 * 833/1000 when it shows the mono family — the same optical size for 汉字, with the Latin 17%
 * smaller as the accepted trade. Sections where the real 0.6em cell is the point (ASCII table,
 * 2:1 proof) never use this scale.
 */

export type Family = "sans" | "mono";
export type Weight = "regular" | "bold";

export interface SpecimenState {
  family: Family;
  weight: Weight;
  italic: boolean;
}

export const INITIAL_STATE: SpecimenState = { family: "sans", weight: "regular", italic: false };

/** 833 / 1000 — the two families' upm ratio, and the specimen's optical compensation. */
export const MONO_OPTICAL_SCALE = 0.833;

export const SECTIONS = [
  "specimen",
  "ascii",
  "lookalikes",
  "grid",
  "text",
  "coverage",
  "howto",
  "download",
] as const;

export type SectionId = (typeof SECTIONS)[number];

export interface KeyContext {
  /** True when focus sits in the editable hero or any other text field. */
  editing: boolean;
  /** Index of the section currently in view. */
  section: number;
}

export type Action =
  | { type: "state"; state: SpecimenState }
  | { type: "section"; index: number }
  | { type: "none" };

const sectionStep = (index: number, direction: 1 | -1): number => {
  const next = index + direction;
  return Math.min(SECTIONS.length - 1, Math.max(0, next));
};

/** Every key the specimen listens for; anything else is `none`. */
export function applyKey(state: SpecimenState, key: string, context: KeyContext): Action {
  if (context.editing && key.length === 1) return { type: "none" };
  switch (key) {
    case "b":
    case "B":
    case "l":
    case "L":
      return { type: "state", state: { ...state, weight: "bold" } };
    case "r":
    case "R":
      return { type: "state", state: { ...state, weight: "regular" } };
    case "m":
    case "M":
    case "n":
    case "N":
      return { type: "state", state: { ...state, family: "mono" } };
    case "s":
    case "S":
      return { type: "state", state: { ...state, family: "sans" } };
    case "i":
    case "I":
      return { type: "state", state: { ...state, italic: !state.italic } };
    case "ArrowDown":
      return { type: "section", index: sectionStep(context.section, 1) };
    case "ArrowUp":
      return { type: "section", index: sectionStep(context.section, -1) };
    default: {
      if (/^[1-9]$/.test(key)) {
        const index = Number(key) - 1;
        return index < SECTIONS.length ? { type: "section", index } : { type: "none" };
      }
      return { type: "none" };
    }
  }
}

/** The CSS family stack the specimen and the code samples use for the current state. */
export function fontFamily(state: SpecimenState): string {
  return state.family === "mono" ? '"Qu Black Mono"' : '"Qu Black Sans"';
}

/**
 * The font-size multiplier the editable specimen applies for a family: 1 for Sans, 833/1000 for
 * Mono so one hanzi keeps the same optical size across the switch.
 */
export function specimenScale(state: SpecimenState): number {
  return state.family === "mono" ? MONO_OPTICAL_SCALE : 1;
}

/** The six font faces a state can address (Regular/Bold × upright/italic per family). */
export function faceLabel(state: SpecimenState): string {
  const family = state.family === "mono" ? "Qu Black Mono" : "Qu Black Sans";
  const style = state.weight === "bold" ? "Bold" : "Regular";
  return `${family} ${style}${state.italic ? " Italic" : ""}`;
}

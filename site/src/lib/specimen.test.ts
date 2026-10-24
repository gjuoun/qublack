import { expect, test } from "bun:test";
import {
  applyKey,
  faceLabel,
  INITIAL_STATE,
  MONO_OPTICAL_SCALE,
  SECTIONS,
  type SpecimenState,
  specimenScale,
} from "./specimen.ts";

const idle = { editing: false, section: 0 };

test("B and L switch to bold, R back to regular", () => {
  expect(applyKey(INITIAL_STATE, "b", idle)).toEqual({
    type: "state",
    state: { ...INITIAL_STATE, weight: "bold" },
  });
  const bold: SpecimenState = { ...INITIAL_STATE, weight: "bold" };
  expect(applyKey(bold, "R", idle)).toEqual({ type: "state", state: INITIAL_STATE });
});

test("M and S switch family", () => {
  expect(applyKey(INITIAL_STATE, "m", idle)).toEqual({
    type: "state",
    state: { ...INITIAL_STATE, family: "mono" },
  });
  const mono: SpecimenState = { ...INITIAL_STATE, family: "mono" };
  expect(applyKey(mono, "s", idle)).toEqual({ type: "state", state: INITIAL_STATE });
});

test("N is an alias for the mono family", () => {
  expect(applyKey(INITIAL_STATE, "n", idle)).toEqual({
    type: "state",
    state: { ...INITIAL_STATE, family: "mono" },
  });
});

test("the specimen scales mono by 833/1000 so hanzi keep one optical size", () => {
  expect(specimenScale(INITIAL_STATE)).toBe(1);
  expect(specimenScale({ ...INITIAL_STATE, family: "mono" })).toBe(MONO_OPTICAL_SCALE);
  expect(MONO_OPTICAL_SCALE).toBeCloseTo(833 / 1000, 3);
});

test("I toggles italic", () => {
  expect(applyKey(INITIAL_STATE, "i", idle)).toEqual({
    type: "state",
    state: { ...INITIAL_STATE, italic: true },
  });
});

test("digits jump to a section and out-of-range digits do nothing", () => {
  expect(applyKey(INITIAL_STATE, "3", idle)).toEqual({ type: "section", index: 2 });
  expect(applyKey(INITIAL_STATE, "9", idle)).toEqual({ type: "none" });
  expect(SECTIONS.length).toBe(8);
});

test("arrows walk the sections and stop at the ends", () => {
  expect(applyKey(INITIAL_STATE, "ArrowDown", idle)).toEqual({ type: "section", index: 1 });
  expect(applyKey(INITIAL_STATE, "ArrowUp", idle)).toEqual({ type: "section", index: 0 });
  expect(
    applyKey(INITIAL_STATE, "ArrowDown", { editing: false, section: SECTIONS.length - 1 }),
  ).toEqual({
    type: "section",
    index: SECTIONS.length - 1,
  });
});

test("typing inside the editable hero never changes the specimen", () => {
  for (const key of ["b", "m", "i", "3"]) {
    expect(applyKey(INITIAL_STATE, key, { editing: true, section: 2 })).toEqual({ type: "none" });
  }
});

test("arrows still navigate while editing", () => {
  expect(applyKey(INITIAL_STATE, "ArrowDown", { editing: true, section: 2 })).toEqual({
    type: "section",
    index: 3,
  });
});

test("unknown keys are ignored", () => {
  expect(applyKey(INITIAL_STATE, "z", idle)).toEqual({ type: "none" });
});

test("the face label names the family, weight and italic", () => {
  expect(faceLabel(INITIAL_STATE)).toBe("Qu Black Sans Regular");
  expect(faceLabel({ family: "mono", weight: "bold", italic: true })).toBe(
    "Qu Black Mono Bold Italic",
  );
});

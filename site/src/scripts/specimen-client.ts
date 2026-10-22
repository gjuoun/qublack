/**
 * Wires the pure specimen model (src/lib/specimen.ts) to the page: controls, keyboard, the
 * editable hero, and the section observer that keeps arrow navigation honest.
 */

import {
  applyKey,
  faceLabel,
  INITIAL_STATE,
  SECTIONS,
  type SpecimenState,
  specimenScale,
} from "../lib/specimen.ts";

const root = document.documentElement;
const label = document.getElementById("face-label");
const editable = document.getElementById("hero-specimen");
const samples = [...document.querySelectorAll<HTMLElement>("[data-specimen]")];
// The editable specimen only: Mono's upm-833 cell is compensated so 汉字 keep one optical size.
const scaled = [...document.querySelectorAll<HTMLElement>("[data-specimen-scale]")];
const controls = [...document.querySelectorAll<HTMLElement>("[data-control]")];

let state: SpecimenState = { ...INITIAL_STATE };
let section = 0;

const isEditing = (): boolean => {
  const active = document.activeElement as HTMLElement | null;
  if (!active) return false;
  return (
    active.isContentEditable ||
    active.tagName === "INPUT" ||
    active.tagName === "TEXTAREA" ||
    active.tagName === "SELECT"
  );
};

const render = (): void => {
  root.dataset.specimenFamily = state.family;
  root.dataset.specimenWeight = state.weight;
  root.dataset.specimenItalic = String(state.italic);
  for (const sample of samples) {
    sample.style.fontFamily = state.family === "mono" ? '"QuBlack Mono"' : '"QuBlack Sans"';
    sample.style.fontWeight = state.weight === "bold" ? "700" : "400";
    sample.style.fontStyle = state.italic ? "italic" : "normal";
  }
  for (const element of scaled) {
    element.style.setProperty("--specimen-scale", String(specimenScale(state)));
  }
  for (const control of controls) {
    const kind = control.dataset.control;
    const value = control.dataset.value ?? "";
    const pressed = kind === "italic" ? state.italic : state[kind as "family" | "weight"] === value;
    control.setAttribute("aria-pressed", String(pressed));
  }
  if (label) label.textContent = faceLabel(state);
};

const setState = (next: SpecimenState): void => {
  state = next;
  render();
};

const goTo = (index: number): void => {
  const id = SECTIONS[index];
  if (!id) return;
  const target = document.getElementById(id);
  if (!target) return;
  section = index;
  root.dataset.specimenSection = id;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
};

for (const control of controls) {
  control.addEventListener("click", () => {
    const kind = control.dataset.control;
    const value = control.dataset.value ?? "";
    if (kind === "italic") return setState({ ...state, italic: !state.italic });
    if (kind === "family" || kind === "weight") {
      return setState({ ...state, [kind]: value as SpecimenState["family"] });
    }
  });
}

addEventListener("keydown", (event: KeyboardEvent) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const action = applyKey(state, event.key, { editing: isEditing(), section });
  if (action.type === "none") return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") event.preventDefault();
  if (action.type === "state") setState(action.state);
  if (action.type === "section") goTo(action.index);
});

if (editable) {
  let committed = editable.textContent ?? "";
  editable.addEventListener("focus", () => {
    committed = editable.textContent ?? "";
  });
  editable.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      committed = editable.textContent ?? "";
      editable.blur();
    }
    if (event.key === "Escape") {
      event.preventDefault();
      editable.textContent = committed;
      editable.blur();
    }
  });
  editable.addEventListener("blur", () => {
    committed = editable.textContent ?? "";
  });
}

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const index = SECTIONS.indexOf(entry.target.id as (typeof SECTIONS)[number]);
        if (index >= 0) {
          section = index;
          root.dataset.specimenSection = entry.target.id;
        }
      }
    },
    { rootMargin: "-45% 0px -45% 0px" },
  );
  for (const id of SECTIONS) {
    const target = document.getElementById(id);
    if (target) observer.observe(target);
  }
}

root.dataset.specimenSection = SECTIONS[0];
render();

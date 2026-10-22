import paletteJson from "../../../palette/qublack.json";

export interface Color {
  hex: string;
  source: string;
}
export interface Palette {
  name: string;
  appearance: string;
  colors: Record<string, Color>;
  ansi: Record<string, Color>;
  syntax: Record<string, string>;
}

/** Read at build time, so the site can never drift from the palette it ships. */
export const palette: Palette = paletteJson as Palette;

export const hex = (name: string): string => {
  const color = palette.colors[name];
  if (!color) throw new Error(`unknown colour ${name}`);
  return color.hex;
};

export const kebab = (name: string): string => name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);

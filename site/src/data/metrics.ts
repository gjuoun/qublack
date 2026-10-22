import generated from "./metrics.generated.json";

export interface FaceMetrics {
  upm: number;
  glyphs: number;
  codepoints: number;
  lineHeight: number;
  advances: Record<string, number>;
  ink: Record<string, { w: number; h: number; x: number; y: number } | null>;
}

export interface FamilyMetrics {
  display: string;
  upm: number;
  glyphs: number;
  han: number;
  ascii: number;
  ratio: number;
  lineHeight: number;
  styles: string[];
}

interface Generated {
  faces: Record<string, FaceMetrics>;
  families: Record<string, FamilyMetrics>;
}

/** Numbers the site prints are generated from the faces by tools/metrics_json.py — never typed. */
export const METRICS = generated as unknown as Generated;

export const MONO = METRICS.families.QuBlackMono;
export const SANS = METRICS.families.QuBlackSans;

export const FACE_LIST = Object.keys(METRICS.faces).sort();

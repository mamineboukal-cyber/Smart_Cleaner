// Number display: one rule everywhere (tables, stat tiles, chart labels, hovers).
// Integers keep every digit; other values show at most 4 significant figures;
// exponent form only at the extremes; percentages always carry "%".

const grouped = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const sig4 = new Intl.NumberFormat("en-US", { maximumSignificantDigits: 4 });
const pct2 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

const isMissing = (value) => value == null || Number.isNaN(value);

export function fmt(value, missing = "") {
  if (isMissing(value)) return missing;
  if (typeof value !== "number") return String(value);
  const abs = Math.abs(value);
  if (abs < 1e-12) return "0"; // floating-point noise, e.g. the mean after standardising
  if (abs >= 1e7 || abs < 1e-3) return value.toExponential(2);
  return Number.isInteger(value) ? grouped.format(value) : sig4.format(value);
}

export const fmtInt = (value) => (value == null ? "" : grouped.format(Math.round(value)));

/** A percentage already on the 0–100 scale. Tiny non-zero values never read as 0%. */
export function fmtPct(value, missing = "") {
  if (isMissing(value)) return missing;
  if (value !== 0 && Math.abs(value) < 0.01) return "<0.01%";
  return `${pct2.format(value)}%`;
}

/** Formats a profiling stat by its key, so every table and tile shows it the same way. */
export function fmtStat(key, value, missing = "") {
  if (key.endsWith("_pct")) return fmtPct(value, missing);
  if (key.startsWith("n_")) return isMissing(value) ? missing : fmtInt(value);
  return fmt(value, missing);
}

// Number display. The backend already rounds to 4 significant figures; this only
// adds thousands separators and switches to exponent form for very large/small values.

const grouped = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });

export function fmt(value, missing = "") {
  if (value == null || Number.isNaN(value)) return missing;
  if (typeof value !== "number") return String(value);
  const abs = Math.abs(value);
  if (abs < 1e-12) return "0"; // floating-point noise, e.g. the mean after standardising
  if ((abs >= 1e7 || abs < 1e-3)) return value.toExponential(2);
  return grouped.format(value);
}

export const fmtInt = (value) => (value == null ? "" : grouped.format(Math.round(value)));

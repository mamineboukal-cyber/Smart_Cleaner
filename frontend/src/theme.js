// Chart colours. Mirrors the CSS tokens in index.css (Plotly needs literal values).
// One meaning per colour: numeric = violet, categorical = teal, preview before = grey,
// preview after = violet. Red stays reserved for errors.

export const CHART = {
  numeric: "#5B3DF5",
  categorical: "#0D9488",
  before: "#8E88AB",
  after: "#5B3DF5",
  ink: "#1B1630",
  ink2: "#4A4466",
  grid: "#ECEAF5",
  axis: "#CBC6E0",
  surface: "#FFFFFF",
  font: "Plus Jakarta Sans, system-ui, sans-serif",
};

// Correlation: teal (r = -1) to violet (r = +1), neutral at r = 0. Used with a scale
// fixed to [-1, 1], so the same colour means the same r on every dataset.
export const DIVERGING = [
  [0, "#0B6B63"],
  [0.25, "#4FB8AC"],
  [0.5, "#F4F3F8"],
  [0.75, "#9D8CF8"],
  [1, "#4527C9"],
];

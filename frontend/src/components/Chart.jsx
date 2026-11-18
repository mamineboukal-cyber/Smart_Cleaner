// Charts rendered from backend chart data (the backend bins and counts, the
// browser only draws). One series per chart, so no legend: the card title
// names it. Recessive axes and hairline grids keep the bars the loudest thing.
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import { fmt } from "../format.js";
import { useLabels } from "../LabelsContext.jsx";

const createPlot = createPlotlyComponent.default ?? createPlotlyComponent;
const Plot = createPlot(Plotly);

const INK_2 = "#4e5b67";
const GRID = "#e6eaee";
const AXIS = "#c3cbd3";
const SERIES = "#2a78d6";
const SURFACE = "#ffffff";
// Diverging blue <-> red with a neutral grey at r = 0 (equal steps per arm).
const DIVERGING = [[0, "#104281"], [0.25, "#5598e7"], [0.5, "#f0efec"], [0.75, "#ec8a89"], [1, "#b22d2d"]];
const MAX_LABEL = 22;

const CONFIG_SMALL = { displaylogo: false, responsive: true, displayModeBar: false };
const CONFIG_LARGE = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["select2d", "lasso2d"] };

function baseLayout(height) {
  return {
    height,
    autosize: true,
    margin: { l: 52, r: 12, t: 8, b: 40 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Public Sans, system-ui, sans-serif", size: 11, color: INK_2 },
    hoverlabel: { bgcolor: SURFACE, bordercolor: AXIS, font: { color: "#16222e", size: 12 } },
    bargap: 0,
    barcornerradius: 3,
    showlegend: false,
  };
}

const axis = (extra = {}) => ({
  gridcolor: GRID, linecolor: AXIS, zeroline: false, tickcolor: AXIS, automargin: true,
  title: { font: { size: 11, color: INK_2 }, standoff: 6, ...extra.title }, ...extra,
});

const DAY_MS = 86_400_000;
/** Formats a bin edge (ms, UTC like the backend): the day alone when the range spans
 * several days, otherwise the day and time. */
const dateLabel = (first, last) => (ms) => {
  const iso = new Date(ms).toISOString();
  return last - first >= 2 * DAY_MS ? iso.slice(0, 10) : iso.slice(0, 16).replace("T", " ");
};

const truncate = (s) => (s.length > MAX_LABEL ? `${s.slice(0, MAX_LABEL - 1)}…` : s);

/** Histogram (numeric, or rows per hour for times of day), horizontal bar chart
 * (categories) or a note (kind "unique": almost every value distinct), from {kind, ...}. */
export default function Chart({ chart, height = 220 }) {
  const t = useLabels();
  const rows = t("ui.chart.rows");

  // Almost every value is unique: a top-values chart would be a row of invisible bars.
  if (chart?.kind === "unique") {
    return <p className="chart-empty">{t("ui.chart.near_unique", { n_unique: fmt(chart.n_unique), unique_pct: fmt(chart.unique_pct) })}</p>;
  }
  if (!chart || !chart.counts?.length) return <p className="chart-empty">{t("ui.chart.empty")}</p>;

  if (chart.kind === "histogram") {
    const isDate = chart.x_type === "date";
    const { counts } = chart;
    // Date edges arrive as ISO strings: bin maths in milliseconds, a date axis draws them.
    // The backend sends naive timestamps; read and write them as UTC so no timezone shift creeps in.
    const edges = isDate ? chart.edges.map((e) => Date.parse(`${e}Z`)) : chart.edges;
    const mid = counts.map((_, i) => (edges[i] + edges[i + 1]) / 2);
    const x = isDate ? mid.map((m) => new Date(m).toISOString().slice(0, -1)) : mid;
    const width = counts.map((_, i) => edges[i + 1] - edges[i]);
    const label = isDate ? dateLabel(edges[0], edges[edges.length - 1]) : fmt;
    const ranges = counts.map((_, i) => `[${label(edges[i])}, ${label(edges[i + 1])}${i === counts.length - 1 ? "]" : ")"}`);
    const data = [{
      type: "bar", x, y: counts, width, customdata: ranges,
      marker: { color: SERIES, line: { color: SURFACE, width: 1 } }, // 1px surface gap between bins
      hovertemplate: `%{customdata}<br>${rows}: %{y:,}<extra></extra>`,
    }];
    const xaxis = axis({ showgrid: false, ...(isDate && { type: "date" }),
                         ...(chart.x_label && { title: { text: chart.x_label } }) });
    const layout = { ...baseLayout(height), xaxis, yaxis: axis({ title: { text: rows } }) };
    return <Plot data={data} layout={layout} config={CONFIG_SMALL} useResizeHandler className="plot" />;
  }

  // Categorical: horizontal bars, most frequent on top, so long labels stay readable.
  const labels = chart.labels.map(String);
  // Height follows the number of bars (~24px each) so 2 categories don't become slabs.
  const h = Math.max(120, 56 + labels.length * 24);
  const data = [{
    type: "bar", orientation: "h", x: chart.counts, y: labels.map(truncate), customdata: labels,
    marker: { color: SERIES, line: { color: SURFACE, width: 2 } },
    hovertemplate: `%{customdata}<br>${rows}: %{x:,}<extra></extra>`,
    // Few bars: label each with its count, so a rare class (e.g. 72 frauds) stays readable.
    ...(labels.length <= 8 && {
      text: chart.counts.map((c) => fmt(c)), textposition: "outside", cliponaxis: false,
      textfont: { size: 11, color: INK_2 },
    }),
  }];
  const layout = {
    ...baseLayout(h),
    bargap: 0.25,
    margin: { l: 8, r: 12, t: 8, b: 40 },
    xaxis: axis({ title: { text: rows } }),
    yaxis: axis({ showgrid: false, autorange: "reversed", type: "category" }),
  };
  return <Plot data={data} layout={layout} config={CONFIG_SMALL} useResizeHandler className="plot" />;
}

/** Correlation heatmap: diverging scale fixed at [-1, 1] so colours are comparable across datasets. */
export function Heatmap({ columns, matrix }) {
  const t = useLabels();
  const n = columns.length;
  const showText = n <= 12;
  const size = Math.min(860, 120 + n * (showText ? 44 : 24));
  const data = [{
    type: "heatmap", x: columns, y: columns, z: matrix,
    zmin: -1, zmax: 1, zmid: 0, colorscale: DIVERGING, xgap: 1, ygap: 1, hoverongaps: false,
    colorbar: { thickness: 10, len: 0.8, outlinewidth: 0, title: { text: "r", side: "top" }, tickvals: [-1, -0.5, 0, 0.5, 1] },
    texttemplate: showText ? "%{z:.2f}" : "", textfont: { size: 10 },
    hovertemplate: `%{y} × %{x}<br>${t("ui.chart.r")}: %{z:.3f}<extra></extra>`,
  }];
  const layout = {
    ...baseLayout(size),
    margin: { l: 8, r: 8, t: 8, b: 8 },
    xaxis: axis({ showgrid: false, linecolor: "rgba(0,0,0,0)", tickangle: n > 8 ? -45 : 0, constrain: "domain" }),
    yaxis: axis({ showgrid: false, linecolor: "rgba(0,0,0,0)", autorange: "reversed", scaleanchor: "x", constrain: "domain" }),
  };
  // Cap the width near the square's size so the colour bar sits next to the grid.
  return (
    <div style={{ maxWidth: size + 110 }}>
      <Plot data={data} layout={layout} config={CONFIG_LARGE} useResizeHandler className="plot plot-heatmap" />
    </div>
  );
}

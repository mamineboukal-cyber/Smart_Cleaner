// Charts rendered from backend chart data (the backend bins and counts, the
// browser only draws). One series per chart, so no legend: the card title
// names it. Recessive axes and hairline grids keep the bars the loudest thing.
// Colour carries meaning (see theme.js): numeric violet, categorical teal, and in a
// before/after preview grey vs violet. Counts in hovers go through fmt like everywhere else.
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import { fmt } from "../format.js";
import { useLabels } from "../LabelsContext.jsx";
import { CHART, DIVERGING } from "../theme.js";

const createPlot = createPlotlyComponent.default ?? createPlotlyComponent;
const Plot = createPlot(Plotly);

const MAX_LABEL = 22;
const TONE = { before: CHART.before, after: CHART.after };

const CONFIG_SMALL = { displaylogo: false, responsive: true, displayModeBar: false };
const CONFIG_LARGE = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["select2d", "lasso2d"] };

function baseLayout(height) {
  return {
    height,
    autosize: true,
    margin: { l: 52, r: 12, t: 8, b: 40 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: CHART.font, size: 11, color: CHART.ink2 },
    hoverlabel: { bgcolor: CHART.surface, bordercolor: CHART.axis, font: { family: CHART.font, color: CHART.ink, size: 12 } },
    bargap: 0,
    barcornerradius: 3,
    showlegend: false,
  };
}

const axis = (extra = {}) => ({
  gridcolor: CHART.grid, linecolor: CHART.axis, zeroline: false, tickcolor: CHART.axis, automargin: true,
  title: { font: { size: 11, color: CHART.ink2 }, standoff: 6, ...extra.title }, ...extra,
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
export default function Chart({ chart, height = 220, tone = "default" }) {
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
      type: "bar", x, y: counts, width, customdata: ranges.map((r, i) => [r, fmt(counts[i])]),
      marker: { color: TONE[tone] ?? CHART.numeric, line: { color: CHART.surface, width: 1 } }, // 1px gap between bins
      hovertemplate: `%{customdata[0]}<br>${rows}: %{customdata[1]}<extra></extra>`,
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
    type: "bar", orientation: "h", x: chart.counts, y: labels.map(truncate),
    customdata: labels.map((l, i) => [l, fmt(chart.counts[i])]),
    marker: { color: TONE[tone] ?? CHART.categorical, line: { color: CHART.surface, width: 2 } },
    hovertemplate: `%{customdata[0]}<br>${rows}: %{customdata[1]}<extra></extra>`,
    // Few bars: label each with its count, so a rare class (e.g. 72 frauds) stays readable.
    ...(labels.length <= 8 && {
      text: chart.counts.map((c) => fmt(c)), textposition: "outside", cliponaxis: false,
      textfont: { size: 11, color: CHART.ink2 },
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

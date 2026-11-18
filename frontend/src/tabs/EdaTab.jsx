// Step 2: exploratory analysis of the train split: dataset summary, a sortable
// statistics table, one chart per column and the correlation heatmap.
import { Fragment, useMemo, useState } from "react";
import Chart, { Heatmap } from "../components/Chart.jsx";
import { fmt, fmtInt, fmtStat } from "../format.js";
import { useLabels } from "../LabelsContext.jsx";

const STAT_COLUMNS = ["missing_pct", "n_unique", "mean", "std", "min", "max", "skewness", "outlier_pct"];

export default function EdaTab({ eda, findings, upload }) {
  const t = useLabels();
  return (
    <section className="tab-panel" aria-labelledby="eda-heading">
      <h2 id="eda-heading">{t("ui.eda.heading")}</h2>
      <p className="tab-intro">{t("ui.eda.intro")}</p>
      <DatasetSummary dataset={eda.dataset} findings={findings} upload={upload} />
      <StatsTable columns={eda.columns} />
      <Distributions columns={eda.columns} />
      <Correlation correlation={eda.correlation} />
    </section>
  );
}

export function DatasetSummary({ dataset, findings, upload }) {
  const t = useLabels();
  const imbalance = findings.find((f) => f.rule === "imbalance");
  const facts = [
    [t("ui.eda.file"), upload.filename],
    [t("ui.eda.task"), t(`ui.task.${dataset.task ?? "none"}`)],
    [t("ui.eda.split"), t(dataset.stratified ? "ui.split.stratified" : "ui.split.random")],
    [t("ui.eda.train"), fmtInt(dataset.n_train), true],
    [t("ui.eda.test"), fmtInt(dataset.n_test), true],
    [t("ui.eda.duplicates"), fmtInt(dataset.n_duplicates), true],
  ];
  if (dataset.n_target_missing) facts.push([t("ui.eda.target_missing"), fmtInt(dataset.n_target_missing), true]);
  if (imbalance) {
    facts.push([t("ui.eda.class_ratio"), fmt(imbalance.stats.ratio), true]);
    facts.push([t("ui.eda.class_counts"), imbalance.stats.class_counts]);
  }
  return (
    <div className="panel">
      <h3>{t("ui.eda.dataset")}</h3>
      <dl className="facts">
        {facts.map(([k, v, isNum]) => (
          <div key={k}><dt>{k}</dt><dd className={isNum ? "num-mono" : undefined}>{v}</dd></div>
        ))}
      </dl>
      {dataset.warnings.map((w) => <div key={w} className="alert alert-warn facts-warning" role="status">{w}</div>)}
    </div>
  );
}

function StatsTable({ columns }) {
  const t = useLabels();
  const [sort, setSort] = useState({ key: null, dir: 1 });

  const rows = useMemo(() => {
    if (!sort.key) return columns;
    const value = (c) => (sort.key === "name" ? c.name : sort.key === "type" ? c.type : c.stats[sort.key]);
    return [...columns].sort((a, b) => {
      const va = value(a), vb = value(b);
      if (va == null) return 1;   // empty values always last
      if (vb == null) return -1;
      return (typeof va === "string" ? va.localeCompare(vb) : va - vb) * sort.dir;
    });
  }, [columns, sort]);

  const header = (key, label, numeric) => {
    const active = sort.key === key;
    return (
      <th scope="col" className={numeric ? "num" : undefined}
          aria-sort={active ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
        <button type="button" className="sort-btn"
                onClick={() => setSort({ key, dir: active ? -sort.dir : numeric ? -1 : 1 })}>
          {label}<span className="sort-mark" aria-hidden="true">{active ? (sort.dir === 1 ? "▲" : "▼") : ""}</span>
        </button>
      </th>
    );
  };

  const dash = t("ui.missing_value");
  return (
    <div className="panel">
      <h3>{t("ui.eda.stats")}</h3>
      <p className="help">{t("ui.eda.stats_help")}</p>
      <div className="table-scroll stats-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {header("name", t("ui.eda.column"))}
              {header("type", t("ui.eda.type"))}
              {STAT_COLUMNS.map((k) => <Fragment key={k}>{header(k, t(`ui.stat.${k}`), true)}</Fragment>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.name} className={c.is_target ? "is-target" : undefined}>
                <th scope="row">
                  {c.name} {c.is_target && <span className="tag">{t("ui.import.target_tag")}</span>}
                </th>
                <td>{t(`ui.type.${c.type}`)}</td>
                {STAT_COLUMNS.map((k) => {
                  const v = c.stats[k];
                  const warn = k === "missing_pct" && v > 0;
                  return <td key={k} className={warn ? "num cell-warn" : "num"}>{fmtStat(k, v, dash)}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Distributions({ columns }) {
  const t = useLabels();
  return (
    <div className="panel">
      <h3>{t("ui.eda.distributions")}</h3>
      <p className="help">{t("ui.eda.distributions_help")}</p>
      <div className="chart-grid">
        {columns.map((c) => (
          <figure key={c.name} className="chart-card">
            <figcaption>
              <span className="chart-title">{c.name}</span>
              <span className="chart-meta">
                {t(`ui.type.${c.type}`)}
                {c.is_target && <span className="tag">{t("ui.import.target_tag")}</span>}
              </span>
            </figcaption>
            <Chart chart={c.chart} />
          </figure>
        ))}
      </div>
    </div>
  );
}

function Correlation({ correlation }) {
  const t = useLabels();
  return (
    <div className="panel">
      <h3>{t("ui.eda.correlation")}</h3>
      <p className="help">{t("ui.eda.correlation_help")}</p>
      {correlation.columns.length < 2
        ? <p className="empty">{t("ui.eda.no_correlation")}</p>
        : <div className="heatmap-wrap"><Heatmap columns={correlation.columns} matrix={correlation.matrix} /></div>}
    </div>
  );
}

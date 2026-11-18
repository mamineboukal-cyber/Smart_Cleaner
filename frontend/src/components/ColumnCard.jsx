// One column: key stats, a FindingRow per finding, and a before/after preview
// that runs this column's chosen steps (in pipeline order) on the train split.
import { useState } from "react";
import { preview as previewApi } from "../api.js";
import { followScaling } from "../choices.js";
import { fmt } from "../format.js";
import { errorMessage, useLabels } from "../LabelsContext.jsx";
import Chart from "./Chart.jsx";
import ErrorAlert from "./ErrorAlert.jsx";
import FindingRow from "./FindingRow.jsx";

const KEY_STATS = {
  numeric: ["missing_pct", "n_unique", "mean", "std", "min", "max", "skewness", "outlier_pct"],
  other: ["missing_pct", "n_unique", "top_freq_pct", "mean_length"],
};
const COMPARE_STATS = ["missing_pct", "n_unique", "mean", "std", "min", "max", "skewness", "outlier_pct"];

export default function ColumnCard({ sessionId, column, findings, choices, recomputed, onChoice, onScaling,
                                     result, onResult }) {
  const t = useLabels();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [afterIndex, setAfterIndex] = useState(0);

  const columnChoices = choices[column.name] ?? {};
  const choicesKey = JSON.stringify(columnChoices);
  const stale = result && result.choicesKey !== choicesKey;
  const stats = KEY_STATS[column.type === "numeric" ? "numeric" : "other"];
  const dash = t("ui.missing_value");

  async function runPreview() {
    setBusy(true);
    setError(null);
    try {
      const ask = (c) => previewApi({ session_id: sessionId, column: column.name, choices: c });
      let used = columnChoices;
      let data = await ask(used);
      if (data.scaling) {
        // App switches the scaling choice to the recomputed recommendation if the user
        // had kept the old one; preview once more so "after" really uses that scaler.
        onScaling(column.name, data.scaling);
        const followed = followScaling(findings, { [column.name]: used }, { [column.name]: data.scaling });
        if (followed.changed) {
          used = followed.choices[column.name];
          data = await ask(used);
        }
      }
      onResult({ data, choicesKey: JSON.stringify(used) });
      setAfterIndex(0);
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="column-card" aria-labelledby="column-card-title">
      <header className="column-card-head">
        <h3 id="column-card-title">{column.name}</h3>
        <span className="chart-meta">{t(`ui.type.${column.type}`)}</span>
      </header>
      <dl className="key-stats">
        {stats.map((k) => (
          <div key={k}>
            <dt>{t(`ui.stat.${k}`)}</dt>
            <dd className={k === "missing_pct" && column.stats[k] > 0 ? "is-warn" : undefined}>{fmt(column.stats[k], dash)}</dd>
          </div>
        ))}
      </dl>

      {findings.length === 0
        ? <p className="no-anomaly">{t("ui.prep.no_anomaly")}</p>
        : findings.map((f) => (
          <FindingRow key={f.rule} finding={f} chosen={columnChoices[f.rule] ?? f.recommendation}
                      recomputed={f.rule === "scaling" && recomputed}
                      onChoose={(option) => onChoice(column.name, f.rule, option)} />
        ))}

      <section className="preview" aria-labelledby="preview-title">
        <div className="preview-head">
          <div>
            <h4 id="preview-title">{t("ui.prep.preview_title")}</h4>
            <p className="help">{t("ui.prep.preview_help")}</p>
          </div>
          <button type="button" className="btn preview-btn" onClick={runPreview} disabled={busy}>
            {busy ? t("ui.prep.previewing") : t("ui.prep.preview")}
          </button>
        </div>
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
        {stale && <p className="alert alert-warn" role="status">{t("ui.prep.preview_stale")}</p>}
        {result && (
          <PreviewResult data={result.data} column={column} afterIndex={afterIndex}
                         setAfterIndex={setAfterIndex} faded={stale} />
        )}
      </section>
    </article>
  );
}

function PreviewResult({ data, column, afterIndex, setAfterIndex, faded }) {
  const t = useLabels();
  const after = data.after[afterIndex];
  const dash = t("ui.missing_value");
  const rows = COMPARE_STATS.filter((k) => data.before.stats[k] != null || after?.stats[k] != null);

  return (
    <div className={`preview-result${faded ? " is-stale" : ""}`}>
      {data.rows_dropped > 0 && <p className="alert alert-info">{t("ui.prep.rows_dropped", { n: data.rows_dropped })}</p>}
      <div className="preview-pair">
        <figure className="chart-card">
          <figcaption><span className="chart-title">{t("ui.prep.before")}</span></figcaption>
          <Chart chart={data.before.chart} />
        </figure>
        <figure className="chart-card">
          <figcaption>
            <span className="chart-title">{t("ui.prep.after")}</span>
            {data.after.length > 1 && (
              <select aria-label={t("ui.prep.after_column")} value={afterIndex}
                      onChange={(e) => setAfterIndex(Number(e.target.value))}>
                {data.after.map((a, i) => <option key={a.name} value={i}>{a.name}</option>)}
              </select>
            )}
          </figcaption>
          {after ? <Chart chart={after.chart} /> : <p className="chart-empty">{t("ui.prep.dropped")}</p>}
          {data.after.length > 1 && <p className="help">{t("ui.prep.after_many", { n: data.after.length })}</p>}
        </figure>
      </div>
      {after && (
        <div className="table-scroll">
          <table className="data-table compare-table">
            <thead>
              <tr>
                <th scope="col">{t("ui.prep.stat")}</th>
                <th scope="col" className="num">{t("ui.prep.before_short")}</th>
                <th scope="col" className="num">{t("ui.prep.after_short")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((k) => (
                <tr key={k}>
                  <th scope="row">{t(`ui.stat.${k}`)}</th>
                  <td className="num">{fmt(data.before.stats[k], dash)}</td>
                  <td className="num">{fmt(after.stats[k], dash)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

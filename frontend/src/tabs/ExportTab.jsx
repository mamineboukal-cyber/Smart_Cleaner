// Step 4: summarise the choices, apply them (fitted on train only) and download
// the zip with train.csv, test.csv and report.xlsx.
import { useState } from "react";
import { apply as applyApi, exportUrl } from "../api.js";
import { countChoices, followScaling } from "../choices.js";
import ErrorAlert from "../components/ErrorAlert.jsx";
import { fmtInt } from "../format.js";
import { errorMessage, useLabels } from "../LabelsContext.jsx";

export default function ExportTab({ sessionId, findings, choices, applied, onApplied }) {
  const t = useLabels();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const counts = countChoices(findings, choices);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      let res = await applyApi({ session_id: sessionId, choices });
      // The backend recomputes each scaling recommendation after the earlier steps.
      // Follow it where the user kept the recommendation, and apply once more, so the
      // screen and report.xlsx agree on what was recommended and what was applied.
      const followed = followScaling(findings, choices, res.scaling);
      if (followed.changed) res = await applyApi({ session_id: sessionId, choices: followed.choices });
      onApplied(res, followed.choices);
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  }

  const appliedRows = applied
    ? Object.entries(applied.applied).filter(([, steps]) => Object.keys(steps).length > 0)
    : [];

  return (
    <section className="tab-panel" aria-labelledby="export-heading">
      <h2 id="export-heading">{t("ui.export.heading")}</h2>
      <p className="alert alert-info">{t("ui.export.leakage_note")}</p>
      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="panel">
        <h3>{t("ui.export.summary")}</h3>
        <dl className="facts">
          <div><dt>{t("ui.export.recommended")}</dt><dd>{counts.recommended}</dd></div>
          <div><dt>{t("ui.export.changed")}</dt><dd>{counts.changed}</dd></div>
          <div><dt>{t("ui.export.none")}</dt><dd>{counts.none}</dd></div>
          <div><dt>{t("ui.export.dropped")}</dt><dd>{counts.dropped.length}</dd></div>
        </dl>
        {counts.dropped.length > 0 && (
          <p className="dropped-list">
            <span className="help">{t("ui.export.dropped_list")}</span>{" "}
            {counts.dropped.map((c) => <code key={c}>{c}</code>)}
          </p>
        )}
        <div className="actions export-actions">
          <button type="button" className="btn btn-primary apply-btn" onClick={run} disabled={busy}>
            {busy ? t("ui.export.applying") : t("ui.export.apply")}
          </button>
          {applied
            ? <a className="btn" href={exportUrl(sessionId)} download>{t("ui.export.download")}</a>
            : <button type="button" className="btn" disabled>{t("ui.export.download")}</button>}
          {!applied && <p className="help">{t("ui.export.apply_first")}</p>}
        </div>
      </div>

      {applied && (
        <div className="panel apply-result">
          <h3>{t("ui.export.result")}</h3>
          <dl className="facts">
            <div><dt>{t("ui.export.n_train")}</dt><dd>{fmtInt(applied.n_train)}</dd></div>
            <div><dt>{t("ui.export.n_test")}</dt><dd>{fmtInt(applied.n_test)}</dd></div>
            <div><dt>{t("ui.export.n_columns_out")}</dt><dd>{fmtInt(applied.n_columns_out)}</dd></div>
            <div><dt>{t("ui.export.rows_dropped")}</dt><dd>{fmtInt(applied.rows_dropped_train)}</dd></div>
          </dl>
          <p className="help export-contents">{t("ui.export.contents")}</p>
          {appliedRows.length > 0 && (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">{t("ui.export.column")}</th>
                    <th scope="col">{t("ui.export.steps")}</th>
                  </tr>
                </thead>
                <tbody>
                  {appliedRows.map(([column, steps]) => (
                    <tr key={column}>
                      <th scope="row">{column}</th>
                      <td className="steps-cell">
                        {Object.entries(steps).map(([rule, option]) => (
                          <span key={rule} className="step-chip">
                            {t(`ui.rule.${rule}`)}: <strong>{t(`ui.option.${option}`)}</strong>
                          </span>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

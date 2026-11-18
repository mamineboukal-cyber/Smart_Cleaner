// Step 1: upload a file, pick a sheet, the learning mode, the target and
// (optionally) correct the inferred column types, then run the analysis.
import { useState } from "react";
import { configure, getEda, getFindings, upload as uploadFile } from "../api.js";
import { fmtInt } from "../format.js";
import { errorMessage, useLabels } from "../LabelsContext.jsx";
import DropZone from "../components/DropZone.jsx";
import ErrorAlert from "../components/ErrorAlert.jsx";

const TYPES = ["numeric", "categorical", "datetime"];

export default function ImportTab({ upload, onUploaded, onAnalysed }) {
  const t = useLabels();
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(null); // "upload" | "analyse" | null
  const [error, setError] = useState(null);
  const [mode, setMode] = useState("supervised");
  const [target, setTarget] = useState("");
  const [overrides, setOverrides] = useState({});

  async function send(f, sheet) {
    setBusy("upload");
    setError(null);
    try {
      const res = await uploadFile(f, sheet);
      setTarget("");
      setOverrides({});
      onUploaded(res);
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setBusy(null);
    }
  }

  function onFile(f) {
    setFile(f);
    send(f);
  }

  async function analyse(e) {
    e.preventDefault();
    setBusy("analyse");
    setError(null);
    try {
      // Only send the types the user actually changed.
      const type_overrides = Object.fromEntries(
        Object.entries(overrides).filter(([col, typ]) => typ !== upload.types[col]));
      const config = await configure({
        session_id: upload.session_id, mode, target: mode === "supervised" ? target : null, type_overrides });
      const [eda, { findings }] = await Promise.all([getEda(upload.session_id), getFindings(upload.session_id)]);
      onAnalysed({ config, eda, findings });
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setBusy(null);
    }
  }

  const needsTarget = mode === "supervised" && !target;

  return (
    <section className="tab-panel" aria-labelledby="import-heading">
      <h2 id="import-heading">{t("ui.import.heading")}</h2>
      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <form className="import-grid" onSubmit={analyse}>
        <div className="panel import-settings">
          <DropZone onFile={onFile} disabled={busy != null}
                    file={upload && busy !== "upload" ? {
                      name: upload.filename,
                      summary: t("ui.import.summary", { rows: fmtInt(upload.n_rows), columns: fmtInt(upload.columns.length) }),
                    } : null} />
          {busy === "upload" && <p className="progress" role="status">{t("ui.import.uploading")}</p>}

          {upload?.sheets?.length > 1 && (
            <div className="field">
              <label htmlFor="sheet">{t("ui.import.sheet")}</label>
              <select id="sheet" value={upload.sheet ?? ""} disabled={busy != null}
                      onChange={(e) => send(file, e.target.value)}>
                {upload.sheets.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <p className="help">{t("ui.import.sheet_help")}</p>
            </div>
          )}

          {upload && (
            <>
              <fieldset className="field">
                <legend>{t("ui.import.mode")}</legend>
                {["supervised", "unsupervised"].map((m) => (
                  <label key={m} className="choice">
                    <input type="radio" name="mode" value={m} checked={mode === m} onChange={() => setMode(m)} />
                    <span>
                      <span className="choice-label">{t(`ui.mode.${m}`)}</span>
                      <span className="help">{t(`ui.mode.${m}_help`)}</span>
                    </span>
                  </label>
                ))}
              </fieldset>

              {mode === "supervised" && (
                <div className="field">
                  <label htmlFor="target">{t("ui.import.target")}</label>
                  <select id="target" value={target} onChange={(e) => setTarget(e.target.value)}>
                    <option value="">{t("ui.import.target_placeholder")}</option>
                    {upload.columns.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              )}

              <div className="actions">
                <button type="submit" className="btn btn-primary" disabled={busy != null || needsTarget}>
                  {busy === "analyse" ? t("ui.import.analysing") : t("ui.import.analyse")}
                </button>
                {needsTarget && <p className="help">{t("ui.import.need_target")}</p>}
              </div>
            </>
          )}
          {!upload && busy == null && <p className="empty">{t("ui.import.empty")}</p>}
        </div>

        {upload && (
          <div className="panel import-types">
            <h3>{t("ui.import.types")}</h3>
            <p className="help">{t("ui.import.types_help")}</p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">{t("ui.import.column")}</th>
                    <th scope="col">{t("ui.import.inferred")}</th>
                    <th scope="col">{t("ui.import.type")}</th>
                  </tr>
                </thead>
                <tbody>
                  {upload.columns.map((c) => {
                    const isTarget = mode === "supervised" && c === target;
                    const value = overrides[c] ?? upload.types[c];
                    return (
                      <tr key={c} className={isTarget ? "is-target" : undefined}>
                        <th scope="row">
                          {c} {isTarget && <span className="tag">{t("ui.import.target_tag")}</span>}
                        </th>
                        <td>{t(`ui.type.${upload.types[c]}`)}</td>
                        <td>
                          <select aria-label={`${t("ui.import.type")}: ${c}`} value={value}
                                  className={value !== upload.types[c] ? "changed" : undefined}
                                  onChange={(e) => setOverrides((o) => ({ ...o, [c]: e.target.value }))}>
                            {TYPES.map((typ) => <option key={typ} value={typ}>{t(`ui.type.${typ}`)}</option>)}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </form>
    </section>
  );
}

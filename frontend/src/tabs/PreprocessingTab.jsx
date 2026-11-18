// Step 3: one card per (non-target) column, chosen from an index on the left,
// plus the dataset-level findings (duplicates, class imbalance) in a banner.
import { useMemo, useState } from "react";
import ColumnCard from "../components/ColumnCard.jsx";
import { SeverityBadge } from "../components/FindingRow.jsx";
import { useLabels } from "../LabelsContext.jsx";

const SEVERITY_RANK = { info: 0, warning: 1, error: 2 };

export default function PreprocessingTab({ sessionId, eda, findings, scaling, choices, onChoice, onReset, onScaling }) {
  const t = useLabels();
  const target = eda.columns.find((c) => c.is_target)?.name ?? null;
  const columns = useMemo(() => eda.columns.filter((c) => !c.is_target), [eda]);
  const [onlyWarnings, setOnlyWarnings] = useState(false);
  const [selected, setSelected] = useState(columns[0]?.name ?? null);
  const [previews, setPreviews] = useState({}); // column -> {data, choicesKey}; survives switching columns

  const byColumn = useMemo(() => {
    const map = {};
    for (const f of findings) if (f.column != null && f.column !== target) (map[f.column] ??= []).push(f);
    return map;
  }, [findings, target]);
  const datasetFindings = findings.filter((f) => f.column == null || f.column === target);

  const summary = (name) => {
    const fs = byColumn[name] ?? [];
    const top = fs.reduce((m, f) => (SEVERITY_RANK[f.severity] > SEVERITY_RANK[m] ? f.severity : m), "info");
    const changed = fs.some((f) => (choices[name]?.[f.rule] ?? f.recommendation) !== f.recommendation);
    return { count: fs.length, top, changed };
  };

  const visible = onlyWarnings ? columns.filter((c) => summary(c.name).top !== "info") : columns;
  const current = columns.find((c) => c.name === selected) ?? columns[0];

  return (
    <section className="tab-panel" aria-labelledby="prep-heading">
      <div className="tab-head">
        <div>
          <h2 id="prep-heading">{t("ui.prep.heading")}</h2>
          <p className="tab-intro">{t("ui.prep.intro")}</p>
        </div>
        <button type="button" className="btn" onClick={onReset}>{t("ui.prep.reset")}</button>
      </div>

      {datasetFindings.length > 0 && (
        <div className="panel dataset-findings">
          <h3>{t("ui.prep.dataset_findings")}</h3>
          {datasetFindings.map((f) => (
            <div key={f.rule} className="dataset-finding">
              <div className="finding-head">
                <h4>{t(`ui.rule.${f.rule}`)}</h4>
                <SeverityBadge severity={f.severity} />
                <span className="finding-rec">{t("ui.prep.recommendation")} <strong>{t(`ui.option.${f.recommendation}`)}</strong></span>
              </div>
              <p className="finding-reason">{f.reason}</p>
            </div>
          ))}
        </div>
      )}

      <div className="prep-layout">
        <nav className="panel col-index" aria-label={t("ui.prep.columns")}>
          <div className="col-index-head">
            <h3>{t("ui.prep.columns")}</h3>
            <label className="toggle">
              <input type="checkbox" checked={onlyWarnings} onChange={(e) => setOnlyWarnings(e.target.checked)} />
              {t("ui.prep.only_warnings")}
            </label>
          </div>
          {visible.length === 0 && <p className="empty">{t("ui.prep.no_match")}</p>}
          <ul>
            {visible.map((c) => {
              const s = summary(c.name);
              return (
                <li key={c.name}>
                  <button type="button" data-column={c.name} aria-current={c.name === current?.name ? "true" : undefined}
                          onClick={() => setSelected(c.name)}>
                    <span className={`dot dot-${s.count ? s.top : "none"}`} aria-hidden="true" />
                    <span className="col-name">{c.name}</span>
                    <span className="col-meta">
                      {s.changed && <span className="tag">{t("ui.prep.changed")}</span>}
                      {s.count === 0 ? t("ui.prep.no_findings_short") : t("ui.prep.n_findings", { n: s.count })}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {current && (
          <ColumnCard key={current.name} sessionId={sessionId} column={current}
                      findings={byColumn[current.name] ?? []} choices={choices}
                      recomputed={scaling[current.name] != null} onChoice={onChoice} onScaling={onScaling}
                      result={previews[current.name] ?? null}
                      onResult={(r) => setPreviews((p) => ({ ...p, [current.name]: r }))} />
        )}
      </div>
    </section>
  );
}

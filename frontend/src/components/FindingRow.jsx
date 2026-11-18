// One finding: what was detected (with the numbers), the recommendation and
// every alternative with its trade-off. The user's choice is a radio group.
import { useLabels } from "../LabelsContext.jsx";

export function SeverityBadge({ severity }) {
  const t = useLabels();
  return <span className={`severity severity-${severity}`}>{t(`ui.severity.${severity}`)}</span>;
}

export default function FindingRow({ finding, chosen, onChoose, recomputed }) {
  const t = useLabels();
  const { column, rule, recommendation, reason, alternatives, severity } = finding;
  const name = `${column}-${rule}`;
  return (
    <section className="finding" aria-labelledby={`${name}-title`}>
      <header className="finding-head">
        <h4 id={`${name}-title`}>{t(`ui.rule.${rule}`)}</h4>
        <SeverityBadge severity={severity} />
      </header>
      <p className="finding-rec">
        {t("ui.prep.recommendation")} <strong>{t(`ui.option.${recommendation}`)}</strong>
      </p>
      <p className="finding-reason">{reason}</p>
      {recomputed && <p className="help finding-note">{t("ui.prep.scaling_updated")}</p>}

      <fieldset className="options">
        <legend className="visually-hidden">{t("ui.prep.your_choice", { rule: t(`ui.rule.${rule}`) })}</legend>
        {alternatives.map((a) => (
          <label key={a.option} className={`option${chosen === a.option ? " is-chosen" : ""}`}>
            <input type="radio" name={name} value={a.option} checked={chosen === a.option}
                   onChange={() => onChoose(a.option)} />
            <span>
              <span className="option-label">
                {t(`ui.option.${a.option}`)}
                {a.option === recommendation && <span className="tag">{t("ui.prep.recommended")}</span>}
              </span>
              <span className="help">{a.tradeoff}</span>
            </span>
          </label>
        ))}
      </fieldset>
    </section>
  );
}

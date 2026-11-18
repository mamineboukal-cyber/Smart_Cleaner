import { useLabels } from "../LabelsContext.jsx";

/** An error message from the backend (already translated), with a dismiss button. */
export default function ErrorAlert({ message, onDismiss }) {
  const t = useLabels();
  return (
    <div className="alert alert-error" role="alert">
      <div>
        <strong>{t("ui.error.title")}</strong>
        <p>{message}</p>
      </div>
      {onDismiss && (
        <button type="button" className="btn btn-quiet" onClick={onDismiss}>{t("ui.dismiss")}</button>
      )}
    </div>
  );
}

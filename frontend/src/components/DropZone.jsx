// File picker as a drop target. A <label> wraps the real (visually hidden) file input,
// so click, Enter and Space still open the native picker and screen readers still
// announce a file input. Once a file is loaded it shrinks to a file row that still
// accepts a drop. The backend validates the file type, as it does for the picker.
import { useState } from "react";
import { pickDroppedFile } from "../dropzone.js";
import { useLabels } from "../LabelsContext.jsx";

const ACCEPT = ".csv,.txt,.xlsx,.xls";

export default function DropZone({ onFile, disabled, file }) {
  const t = useLabels();
  const [dragging, setDragging] = useState(false);

  const over = (e) => {
    e.preventDefault(); // allows the drop
    if (!disabled) setDragging(true);
  };
  const leave = (e) => {
    // dragleave also fires when moving onto a child element; only clear on a real exit.
    if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
  };
  const drop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const f = pickDroppedFile(e.dataTransfer);
    if (f) onFile(f);
  };
  const pick = (e) => {
    const f = e.target.files?.[0];
    e.target.value = ""; // so picking the same file again still fires a change
    if (f) onFile(f);
  };

  const cls = ["dropzone", file && "is-compact", dragging && "is-dragging", disabled && "is-disabled"]
    .filter(Boolean).join(" ");

  return (
    <div className="field">
      <span className="field-label" id="file-label">{t("ui.import.file")}</span>
      <label htmlFor="file" className={cls} onDragEnter={over} onDragOver={over} onDragLeave={leave} onDrop={drop}>
        <input id="file" type="file" className="visually-hidden" accept={ACCEPT} disabled={disabled}
               onChange={pick} aria-labelledby="file-label" aria-describedby="file-help" />
        {file ? (
          <>
            <FileIcon />
            <span className="dropzone-file">
              <strong>{file.name}</strong>
              <span className="num-mono">{file.summary}</span>
            </span>
            <span className="dropzone-replace">{dragging ? t("ui.import.drop_release") : t("ui.import.replace")}</span>
          </>
        ) : (
          <>
            <UploadIcon />
            <strong className="dropzone-title">{dragging ? t("ui.import.drop_release") : t("ui.import.drop_title")}</strong>
            <span className="dropzone-formats">{t("ui.import.drop_formats")}</span>
            <span className="btn btn-primary dropzone-browse" aria-hidden="true">{t("ui.import.drop_browse")}</span>
          </>
        )}
      </label>
      <p className="help" id="file-help">{t("ui.import.file_help")}</p>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg className="dropzone-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none"
         stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 15V4m0 0l-4 4m4-4l4 4" />
      <path d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg className="dropzone-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none"
         stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z" />
      <path d="M14 3v5h5M9 13h6M9 17h6" />
    </svg>
  );
}

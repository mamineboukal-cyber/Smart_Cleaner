// UI labels come from the backend (GET /labels, built from backend/app/i18n.py),
// so the frontend holds no user-facing text of its own.
import { createContext, useContext } from "react";
import { NetworkError } from "./api.js";

export const LabelsContext = createContext({});

/** Returns t(key, vars): the label with {placeholders} filled in, or the key if unknown. */
export function useLabels() {
  const labels = useContext(LabelsContext);
  return (key, vars) => {
    const text = labels[key] ?? key;
    if (!vars) return text;
    return text.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m));
  };
}

/** The message to show for a failed API call. */
export function errorMessage(t, err) {
  return err instanceof NetworkError ? t("ui.error.network") : err.message;
}

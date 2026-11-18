// UI labels come from the backend (GET /labels, built from backend/app/i18n.py),
// so the frontend holds no user-facing text of its own.
import { createContext, useContext } from "react";
import { NetworkError } from "./api.js";

export const LabelsContext = createContext({});

/** The label with {placeholders} filled in, or the key if unknown. When
 * vars.n === 1 and a `${key}_one` label exists, that singular form is used
 * ("1 finding", not "1 findings"). */
export function formatLabel(labels, key, vars) {
  const singular = vars?.n === 1 ? labels[`${key}_one`] : undefined;
  const text = singular ?? labels[key] ?? key;
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m));
}

/** Returns t(key, vars), see formatLabel. */
export function useLabels() {
  const labels = useContext(LabelsContext);
  return (key, vars) => formatLabel(labels, key, vars);
}

/** The message to show for a failed API call. */
export function errorMessage(t, err) {
  return err instanceof NetworkError ? t("ui.error.network") : err.message;
}

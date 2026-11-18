import { expect, test } from "vitest";
import { formatLabel } from "./LabelsContext.jsx";

const labels = { "ui.n": "{n} findings", "ui.n_one": "{n} finding", "ui.plain": "{n} columns" };

test("formatLabel uses the _one form only when n is 1", () => {
  expect(formatLabel(labels, "ui.n", { n: 1 })).toBe("1 finding");
  expect(formatLabel(labels, "ui.n", { n: 0 })).toBe("0 findings");
  expect(formatLabel(labels, "ui.n", { n: 2 })).toBe("2 findings");
});

test("formatLabel falls back to the plural label, then to the key", () => {
  expect(formatLabel(labels, "ui.plain", { n: 1 })).toBe("1 columns");
  expect(formatLabel(labels, "ui.unknown")).toBe("ui.unknown");
});

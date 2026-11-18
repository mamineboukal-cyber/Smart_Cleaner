import { expect, test } from "vitest";
import { pickDroppedFile } from "./dropzone.js";

test("no data transfer (e.g. a synthetic event) gives no file", () => {
  expect(pickDroppedFile(null)).toBe(null);
});

test("a drag without files (selected text, a link) gives no file", () => {
  expect(pickDroppedFile({ files: [] })).toBe(null);
});

test("several files: the first one is used", () => {
  const a = { name: "a.csv" }, b = { name: "b.csv" };
  expect(pickDroppedFile({ files: [a, b] })).toBe(a);
});

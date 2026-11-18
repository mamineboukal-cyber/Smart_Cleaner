import { expect, test } from "vitest";
import { guardWindowDrop, pickDroppedFile } from "./dropzone.js";

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

// A file dropped outside the zone must not make the browser open it (and drop the session).
const fileDrag = (type) => {
  const e = new Event(type, { cancelable: true, bubbles: true });
  Object.defineProperty(e, "dataTransfer", { value: { types: ["Files"], dropEffect: "copy" } });
  return e;
};

test("guardWindowDrop blocks a stray file drop and refuses the drag cursor", () => {
  const target = new EventTarget();
  const stop = guardWindowDrop(target);
  const over = fileDrag("dragover");
  const drop = fileDrag("drop");
  target.dispatchEvent(over);
  target.dispatchEvent(drop);
  expect(over.defaultPrevented).toBe(true);
  expect(over.dataTransfer.dropEffect).toBe("none");
  expect(drop.defaultPrevented).toBe(true);
  stop();
});

test("guardWindowDrop leaves non-file drags and stops after cleanup", () => {
  const target = new EventTarget();
  const stop = guardWindowDrop(target);
  const text = new Event("drop", { cancelable: true });
  Object.defineProperty(text, "dataTransfer", { value: { types: ["text/plain"] } });
  target.dispatchEvent(text);
  expect(text.defaultPrevented).toBe(false);
  stop();
  const late = fileDrag("drop");
  target.dispatchEvent(late);
  expect(late.defaultPrevented).toBe(false);
});

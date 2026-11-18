import { expect, test } from "vitest";
import { countChoices, defaultChoices, followScaling, setChoice } from "./choices.js";

test("defaultChoices uses recommendations and skips dataset findings", () => {
  const f = [{ column: "a", rule: "missing", recommendation: "median" },
             { column: null, rule: "duplicates", recommendation: "remove" }];
  expect(defaultChoices(f)).toEqual({ a: { missing: "median" } });
});

test("setChoice is immutable", () => {
  const c = { a: { missing: "median" } };
  const n = setChoice(c, "a", "missing", "mean");
  expect(c.a.missing).toBe("median");
  expect(n.a.missing).toBe("mean");
});

test("countChoices separates recommended, changed and none, and lists dropped columns", () => {
  const f = [{ column: "a", rule: "missing", recommendation: "median" },
             { column: "b", rule: "constant", recommendation: "drop_column" },
             { column: "c", rule: "skewness", recommendation: "log1p" }];
  const c = { a: { missing: "mean" }, b: { constant: "drop_column" }, c: { skewness: "none" } };
  expect(countChoices(f, c)).toEqual({ recommended: 1, changed: 1, none: 1, dropped: ["b"] });
});

test("followScaling follows a recomputed recommendation only where the user kept the old one", () => {
  const f = [{ column: "a", rule: "scaling", recommendation: "robust" },
             { column: "b", rule: "scaling", recommendation: "robust" }];
  const c = { a: { scaling: "robust" }, b: { scaling: "minmax" } };   // b was overridden by the user
  const recomputed = { a: { recommendation: "standard" }, b: { recommendation: "standard" } };
  const { choices, changed } = followScaling(f, c, recomputed);
  expect(changed).toBe(true);
  expect(choices).toEqual({ a: { scaling: "standard" }, b: { scaling: "minmax" } });
  expect(followScaling(f, choices, { a: { recommendation: "standard" } }).changed).toBe(false);
});

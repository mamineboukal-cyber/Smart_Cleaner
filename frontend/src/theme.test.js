import { expect, test } from "vitest";
import { CHART, DIVERGING } from "./theme.js";

test("diverging scale spans 0..1 with a neutral midpoint", () => {
  expect(DIVERGING[0][0]).toBe(0);
  expect(DIVERGING.at(-1)[0]).toBe(1);
  expect(DIVERGING[2]).toEqual([0.5, "#F4F3F8"]);
});

test("diverging stops are strictly increasing", () => {
  const stops = DIVERGING.map(([s]) => s);
  stops.slice(1).forEach((s, i) => expect(s).toBeGreaterThan(stops[i]));
});

test("chart colours carry distinct meanings", () => {
  expect(CHART.numeric).not.toBe(CHART.categorical);
  expect(CHART.before).not.toBe(CHART.after);
});

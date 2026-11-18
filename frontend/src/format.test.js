import { describe, expect, test } from "vitest";
import { fmt, fmtInt, fmtPct, fmtStat } from "./format.js";

describe("fmt", () => {
  test("integers keep every digit, grouped", () => {
    expect(fmt(12480)).toBe("12,480");
    expect(fmt(123456)).toBe("123,456");
  });
  test("decimals: at most 4 significant figures", () => {
    expect(fmt(1284.5678)).toBe("1,285");
    expect(fmt(0.51234)).toBe("0.5123");
    expect(fmt(2.5)).toBe("2.5");
  });
  test("exponent only at the extremes", () => {
    expect(fmt(0.0005)).toBe("5.00e-4");
    expect(fmt(-0.00002)).toBe("-2.00e-5");
    expect(fmt(1e8)).toBe("1.00e+8");
  });
  test("noise, missing and text", () => {
    expect(fmt(1e-15)).toBe("0");
    expect(fmt(null, "—")).toBe("—");
    expect(fmt(NaN, "—")).toBe("—");
    expect(fmt("abc")).toBe("abc");
  });
});

describe("fmtPct", () => {
  test("suffix and two decimals at most", () => {
    expect(fmtPct(3.4215)).toBe("3.42%");
    expect(fmtPct(0)).toBe("0%");
    expect(fmtPct(100)).toBe("100%");
  });
  test("tiny non-zero values are not shown as 0%", () => {
    expect(fmtPct(0.004)).toBe("<0.01%");
  });
  test("missing", () => expect(fmtPct(null, "—")).toBe("—"));
});

describe("fmtStat", () => {
  test("routes by key", () => {
    expect(fmtStat("missing_pct", 3.4215)).toBe("3.42%");
    expect(fmtStat("outlier_pct", 0)).toBe("0%");
    expect(fmtStat("n_unique", 12480)).toBe("12,480");
    expect(fmtStat("mean", 0.51234)).toBe("0.5123");
    expect(fmtStat("skewness", null, "—")).toBe("—");
  });
});

test("fmtInt", () => expect(fmtInt(1234.6)).toBe("1,235"));

import { formatCompactCurrency, formatCompactHours } from "@/lib/compactNumberFormat";

describe("compactNumberFormat", () => {
  it("formats currency with German compact units", () => {
    expect(formatCompactCurrency(0)).toBe("0 €");
    expect(formatCompactCurrency(4)).toBe("4 €");
    expect(formatCompactCurrency(35_000)).toBe("35 Tsd. €");
    expect(formatCompactCurrency(2_101_000)).toBe("2,1 Mio. €");
    expect(formatCompactCurrency(-42_761_000)).toBe("-42,8 Mio. €");
    expect(formatCompactCurrency(1_250_000_000)).toBe("1,3 Mrd. €");
  });

  it("formats hours with compact units", () => {
    expect(formatCompactHours(14_200)).toBe("14,2 Tsd. h");
    expect(formatCompactHours(-32_706_666.6667)).toBe("-32,7 Mio. h");
  });

  it("promotes values that round up to the next compact unit", () => {
    expect(formatCompactCurrency(999_950)).toBe("1 Mio. €");
    expect(formatCompactCurrency(999_950_000)).toBe("1 Mrd. €");
    expect(formatCompactHours(999_950)).toBe("1 Mio. h");
  });
});

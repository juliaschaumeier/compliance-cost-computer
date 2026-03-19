import {
  isValidNullableNumberInput,
  parseNullableNumber,
  toLocalizedInputString,
} from "@/components/ea_edit/utils";

describe("ea_edit utils", () => {
  it("parses German formatted numbers", () => {
    expect(parseNullableNumber("1.234,5")).toBe(1234.5);
    expect(parseNullableNumber("1.234")).toBe(1234);
    expect(parseNullableNumber("1234,5")).toBe(1234.5);
    expect(parseNullableNumber("1,5")).toBe(1.5);
  });

  it("flags invalid or non-german numeric input", () => {
    expect(parseNullableNumber("1,234.5")).toBeNull();
    expect(parseNullableNumber("1.5")).toBeNull();
    expect(parseNullableNumber("-1")).toBeNull();
    expect(parseNullableNumber("abc")).toBeNull();
    expect(isValidNullableNumberInput("abc")).toBe(false);
    expect(isValidNullableNumberInput("1,234.5")).toBe(false);
    expect(isValidNullableNumberInput("1.5")).toBe(false);
    expect(isValidNullableNumberInput("-1")).toBe(false);
    expect(isValidNullableNumberInput("")).toBe(true);
    expect(isValidNullableNumberInput("  ")).toBe(true);
  });

  it("formats localized input strings in de-DE style", () => {
    expect(toLocalizedInputString(1.5)).toBe("1,5");
    expect(toLocalizedInputString(1234)).toBe("1234");
    expect(toLocalizedInputString(null)).toBe("");
  });
});

import { NormAddressee } from "@/types";

export type PayGradeSlot = "a" | "b" | "c" | "d" | "expenses";

export const COLUMN_LABELS_BY_ADDRESSEE: Record<
  NormAddressee,
  Record<PayGradeSlot, string>
> = {
  administration: {
    a: "eD/mD",
    b: "gD",
    c: "hD",
    d: "Ø",
    expenses: "Sach",
  },
  business: {
    a: "Niedrig",
    b: "Mittel",
    c: "Hoch",
    d: "Ø",
    expenses: "Sach",
  },
  citizens: {
    a: "Zeit",
    b: "Reserve B",
    c: "Reserve C",
    d: "Reserve D",
    expenses: "Sach",
  },
};

export function getColumnLabel(
  normAddressee: NormAddressee,
  slot: PayGradeSlot,
): string {
  return COLUMN_LABELS_BY_ADDRESSEE[normAddressee][slot];
}

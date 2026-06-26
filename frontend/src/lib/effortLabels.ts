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

const ALL_SLOTS: PayGradeSlot[] = ["a", "b", "c", "d", "expenses"];
// Citizens have no qualifications/wage rates: only slot "a" (Zeit) and expenses
// are ever populated; b/c/d are structural placeholders ("Reserve B/C/D") that
// stay empty. Hide them so the effort editor only shows the meaningful columns.
const CITIZENS_SLOTS: PayGradeSlot[] = ["a", "expenses"];

export function getVisibleSlots(normAddressee: NormAddressee): PayGradeSlot[] {
  return normAddressee === "citizens" ? CITIZENS_SLOTS : ALL_SLOTS;
}

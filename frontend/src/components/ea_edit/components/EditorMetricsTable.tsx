"use client";

import { ReactNode } from "react";

type EditorMetricsTableProps = {
  children: ReactNode;
  containerClassName?: string;
  tableClassName?: string;
};

export default function EditorMetricsTable({
  children,
  containerClassName = "max-h-[52vh] overflow-auto rounded-lg border border-slate-200",
  tableClassName = "min-w-full border-collapse text-xs",
}: EditorMetricsTableProps) {
  return (
    <div className={containerClassName}>
      <table className={tableClassName}>{children}</table>
    </div>
  );
}


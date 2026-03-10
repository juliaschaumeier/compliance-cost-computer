function isExplicitlyEnabled(value: string): boolean {
  const normalized = value.trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(normalized);
}

function isExplicitlyDisabled(value: string): boolean {
  const normalized = value.trim().toLowerCase();
  return ["0", "false", "no", "off"].includes(normalized);
}

export function isLlmConsoleEnabled(): boolean {
  const explicit = process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE;
  if (typeof explicit === "string" && explicit.trim().length > 0) {
    if (isExplicitlyEnabled(explicit)) {
      return true;
    }
    if (isExplicitlyDisabled(explicit)) {
      return false;
    }
  }
  return true;
}

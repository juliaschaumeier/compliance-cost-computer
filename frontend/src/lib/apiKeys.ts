export function hasPlausibleApiKey(value: string | null | undefined): boolean {
  return Boolean(value && value.trim().length > 10);
}

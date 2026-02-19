export function logClientError(
  scope: string,
  error: unknown,
  context?: Record<string, unknown>
): void {
  if (process.env.NODE_ENV === "production" || process.env.NODE_ENV === "test") {
    return;
  }

  const details: Record<string, unknown> = { ...(context || {}) };
  if (error instanceof Error) {
    details.message = error.message;
    details.name = error.name;
  } else if (error && typeof error === "object") {
    const maybe = error as {
      message?: unknown;
      status?: unknown;
      details?: unknown;
      raw?: unknown;
    };
    if (typeof maybe.message === "string") {
      details.message = maybe.message;
    }
    if (maybe.status !== undefined) {
      details.status = maybe.status;
    }
    if (maybe.details !== undefined) {
      details.details = maybe.details;
    }
    if (maybe.raw !== undefined) {
      details.raw = maybe.raw;
    }
  } else if (error !== undefined) {
    details.error = error;
  }

  console.debug(`[${scope}]`, details);
}

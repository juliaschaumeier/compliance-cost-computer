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

export const AUTH_EXPIRED_MESSAGE =
  "Ihre Anmeldung ist abgelaufen. Bitte melden Sie sich erneut an.";

export function isUnauthorizedApiError(error: unknown): boolean {
  return (error as { status?: unknown })?.status === 401;
}

export function formatAuthAwareFallbackMessage(
  fallbackMessage: string,
  error: unknown
): string {
  if (isUnauthorizedApiError(error)) {
    return AUTH_EXPIRED_MESSAGE;
  }
  return fallbackMessage.endsWith(".") ? fallbackMessage : `${fallbackMessage}.`;
}

export function formatActionErrorMessage(
  actionMessage: string,
  error: unknown
): string {
  const fallback = actionMessage.endsWith(".")
    ? actionMessage
    : `${actionMessage}.`;
  const maybe = error as {
    message?: unknown;
    status?: unknown;
  };
  const message =
    typeof maybe?.message === "string" ? maybe.message.trim() : "";
  const status = typeof maybe?.status === "number" ? maybe.status : undefined;
  const lower = message.toLowerCase();

  if (isUnauthorizedApiError(error)) {
    return AUTH_EXPIRED_MESSAGE;
  }

  if (lower.includes("failed to fetch")) {
    return "Backend ist nicht erreichbar. Bitte Backend prüfen und erneut versuchen.";
  }

  if (status !== undefined) {
    return `${actionMessage} (HTTP ${status}).`;
  }

  if (message && !lower.startsWith("failed to ")) {
    return `${actionMessage}: ${message}`;
  }

  return fallback;
}

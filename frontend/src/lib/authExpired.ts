export const AUTH_EXPIRED_MESSAGE =
  "Ihre Anmeldung ist abgelaufen. Bitte melden Sie sich erneut an.";

const AUTH_EXPIRED_EVENT = "ccc-auth-expired";

export function notifyAuthExpired(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
}

export function subscribeAuthExpired(callback: () => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }
  window.addEventListener(AUTH_EXPIRED_EVENT, callback);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, callback);
}

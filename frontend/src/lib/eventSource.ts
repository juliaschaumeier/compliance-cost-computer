"use client";

export function createAuthenticatedEventSource(url: string): EventSource {
  return new EventSource(url, { withCredentials: true });
}

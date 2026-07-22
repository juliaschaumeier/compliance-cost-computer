import { createAuthenticatedEventSource } from "@/lib/eventSource";

describe("createAuthenticatedEventSource", () => {
  it("includes credentials for cookie-authenticated SSE endpoints", () => {
    const eventSource = { close: jest.fn() };
    const eventSourceConstructor = jest
      .fn()
      .mockImplementation(() => eventSource);
    const originalEventSource = global.EventSource;
    global.EventSource = eventSourceConstructor as unknown as typeof EventSource;

    try {
      expect(createAuthenticatedEventSource("/events")).toBe(eventSource);
      expect(eventSourceConstructor).toHaveBeenCalledWith("/events", {
        withCredentials: true,
      });
    } finally {
      global.EventSource = originalEventSource;
    }
  });
});

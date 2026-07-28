import { apiClient } from "@/lib/api";
import { subscribeAuthExpired } from "@/lib/authExpired";

describe("apiClient.rebuildTiles", () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  it("sends the selected non-administration norm addressee", async () => {
    await apiClient.rebuildTiles("ABC123", "business");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5000/tiles/rebuild",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app_session_id: "ABC123",
          norm_addressee: "business",
        }),
      })
    );
  });

  it("also sends citizens explicitly", async () => {
    await apiClient.rebuildTiles("ABC123", "citizens");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5000/tiles/rebuild",
      expect.objectContaining({
        body: JSON.stringify({
          app_session_id: "ABC123",
          norm_addressee: "citizens",
        }),
      })
    );
  });

  it("omits administration because the backend default is administration", async () => {
    await apiClient.rebuildTiles("ABC123", "administration");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5000/tiles/rebuild",
      expect.objectContaining({
        body: JSON.stringify({
          app_session_id: "ABC123",
          norm_addressee: undefined,
        }),
      })
    );
  });
});

describe("apiClient session key forwarding", () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        app_session_id: "ABC123",
        created: true,
        case_group_research_enabled: true,
      }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  it("sends the stored Gemini key when creating a session", async () => {
    localStorage.setItem("gemini_api_key", "browser-gemini-key");

    await apiClient.createSession("gpt-5.4");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5000/sessions",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "x-gemini-key": "browser-gemini-key",
        }),
      })
    );
  });

  it("does not send an implausible stored Gemini key when creating a session", async () => {
    localStorage.setItem("gemini_api_key", "short");

    await apiClient.createSession("gpt-5.4");

    const headers = fetchMock.mock.calls[0][1].headers;
    expect(headers).toEqual(
      expect.objectContaining({
        "Content-Type": "application/json",
      })
    );
    expect(headers).not.toEqual(
      expect.objectContaining({
        "x-gemini-key": expect.any(String),
      })
    );
  });

  it("sends the stored Gemini key when loading Deep Research settings", async () => {
    localStorage.setItem("gemini_api_key", "browser-gemini-key");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        app_session_id: "ABC123",
        enabled: false,
        status: "idle",
        locked: false,
        gemini_key_available: true,
      }),
    });

    await apiClient.getCaseGroupResearchSettings("ABC123");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5000/sessions/case-group-research?app_session_id=ABC123",
      expect.objectContaining({
        headers: expect.objectContaining({
          "x-gemini-key": "browser-gemini-key",
        }),
      })
    );
  });

  it("does not send an implausible stored Gemini key when loading Deep Research settings", async () => {
    localStorage.setItem("gemini_api_key", "short");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        app_session_id: "ABC123",
        enabled: true,
        status: "idle",
        locked: false,
        gemini_key_available: true,
      }),
    });

    await apiClient.getCaseGroupResearchSettings("ABC123");

    const headers = fetchMock.mock.calls[0][1].headers;
    expect(headers).not.toEqual(
      expect.objectContaining({
        "x-gemini-key": expect.any(String),
      })
    );
  });

  it("does not send stored API keys when loading session status", async () => {
    localStorage.setItem("gemini_api_key", "browser-gemini-key");
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        summary_ready: false,
        regulations_ready: false,
        processes_ready: false,
        case_groups_ready: false,
        process_steps_ready: false,
        effort_ready: false,
        total_cost_ready: false,
      }),
    });

    await apiClient.getSessionStatus("ABC123");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:5000/sessions/status?app_session_id=ABC123",
      expect.objectContaining({
        credentials: "include",
      })
    );
    expect(fetchMock.mock.calls[0][1]).not.toEqual(
      expect.objectContaining({
        headers: expect.objectContaining({
          "x-gemini-key": "browser-gemini-key",
        }),
      })
    );
  });
});

describe("apiClient auth expiry notification", () => {
  const fetchMock = jest.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock as unknown as typeof fetch;
  });

  it("notifies auth expiry for non-bootstrap 401 responses", async () => {
    const listener = jest.fn();
    const unsubscribe = subscribeAuthExpired(listener);
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      text: async () => JSON.stringify({ detail: "Not authenticated" }),
    });

    await expect(apiClient.createSession("gpt-5.4")).rejects.toMatchObject({
      status: 401,
    });

    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it("does not notify auth expiry for failed login attempts", async () => {
    const listener = jest.fn();
    const unsubscribe = subscribeAuthExpired(listener);
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      text: async () => JSON.stringify({ detail: "Invalid credentials" }),
    });

    await expect(
      apiClient.login("ada@example.com", "wrong")
    ).rejects.toMatchObject({
      status: 401,
    });

    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("does not notify auth expiry for initial getMe 401 responses", async () => {
    const listener = jest.fn();
    const unsubscribe = subscribeAuthExpired(listener);
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      text: async () => JSON.stringify({ detail: "Not authenticated" }),
    });

    await expect(apiClient.getMe()).rejects.toMatchObject({ status: 401 });

    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });
});

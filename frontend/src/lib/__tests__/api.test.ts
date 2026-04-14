import { apiClient } from "@/lib/api";

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

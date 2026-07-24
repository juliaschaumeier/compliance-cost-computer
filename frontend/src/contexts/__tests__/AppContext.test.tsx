import { render, waitFor } from "@testing-library/react";
import React from "react";
import { renderToString } from "react-dom/server.node";

import { AppProvider, useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getSessionStatus: jest.fn(),
    createSession: jest.fn(),
    updateCaseGroupResearchSettings: jest.fn(),
  },
}));

function ContextProbe() {
  const { state } = useApp();
  return (
    <div
      data-testid="state"
      data-tab={state.currentTab}
      data-effort={state.effortReady}
      data-total={state.totalCostReady}
      data-addressee={state.selectedNormAddressee}
      data-session={state.appSessionId}
    />
  );
}

describe("AppContext session status sync", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    localStorage.setItem("selected_model", "gpt-5.4");
    (apiClient.createSession as jest.Mock).mockResolvedValue({
      app_session_id: "a".repeat(32),
      created: true,
      case_group_research_enabled: false,
    });
    (apiClient.updateCaseGroupResearchSettings as jest.Mock).mockResolvedValue({
      enabled: true,
    });
    (apiClient.getSessionStatus as jest.Mock).mockResolvedValue({
      summary_ready: true,
      regulations_ready: true,
      processes_ready: true,
      case_groups_ready: true,
      process_steps_ready: true,
      effort_ready: false,
      total_cost_ready: false,
    });
  });

  it("clamps currentTab backwards when backend is behind", async () => {
    sessionStorage.setItem("app_session_id", "ABC123");

    const { getByTestId } = render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    await waitFor(() => {
      const node = getByTestId("state");
      expect(node.getAttribute("data-effort")).toBe("false");
      expect(node.getAttribute("data-tab")).toBe("2");
    });
  });

  it("keeps the effort tab once all addressees report ready process steps", async () => {
    (apiClient.getSessionStatus as jest.Mock).mockResolvedValue({
      summary_ready: true,
      regulations_ready: true,
      processes_ready: true,
      processes_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
      case_groups_ready: true,
      case_groups_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
      process_steps_ready: true,
      process_steps_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
      effort_ready: false,
      effort_ready_by_addressee: {
        administration: false,
        business: false,
        citizens: false,
      },
      total_cost_ready: false,
      total_cost_ready_by_addressee: {
        administration: false,
        business: false,
        citizens: false,
      },
    });
    sessionStorage.setItem("app_session_id", "ABC123");

    const { getByTestId } = render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    await waitFor(() => {
      const node = getByTestId("state");
      expect(node.getAttribute("data-effort")).toBe("false");
      expect(node.getAttribute("data-tab")).toBe("5");
    });
  });

  it("uses backend by-addressee status as authoritative over stale stored readiness", async () => {
    (apiClient.getSessionStatus as jest.Mock).mockResolvedValue({
      summary_ready: true,
      regulations_ready: true,
      processes_ready: true,
      processes_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
      case_groups_ready: true,
      case_groups_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
      process_steps_ready: true,
      process_steps_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
      effort_ready: true,
      effort_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
      total_cost_ready: true,
      total_cost_ready_by_addressee: {
        administration: true,
        business: true,
        citizens: true,
      },
    });
    sessionStorage.setItem("app_session_id", "ABC123");
    sessionStorage.setItem(
      "norm_addressee_readiness",
      JSON.stringify({
        administration: { totalCostReady: false },
        business: { totalCostReady: false },
        citizens: { totalCostReady: false },
      })
    );

    const { getByTestId } = render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    await waitFor(() => {
      const node = getByTestId("state");
      expect(node.getAttribute("data-total")).toBe("true");
      expect(node.getAttribute("data-tab")).toBe("6");
    });
  });

  it("replaces a stored session id that the backend no longer owns", async () => {
    const freshSessionId = "FRESH1";
    sessionStorage.setItem("app_session_id", "STALE1");
    localStorage.setItem("gemini_api_key", "AIza-valid-test-key");
    sessionStorage.setItem(
      "norm_addressee_readiness",
      JSON.stringify({
        administration: { totalCostReady: true },
        business: { totalCostReady: true },
        citizens: { totalCostReady: true },
      })
    );
    (apiClient.createSession as jest.Mock).mockResolvedValue({
      app_session_id: freshSessionId,
      created: true,
    });
    (apiClient.getSessionStatus as jest.Mock)
      .mockRejectedValueOnce({ status: 404 })
      .mockResolvedValue({
        summary_ready: false,
        regulations_ready: false,
        processes_ready: false,
        case_groups_ready: false,
        process_steps_ready: false,
        effort_ready: false,
        total_cost_ready: false,
      });

    const { getByTestId } = render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    await waitFor(() => {
      expect(apiClient.createSession).toHaveBeenCalledWith("gpt-5.4");
      expect(getByTestId("state").getAttribute("data-session")).toBe(
        freshSessionId
      );
    });
    expect(sessionStorage.getItem("app_session_id")).toBe(freshSessionId);
    expect(sessionStorage.getItem("norm_addressee_readiness")).not.toContain(
      "true"
    );
  });

  it("adopts a frontend-created session with Deep Research enabled", async () => {
    const freshSessionId = "FRONT1";
    (apiClient.createSession as jest.Mock).mockResolvedValue({
      app_session_id: freshSessionId,
      created: true,
      case_group_research_enabled: true,
    });

    const { getByTestId } = render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    await waitFor(() => {
      expect(getByTestId("state").getAttribute("data-session")).toBe(
        freshSessionId
      );
    });
    expect(apiClient.updateCaseGroupResearchSettings).not.toHaveBeenCalled();
  });

  it("does not update Deep Research settings after creating a disabled session", async () => {
    const freshSessionId = "FRONT2";
    (apiClient.createSession as jest.Mock).mockResolvedValue({
      app_session_id: freshSessionId,
      created: true,
      case_group_research_enabled: false,
    });

    const { getByTestId } = render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    await waitFor(() => {
      expect(getByTestId("state").getAttribute("data-session")).toBe(
        freshSessionId
      );
    });
    expect(apiClient.updateCaseGroupResearchSettings).not.toHaveBeenCalled();
  });

  it("restores the selected norm addressee from session storage", async () => {
    sessionStorage.setItem("app_session_id", "ABC123");
    sessionStorage.setItem("selected_norm_addressee", "citizens");

    const { getByTestId } = render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    await waitFor(() => {
      const node = getByTestId("state");
      expect(node.getAttribute("data-addressee")).toBe("citizens");
    });
  });

  it("keeps server-rendered norm addressee deterministic for hydration", () => {
    sessionStorage.setItem("selected_norm_addressee", "citizens");

    const html = renderToString(
      <AppProvider>
        <ContextProbe />
      </AppProvider>
    );

    expect(html).toContain('data-addressee="administration"');
  });
});

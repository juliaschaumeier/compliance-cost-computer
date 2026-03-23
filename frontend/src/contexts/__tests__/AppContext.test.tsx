import { render, waitFor } from "@testing-library/react";
import React from "react";

import { AppProvider, useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getSessionStatus: jest.fn(),
    upsertSession: jest.fn(),
  },
}));

function ContextProbe() {
  const { state } = useApp();
  return (
    <div data-testid="state" data-tab={state.currentTab} data-effort={state.effortReady} />
  );
}

describe("AppContext session status sync", () => {
  beforeEach(() => {
    sessionStorage.clear();
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
    sessionStorage.setItem("effort_ready", "true");

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
});

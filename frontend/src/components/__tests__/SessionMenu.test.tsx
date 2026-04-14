import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SessionMenu from "@/components/SessionMenu";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/api", () => ({
  apiClient: {
    rebuildTiles: jest.fn(),
    listSessions: jest.fn(),
    getSessionStatus: jest.fn(),
    undoLastStep: jest.fn(),
    exportSession: jest.fn(),
    startRunAllSteps: jest.fn(),
    cancelRunAll: jest.fn(),
    getRunAllStatus: jest.fn(),
    getRunAllEventsUrl: jest.fn(() => "/events"),
  },
  buildLlmRequestOptions: jest.fn(() => ({
    model: undefined,
    provider: undefined,
    keys: {},
  })),
}));

const mockUseApp = useApp as jest.Mock;
const mockRebuildTiles = apiClient.rebuildTiles as jest.Mock;
const mockListSessions = apiClient.listSessions as jest.Mock;
const mockGetSessionStatus = apiClient.getSessionStatus as jest.Mock;
const mockUndoLastStep = apiClient.undoLastStep as jest.Mock;

describe("SessionMenu", () => {
  const setCurrentTab = jest.fn();
  const setAppSessionId = jest.fn();
  const setSummaryReady = jest.fn();
  const setRegulationsReady = jest.fn();
  const setLastCompletedStep = jest.fn();
  const setLastCompletedLabel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "ABC123",
        selectedNormAddressee: "business",
        selectedModel: "gpt-5.4",
        availableModels: [],
        selectedCurrentLaw: "",
        selectedRegulation: "",
        summaryReady: true,
        regulationsReady: true,
        processesReady: true,
        caseGroupsReady: true,
        processStepsReady: true,
        effortReady: false,
        totalCostReady: false,
        lastCompletedStep: "effort",
        lastCompletedLabel: "Aufwand berechnen",
      },
      setCurrentTab,
      setAppSessionId,
      setSummaryReady,
      setRegulationsReady,
      setLastCompletedStep,
      setLastCompletedLabel,
    });
    mockRebuildTiles.mockResolvedValue({ ok: true });
    mockListSessions.mockResolvedValue({
      sessions: [
        {
          app_session_id: "XYZ789",
          created_at: "2026-04-14T09:00:00Z",
          llm_model: "gpt-5.4",
          used_llm_models: "gpt-5.4",
        },
      ],
    });
    mockGetSessionStatus.mockResolvedValue({
      summary_ready: true,
      regulations_ready: true,
      processes_ready: true,
      case_groups_ready: true,
      process_steps_ready: true,
      effort_ready: true,
      total_cost_ready: false,
      last_completed_step: "effort",
      last_completed_label: "Aufwand berechnen",
    });
    mockUndoLastStep.mockResolvedValue({
      status: "ok",
      undone_step: "effort",
      undone_label: "Aufwand berechnen",
    });
  });

  async function openMenu() {
    const user = userEvent.setup();
    render(<SessionMenu />);
    await user.click(screen.getByTitle("Session Aktionen"));
    await screen.findByText("Session Aktionen");
    return user;
  }

  it("rebuilds the currently selected norm addressee", async () => {
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", {
        name: /kacheln dieser session neu laden/i,
      })
    );

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("ABC123", "business")
    );
  });

  it("rebuilds the selected norm addressee after loading another session", async () => {
    const user = await openMenu();

    await waitFor(() => expect(mockListSessions).toHaveBeenCalled());
    await user.selectOptions(screen.getByRole("combobox"), "XYZ789");
    await user.click(screen.getByRole("button", { name: /wechseln/i }));

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("XYZ789", "business")
    );
    expect(setAppSessionId).toHaveBeenCalledWith("XYZ789");
  });

  it("rebuilds the selected norm addressee after undo", async () => {
    const user = await openMenu();

    await user.click(
      screen.getByRole("button", {
        name: /aufwand berechnen/i,
      })
    );

    await waitFor(() =>
      expect(mockRebuildTiles).toHaveBeenCalledWith("ABC123", "business")
    );
    expect(mockUndoLastStep).toHaveBeenCalledWith("ABC123", "business");
  });
});

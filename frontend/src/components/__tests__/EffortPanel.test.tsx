"use client";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EffortPanel from "@/components/EffortPanel";
import { apiClient } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

jest.mock("@/lib/api", () => ({
  apiClient: {
    calculateEffort: jest.fn(),
  },
  buildLlmRequestOptions: ({
    selectedModel,
    availableModels,
  }: {
    selectedModel: string;
    availableModels: Array<{ id: string; provider: string }>;
  }) => {
    const selectedModelData = availableModels.find(
      (model) => model.id === selectedModel
    );
    return {
      model: selectedModel || undefined,
      provider: selectedModelData?.provider?.toLowerCase(),
      keys: {
        openaiApiKey: localStorage.getItem("openai_api_key") || undefined,
        deepinfraApiKey: localStorage.getItem("deepinfra_api_key") || undefined,
        geminiApiKey: localStorage.getItem("gemini_api_key") || undefined,
      },
    };
  },
}));

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

const mockUseApp = useApp as jest.Mock;
const mockCalculateEffort = apiClient.calculateEffort as jest.Mock;

const baseState = {
  currentTab: 5,
  appSessionId: "ABC123",
  selectedNormAddressee: "business",
  selectedModel: "gpt-5",
  availableModels: [
    { id: "gpt-5", name: "GPT-5", provider: "OpenAI" },
  ],
  selectedCurrentLaw: "",
  selectedRegulation: "",
  availableRegulations: [],
  summaryReady: true,
  regulationsReady: true,
  processesReady: true,
  caseGroupsReady: true,
  processStepsReady: true,
  effortReady: false,
  totalCostReady: false,
};

describe("EffortPanel", () => {
  beforeEach(() => {
    mockCalculateEffort.mockReset();
    localStorage.clear();
  });

  it("disables the button when process steps are not ready", () => {
    mockUseApp.mockReturnValue({
      state: { ...baseState, processStepsReady: false },
      setCurrentTab: jest.fn(),
      setEffortReady: jest.fn(),
    });

    render(<EffortPanel />);

    const button = screen.getByRole("button", { name: /Aufwand berechnen/i });
    expect(button).toBeDisabled();
  });

  it("calls the API and advances the tab on success", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab,
      setEffortReady,
    });
    localStorage.setItem("openai_api_key", "sk-test");
    mockCalculateEffort.mockResolvedValue({ case_groups_updated: 1, steps_updated: 1 });

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Aufwand berechnen/i }));

    await waitFor(() => {
      expect(mockCalculateEffort).toHaveBeenCalledTimes(3);
    });
    expect(mockCalculateEffort).toHaveBeenNthCalledWith(1, {
      appSessionId: "ABC123",
      normAddressee: "administration",
      model: "gpt-5",
      provider: "openai",
      keys: {
        openaiApiKey: "sk-test",
        deepinfraApiKey: undefined,
        geminiApiKey: undefined,
      },
    });
    expect(mockCalculateEffort).toHaveBeenNthCalledWith(2, {
      appSessionId: "ABC123",
      normAddressee: "business",
      model: "gpt-5",
      provider: "openai",
      keys: {
        openaiApiKey: "sk-test",
        deepinfraApiKey: undefined,
        geminiApiKey: undefined,
      },
    });
    expect(mockCalculateEffort).toHaveBeenNthCalledWith(3, {
      appSessionId: "ABC123",
      normAddressee: "citizens",
      model: "gpt-5",
      provider: "openai",
      keys: {
        openaiApiKey: "sk-test",
        deepinfraApiKey: undefined,
        geminiApiKey: undefined,
      },
    });
    expect(setCurrentTab).toHaveBeenCalledWith(6);
    expect(setEffortReady).toHaveBeenCalledWith(true);
  });

  it("shows an error when the API fails", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab,
      setEffortReady,
    });
    mockCalculateEffort.mockRejectedValue(new Error("boom"));

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Aufwand berechnen/i }));

    expect(
      await screen.findByText("Aufwand konnte nicht berechnet werden: boom")
    ).toBeInTheDocument();
    expect(setCurrentTab).not.toHaveBeenCalled();
  });

  it("handles already computed effort without re-running", async () => {
    const setCurrentTab = jest.fn();
    const setEffortReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab,
      setEffortReady,
    });
    mockCalculateEffort.mockResolvedValue({
      status: "existing",
      case_groups_updated: 0,
      steps_updated: 0,
    });

    render(<EffortPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Aufwand berechnen/i }));

    expect(
      await screen.findByText(
        "Aufwand fuer Verwaltung, Wirtschaft und Buerger wurde bereits berechnet."
      )
    ).toBeInTheDocument();
    expect(mockCalculateEffort).toHaveBeenCalledTimes(3);
    expect(setEffortReady).toHaveBeenCalledWith(true);
    expect(setCurrentTab).toHaveBeenCalledWith(6);
  });
});

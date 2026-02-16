"use client";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import TotalCostPanel from "@/components/TotalCostPanel";
import { apiClient } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

jest.mock("@/lib/api", () => ({
  apiClient: {
    computeTotalCost: jest.fn(),
  },
}));

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

const mockUseApp = useApp as jest.Mock;
const mockComputeTotalCost = apiClient.computeTotalCost as jest.Mock;

const baseState = {
  currentTab: 6,
  appSessionId: "ABC123",
  selectedModel: "gpt-5",
  availableModels: [{ id: "gpt-5", name: "GPT-5", provider: "OpenAI" }],
  selectedCurrentLaw: "",
  selectedRegulation: "",
  availableRegulations: [],
  summaryReady: true,
  regulationsReady: true,
  processesReady: true,
  caseGroupsReady: true,
  processStepsReady: true,
  effortReady: true,
  totalCostReady: false,
};

describe("TotalCostPanel", () => {
  beforeEach(() => {
    mockComputeTotalCost.mockReset();
  });

  it("disables the button when process steps are not ready", () => {
    mockUseApp.mockReturnValue({
      state: { ...baseState, processStepsReady: false },
      setCurrentTab: jest.fn(),
    });

    render(<TotalCostPanel />);

    const button = screen.getByRole("button", {
      name: /Gesamtkosten berechnen/i,
    });
    expect(button).toBeDisabled();
  });

  it("shows an error when the API fails", async () => {
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab: jest.fn(),
    });
    mockComputeTotalCost.mockRejectedValue(new Error("boom"));

    render(<TotalCostPanel />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: /Gesamtkosten berechnen/i })
    );

    expect(
      await screen.findByText("Gesamtkosten konnten nicht berechnet werden.")
    ).toBeInTheDocument();
  });

  it("disables the button when totals are already computed", () => {
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
    });

    render(<TotalCostPanel />);

    const button = screen.getByRole("button", {
      name: /Bereits berechnet/i,
    });
    expect(button).toBeDisabled();
  });
});

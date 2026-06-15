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
  selectedNormAddressee: "citizens",
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
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    const button = screen.getByRole("button", {
      name: /Ausführen/i,
    });
    expect(button).toBeDisabled();
  });

  it("shows a per-addressee error status when every API call fails", async () => {
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });
    mockComputeTotalCost.mockRejectedValue(new Error("boom"));

    render(<TotalCostPanel />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: /Ausführen/i })
    );

    expect(
      await screen.findByText(
        /Gesamtkosten konnten fuer keinen Normadressaten berechnet werden.*Verwaltung.*Wirtschaft.*Buerger/
      )
    ).toBeInTheDocument();
  });

  it("reports partial success when only some addressees fail", async () => {
    const setTotalCostReady = jest.fn();
    mockUseApp.mockReturnValue({
      state: baseState,
      setCurrentTab: jest.fn(),
      setTotalCostReady,
    });
    // administration + business succeed, citizens fails
    mockComputeTotalCost.mockImplementation(
      ({ normAddressee }: { normAddressee: string }) => {
        if (normAddressee === "citizens") {
          return Promise.reject(new Error("boom-citizens"));
        }
        return Promise.resolve({
          total_cost: normAddressee === "administration" ? 100 : 200,
        });
      }
    );

    render(<TotalCostPanel />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: /Ausführen/i })
    );

    expect(
      await screen.findByText(/Teilweise berechnet.*Verwaltung.*Wirtschaft.*Buerger.*Fehler/)
    ).toBeInTheDocument();
    // totalCostReady darf bei Teilfehler NICHT auf true gesetzt werden,
    // damit der Nutzer den fehlenden NA nachziehen kann.
    expect(setTotalCostReady).not.toHaveBeenCalledWith(true);
  });

  it("disables the button when totals are already computed", () => {
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    const button = screen.getByRole("button", {
      name: /Alles berechnet/i,
    });
    expect(button).toBeDisabled();
  });
});

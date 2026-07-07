"use client";

import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import TotalCostPanel from "@/components/TotalCostPanel";
import { apiClient } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

jest.mock("@/lib/api", () => ({
  apiClient: {
    computeTotalCost: jest.fn(),
    getTotalCostSummary: jest.fn(),
  },
}));

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

const mockUseApp = useApp as jest.Mock;
const mockComputeTotalCost = apiClient.computeTotalCost as jest.Mock;
const mockGetTotalCostSummary = apiClient.getTotalCostSummary as jest.Mock;

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
    mockGetTotalCostSummary.mockReset();
    mockGetTotalCostSummary.mockResolvedValue({});
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
        /Gesamtkosten konnten für keinen Normadressaten berechnet werden.*Verwaltung.*Wirtschaft.*Bürger/
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
      await screen.findByText(/Teilweise berechnet.*Verwaltung.*Wirtschaft.*Bürger.*Fehler/)
    ).toBeInTheDocument();
    // totalCostReady darf bei Teilfehler NICHT auf true gesetzt werden,
    // damit der Nutzer den fehlenden NA nachziehen kann.
    expect(setTotalCostReady).not.toHaveBeenCalledWith(true);
  });

  it("replaces the run controls with a compact cost summary after all totals are computed", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
        administration: { norm_addressee: "administration", total_cost: 320000 },
        business: { norm_addressee: "business", total_cost: 920000 },
        citizens: {
          norm_addressee: "citizens",
          total_cost: null,
          total_time_hours: 14200,
          total_expenses: 35000,
        },
      });
    mockComputeTotalCost.mockImplementation(
      ({ normAddressee }: { normAddressee: string }) => {
        if (normAddressee === "citizens") {
          return Promise.resolve({
            total_cost: null,
            total_time_hours: 14200,
            total_expenses: 35000,
          });
        }
        return Promise.resolve({
          total_cost: normAddressee === "administration" ? 320000 : 920000,
        });
      }
    );

    let currentState = baseState;
    const setTotalCostReady = jest.fn((ready: boolean) => {
      currentState = { ...currentState, totalCostReady: ready };
      mockUseApp.mockReturnValue({
        state: currentState,
        setCurrentTab: jest.fn(),
        setTotalCostReady,
      });
    });
    mockUseApp.mockReturnValue({
      state: currentState,
      setCurrentTab: jest.fn(),
      setTotalCostReady,
    });

    const { rerender } = render(<TotalCostPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));
    await waitFor(() => expect(setTotalCostReady).toHaveBeenCalledWith(true));
    rerender(<TotalCostPanel />);

    expect(
      await screen.findByLabelText(
        /Kostenübersicht: Gesamt 1,2 Mio. €.*Bürger:innen 14,2 Tsd. h · 35 Tsd. €.*Wirtschaft 920 Tsd. €.*Verwaltung 320 Tsd. €/i
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Jährlicher")).toBeInTheDocument();
    expect(screen.getByText("Aufwand")).toBeInTheDocument();
    expect(screen.getByText("14,2 Tsd. h · 35 Tsd. €")).toBeInTheDocument();
    expect(
      screen.queryByText(/Kosten fuer Verwaltung, Wirtschaft und Buerger berechnet/)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Alles berechnet/i })
    ).not.toBeInTheDocument();

    await act(async () => {
      window.dispatchEvent(new Event("tiles-updated"));
    });

    expect(
      screen.getByLabelText(/Kostenübersicht: Gesamt 1,2 Mio. €/i)
    ).toBeInTheDocument();
  });

  it("does not keep a hidden success message after total costs are rolled back", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 320000 },
      business: { norm_addressee: "business", total_cost: 920000 },
      citizens: {
        norm_addressee: "citizens",
        total_cost: null,
        total_time_hours: 14200,
        total_expenses: 35000,
      },
    });
    mockComputeTotalCost.mockImplementation(
      ({ normAddressee }: { normAddressee: string }) => {
        if (normAddressee === "citizens") {
          return Promise.resolve({
            total_cost: null,
            total_time_hours: 14200,
            total_expenses: 35000,
          });
        }
        return Promise.resolve({
          total_cost: normAddressee === "administration" ? 320000 : 920000,
        });
      }
    );

    let currentState = baseState;
    const setTotalCostReady = jest.fn((ready: boolean) => {
      currentState = { ...currentState, totalCostReady: ready };
      mockUseApp.mockReturnValue({
        state: currentState,
        setCurrentTab: jest.fn(),
        setTotalCostReady,
      });
    });
    mockUseApp.mockReturnValue({
      state: currentState,
      setCurrentTab: jest.fn(),
      setTotalCostReady,
    });

    const { rerender } = render(<TotalCostPanel />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /Ausführen/i }));
    await waitFor(() => expect(setTotalCostReady).toHaveBeenCalledWith(true));
    rerender(<TotalCostPanel />);

    expect(screen.queryByText(/Kosten fuer Verwaltung/)).not.toBeInTheDocument();

    currentState = { ...currentState, totalCostReady: false };
    mockUseApp.mockReturnValue({
      state: currentState,
      setCurrentTab: jest.fn(),
      setTotalCostReady,
    });
    rerender(<TotalCostPanel />);

    expect(screen.getByRole("button", { name: /Ausführen/i })).toBeInTheDocument();
    expect(screen.queryByText(/Kosten fuer Verwaltung/)).not.toBeInTheDocument();
  });

  it("loads the compact cost summary when totals are already computed", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 320000 },
      business: { norm_addressee: "business", total_cost: 920000 },
      citizens: {
        norm_addressee: "citizens",
        total_cost: null,
        total_time_hours: 14200,
        total_expenses: 35000,
      },
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    expect(
      await screen.findByLabelText(/Kostenübersicht: Gesamt 1,2 Mio. €/i)
    ).toBeInTheDocument();
    expect(mockGetTotalCostSummary).toHaveBeenCalledWith("ABC123");
  });

  it("shows the business bureaucracy cost as an inline 'davon IP' segment", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 320000 },
      business: {
        norm_addressee: "business",
        total_cost: 920000,
        bureaucracy_cost: 40000,
      },
      citizens: {
        norm_addressee: "citizens",
        total_cost: null,
        total_time_hours: 14200,
        total_expenses: 35000,
      },
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    expect(
      await screen.findByText(/920 Tsd\. € · davon IP 40 Tsd\. €/)
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Wirtschaft 920 Tsd\. € · davon IP 40 Tsd\. €/i)
    ).toBeInTheDocument();
  });

  it("compacts very large citizen hours in the cost summary", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: null },
      business: { norm_addressee: "business", total_cost: 8542000 },
      citizens: {
        norm_addressee: "citizens",
        total_cost: null,
        total_time_hours: 13450127,
        total_expenses: 2101000,
      },
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    expect(await screen.findByText("13,5 Mio. h · 2,1 Mio. €")).toBeInTheDocument();
    expect(screen.getByText("0 €")).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Kostenübersicht: Gesamt 8,5 Mio. €.*Verwaltung 0 €/i)
    ).toBeInTheDocument();
  });

  it("uses a fixed-gap flex group for norm addressee cost columns", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: -1655330000 },
      business: { norm_addressee: "business", total_cost: -96755000 },
      citizens: {
        norm_addressee: "citizens",
        total_cost: null,
        total_time_hours: -32700000,
        total_expenses: 0,
      },
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    const group = await screen.findByTestId("cost-summary-addressee-group");
    expect(group).toHaveClass("flex");
    expect(group).toHaveClass("gap-10");
    expect(screen.getByText("-32,7 Mio. h · 0 €")).toHaveClass("whitespace-nowrap");
    expect(screen.getByText("-96,8 Mio. € · davon IP 0 €")).toHaveClass(
      "whitespace-nowrap"
    );
  });

  it("shows zero citizen effort instead of unavailable when citizen totals are empty", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 1000 },
      business: { norm_addressee: "business", total_cost: 2000 },
      citizens: {
        norm_addressee: "citizens",
        total_cost: null,
        total_time_hours: null,
        total_expenses: null,
      },
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    expect(await screen.findByText("0 h · 0 €")).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Kostenübersicht: Gesamt 3 Tsd. €.*Bürger:innen 0 h · 0 €/i)
    ).toBeInTheDocument();
  });

  it("does not invent a zero citizen total when a completed summary is missing the citizen row", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 5793.68 },
      business: { norm_addressee: "business", total_cost: 42606.82 },
      citizens: null,
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    expect(
      await screen.findByText(/Kostenübersicht ist unvollständig/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText(/Kostenübersicht:/i)
    ).not.toBeInTheDocument();
    expect(screen.queryByText("0 h · 0 €")).not.toBeInTheDocument();
  });

  it("clears the incomplete-summary warning when total costs are reset", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 5793.68 },
      business: { norm_addressee: "business", total_cost: 42606.82 },
      citizens: null,
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    const { rerender } = render(<TotalCostPanel />);

    expect(
      await screen.findByText(/Kostenübersicht ist unvollständig/i)
    ).toBeInTheDocument();

    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: false },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });
    rerender(<TotalCostPanel />);

    expect(
      screen.queryByText(/Kostenübersicht ist unvollständig/i)
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ausführen/i })).toBeInTheDocument();
  });

  it("ignores an in-flight incomplete summary after total costs are reset", async () => {
    let resolveSummary: (
      value: Awaited<ReturnType<typeof apiClient.getTotalCostSummary>>
    ) => void = () => {};
    mockGetTotalCostSummary.mockReturnValue(
      new Promise((resolve) => {
        resolveSummary = resolve;
      })
    );
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: true },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    const { rerender } = render(<TotalCostPanel />);

    await waitFor(() =>
      expect(mockGetTotalCostSummary).toHaveBeenCalledWith("ABC123")
    );

    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: false },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });
    rerender(<TotalCostPanel />);

    await act(async () => {
      resolveSummary({
        administration: { norm_addressee: "administration", total_cost: 5793.68 },
        business: { norm_addressee: "business", total_cost: 42606.82 },
        citizens: null,
      });
    });

    expect(
      screen.queryByText(/Kostenübersicht ist unvollständig/i)
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ausführen/i })).toBeInTheDocument();
  });

  it("does not load or show persisted totals before the total-cost step is ready", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 320000 },
      business: { norm_addressee: "business", total_cost: 920000 },
      citizens: {
        norm_addressee: "citizens",
        total_cost: null,
        total_time_hours: 14200,
        total_expenses: 35000,
      },
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: false },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    expect(mockGetTotalCostSummary).not.toHaveBeenCalled();
    expect(
      screen.queryByLabelText(/Kostenübersicht:/i)
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ausführen/i })).toBeInTheDocument();
  });

  it("keeps the run controls visible for a partial persisted cost summary", async () => {
    mockGetTotalCostSummary.mockResolvedValue({
      administration: { norm_addressee: "administration", total_cost: 320000 },
      business: { norm_addressee: "business", total_cost: 920000 },
    });
    mockUseApp.mockReturnValue({
      state: { ...baseState, totalCostReady: false },
      setCurrentTab: jest.fn(),
      setTotalCostReady: jest.fn(),
    });

    render(<TotalCostPanel />);

    expect(mockGetTotalCostSummary).not.toHaveBeenCalled();
    expect(
      screen.queryByLabelText(/Kostenübersicht:/i)
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Ausführen/i })
    ).toBeInTheDocument();
  });

  it("disables the button when totals are already computed but no summary is loaded", async () => {
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
    await waitFor(() =>
      expect(mockGetTotalCostSummary).toHaveBeenCalledWith("ABC123")
    );
    expect(
      await screen.findByText(/Kostenübersicht ist unvollständig/i)
    ).toBeInTheDocument();
  });
});

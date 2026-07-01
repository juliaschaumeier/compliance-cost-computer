import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EaEditDrawerShell from "@/components/ea_edit/EaEditDrawerShell";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/useMounted", () => ({
  useMounted: () => true,
}));

jest.mock("@/lib/api", () => ({
  apiClient: {
    acquireEaEditActivity: jest.fn(),
    heartbeatEaEditActivity: jest.fn(),
    releaseEaEditActivity: jest.fn(),
    computeTotalCost: jest.fn(),
    getSessionWageRates: jest.fn(),
    updateSessionWageRate: jest.fn(),
    getEditableCaseGroups: jest.fn(),
    getEditableProcessSteps: jest.fn(),
  },
}));

const mockUseApp = useApp as jest.Mock;
const mockAcquireEaEditActivity = apiClient.acquireEaEditActivity as jest.Mock;
const mockHeartbeatEaEditActivity = apiClient.heartbeatEaEditActivity as jest.Mock;
const mockReleaseEaEditActivity = apiClient.releaseEaEditActivity as jest.Mock;
const mockGetSessionWageRates = apiClient.getSessionWageRates as jest.Mock;
const mockUpdateSessionWageRate = apiClient.updateSessionWageRate as jest.Mock;
const mockComputeTotalCost = apiClient.computeTotalCost as jest.Mock;

const ADMIN_WAGE_ROWS = [
  { wage_source_kind: "verwaltungsebene", wage_source_value: "bund", qualification: "einfacher_und_mittlerer_dienst", model_hourly_rate: 42, hourly_rate_edited: null },
  { wage_source_kind: "verwaltungsebene", wage_source_value: "bund", qualification: "gehobener_dienst", model_hourly_rate: 52, hourly_rate_edited: null },
  { wage_source_kind: "verwaltungsebene", wage_source_value: "bund", qualification: "hoeherer_dienst", model_hourly_rate: 62, hourly_rate_edited: null },
  { wage_source_kind: "verwaltungsebene", wage_source_value: "bund", qualification: "durchschnitt", model_hourly_rate: 57, hourly_rate_edited: null },
];

describe("EaEditDrawerShell integration", () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "EA-INTEGRATION",
        selectedNormAddressee: "administration",
        totalCostReady: true,
      },
    });
    mockGetSessionWageRates.mockResolvedValue({
      app_session_id: "EA-INTEGRATION",
      rows: ADMIN_WAGE_ROWS,
    });
    mockAcquireEaEditActivity.mockResolvedValue({
      app_session_id: "EA-INTEGRATION",
      activity_id: "ea_edit:integration",
      lease_seconds: 120,
      expires_at: 123,
    });
    mockHeartbeatEaEditActivity.mockResolvedValue({
      app_session_id: "EA-INTEGRATION",
      activity_id: "ea_edit:integration",
      lease_seconds: 120,
      expires_at: 456,
    });
    mockReleaseEaEditActivity.mockResolvedValue({ ok: true });
  });

  it("opens close guard after real pay-rate edit", async () => {
    render(<EaEditDrawerShell open onClose={jest.fn()} />);
    const user = userEvent.setup();

    const row = await screen.findByText(/einfacher\/mittlerer dienst/i);
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const firstOverrideInput = within(tr as HTMLElement).getByRole("textbox");
    await user.type(firstOverrideInput, "55,5");

    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    expect(
      await screen.findByRole("dialog", { name: /ungespeicherte änderungen/i })
    ).toBeInTheDocument();
  });

  it("recomputes the SELECTED addressee (business) after a business pay-rate save", async () => {
    // Regression: auto-recompute used to always run for administration
    // (norm_addressee was missing from the request), so a business-tab override
    // never updated the business total.
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "EA-INTEGRATION",
        selectedNormAddressee: "business",
        totalCostReady: true,
      },
    });
    const businessRows = [
      { wage_source_kind: "wirtschaftsabschnitt", wage_source_value: "K", qualification: "niedrig", model_hourly_rate: 29, hourly_rate_edited: null },
      { wage_source_kind: "wirtschaftsabschnitt", wage_source_value: "K", qualification: "mittel", model_hourly_rate: 54.4, hourly_rate_edited: null },
      { wage_source_kind: "wirtschaftsabschnitt", wage_source_value: "K", qualification: "hoch", model_hourly_rate: 93.1, hourly_rate_edited: null },
      { wage_source_kind: "wirtschaftsabschnitt", wage_source_value: "K", qualification: "durchschnitt", model_hourly_rate: 57.9, hourly_rate_edited: null },
    ];
    mockGetSessionWageRates.mockResolvedValue({
      app_session_id: "EA-INTEGRATION",
      norm_addressee: "business",
      rows: businessRows,
    });
    mockUpdateSessionWageRate.mockResolvedValue({
      app_session_id: "EA-INTEGRATION",
      norm_addressee: "business",
      rows: businessRows,
    });
    mockComputeTotalCost.mockResolvedValue({ total_cost: 80 });

    render(<EaEditDrawerShell open onClose={jest.fn()} />);
    const user = userEvent.setup();

    const row = await screen.findByText(/^niedrig$/i);
    const tr = row.closest("tr");
    const overrideInput = within(tr as HTMLElement).getByRole("textbox");
    await user.type(overrideInput, "80");
    await user.click(screen.getByRole("button", { name: /lohnsätze speichern/i }));

    await waitFor(() =>
      expect(mockComputeTotalCost).toHaveBeenCalledWith(
        expect.objectContaining({
          appSessionId: "EA-INTEGRATION",
          normAddressee: "business",
        })
      )
    );
  });
});

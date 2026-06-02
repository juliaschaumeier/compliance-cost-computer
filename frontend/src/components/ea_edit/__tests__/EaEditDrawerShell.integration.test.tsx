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
    computeTotalCost: jest.fn(),
    getSessionPayRates: jest.fn(),
    updateSessionPayRates: jest.fn(),
    getEditableCaseGroups: jest.fn(),
    getEditableProcessSteps: jest.fn(),
  },
}));

const mockUseApp = useApp as jest.Mock;
const mockGetSessionPayRates = apiClient.getSessionPayRates as jest.Mock;
const mockUpdateSessionPayRates = apiClient.updateSessionPayRates as jest.Mock;
const mockComputeTotalCost = apiClient.computeTotalCost as jest.Mock;

describe("EaEditDrawerShell integration", () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "EA-INTEGRATION",
        selectedNormAddressee: "administration",
      },
    });
    mockGetSessionPayRates.mockResolvedValue({
      app_session_id: "EA-INTEGRATION",
      administration_level: "bund",
      defaults: { a: 42, b: 52, c: 62, d: 57 },
      edited: { a: null, b: null, c: null, d: null },
      active: { a: 42, b: 52, c: 62, d: 57 },
    });
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
    // Regression: das automatische Neuberechnen lief frueher immer fuer
    // administration (norm_addressee fehlte im Request), sodass ein im
    // Wirtschaft-Tab gesetzter Override die Wirtschaft-Gesamtkosten nie aktualisierte.
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "EA-INTEGRATION",
        selectedNormAddressee: "business",
      },
    });
    const businessRates = {
      app_session_id: "EA-INTEGRATION",
      norm_addressee: "business",
      editable: true,
      administration_level: null,
      wage_source_label: "K",
      defaults: { a: 29, b: 54.4, c: 93.1, d: 57.9 },
      edited: { a: null, b: null, c: null, d: null },
      active: { a: 29, b: 54.4, c: 93.1, d: 57.9 },
    };
    mockGetSessionPayRates.mockResolvedValue(businessRates);
    mockUpdateSessionPayRates.mockResolvedValue({
      ...businessRates,
      edited: { a: 80, b: null, c: null, d: null },
      active: { a: 80, b: 54.4, c: 93.1, d: 57.9 },
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

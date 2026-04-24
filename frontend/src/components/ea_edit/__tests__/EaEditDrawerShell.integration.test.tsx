import { render, screen, within } from "@testing-library/react";
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
});

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EaPayRatesTab from "@/components/ea_edit/EaPayRatesTab";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getSessionPayRates: jest.fn(),
    updateSessionPayRates: jest.fn(),
  },
}));

const mockGetSessionPayRates = apiClient.getSessionPayRates as jest.Mock;
const mockUpdateSessionPayRates = apiClient.updateSessionPayRates as jest.Mock;

describe("EaPayRatesTab", () => {
  beforeEach(() => {
    mockGetSessionPayRates.mockReset();
    mockUpdateSessionPayRates.mockReset();
    mockGetSessionPayRates.mockResolvedValue({
      app_session_id: "PAY-TAB",
      administration_level: "bund",
      defaults: { a: 10, b: 20, c: 30, d: 40 },
      edited: { a: null, b: null, c: null, d: null },
      active: { a: 10, b: 20, c: 30, d: 40 },
    });
    mockUpdateSessionPayRates.mockResolvedValue({
      app_session_id: "PAY-TAB",
      administration_level: "bund",
      defaults: { a: 10, b: 20, c: 30, d: 40 },
      edited: { a: 99, b: null, c: null, d: null },
      active: { a: 99, b: 20, c: 30, d: 40 },
    });
  });

  it("loads and saves pay-rate edited values", async () => {
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={runAutoRecompute} />
    );

    const row = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const input = within(tr as HTMLElement).getByRole("textbox");
    const user = userEvent.setup();

    await user.clear(input);
    await user.type(input, "99");
    await user.click(screen.getByRole("button", { name: /lohnsätze speichern/i }));

    await waitFor(() => expect(mockUpdateSessionPayRates).toHaveBeenCalledTimes(1));
    expect(mockUpdateSessionPayRates).toHaveBeenCalledWith({
      appSessionId: "PAY-TAB",
      administrationLevel: "bund",
      editedA: 99,
      editedB: null,
      editedC: null,
      editedD: null,
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("emits tiles-updated only once on save via recompute", async () => {
    const onTilesUpdated = jest.fn();
    window.addEventListener("tiles-updated", onTilesUpdated);
    try {
      const runAutoRecompute = jest.fn().mockImplementation(async () => {
        window.dispatchEvent(new Event("tiles-updated"));
      });
      render(
        <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={runAutoRecompute} />
      );

      const row = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
      const tr = row.closest("tr");
      expect(tr).toBeTruthy();
      const input = within(tr as HTMLElement).getByRole("textbox");
      const user = userEvent.setup();

      await user.clear(input);
      await user.type(input, "99");
      await user.click(screen.getByRole("button", { name: /lohnsätze speichern/i }));

      await waitFor(() => expect(runAutoRecompute).toHaveBeenCalledTimes(1));
      expect(onTilesUpdated).toHaveBeenCalledTimes(1);
    } finally {
      window.removeEventListener("tiles-updated", onTilesUpdated);
    }
  });

  it("disables save for invalid numeric input", async () => {
    render(
      <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={jest.fn()} />
    );

    const row = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const input = within(tr as HTMLElement).getByRole("textbox");
    const user = userEvent.setup();

    await user.clear(input);
    await user.type(input, "abc");

    expect(
      screen.getByRole("button", { name: /lohnsätze speichern/i })
    ).toBeDisabled();
    expect(
      screen.getByText(/bitte ungültige zahlenformate korrigieren/i)
    ).toBeInTheDocument();
  });

  it("disables save when there are no changes", async () => {
    render(
      <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={jest.fn()} />
    );
    await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    expect(
      screen.getByRole("button", { name: /lohnsätze speichern/i })
    ).toBeDisabled();
  });

  it("resets values to model values", async () => {
    mockGetSessionPayRates.mockResolvedValueOnce({
      app_session_id: "PAY-TAB",
      administration_level: "bund",
      defaults: { a: 10, b: 20, c: 30, d: 40 },
      edited: { a: 77, b: null, c: null, d: null },
      active: { a: 77, b: 20, c: 30, d: 40 },
    });
    mockUpdateSessionPayRates.mockResolvedValueOnce({
      app_session_id: "PAY-TAB",
      administration_level: "bund",
      defaults: { a: 10, b: 20, c: 30, d: 40 },
      edited: { a: null, b: null, c: null, d: null },
      active: { a: 10, b: 20, c: 30, d: 40 },
    });
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={runAutoRecompute} />
    );
    await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: /auf modellwerte zurücksetzen/i })
    );

    await waitFor(() => expect(mockUpdateSessionPayRates).toHaveBeenCalledTimes(1));
    expect(mockUpdateSessionPayRates).toHaveBeenCalledWith({
      appSessionId: "PAY-TAB",
      administrationLevel: "bund",
      editedA: null,
      editedB: null,
      editedC: null,
      editedD: null,
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("disables reset when no saved edited value is active", async () => {
    render(
      <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={jest.fn()} />
    );
    await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    expect(
      screen.getByRole("button", { name: /auf modellwerte zurücksetzen/i })
    ).toBeDisabled();
  });

  it("keeps unsaved edited values across tab deactivate/reactivate", async () => {
    const onDirtyChange = jest.fn();
    const { rerender } = render(
      <EaPayRatesTab
        open
        active
        appSessionId="PAY-TAB"
        runAutoRecompute={jest.fn()}
        onDirtyChange={onDirtyChange}
      />
    );

    const row = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const input = within(tr as HTMLElement).getByRole("textbox");
    const user = userEvent.setup();

    await user.clear(input);
    await user.type(input, "88");
    expect(input).toHaveValue("88");
    expect(
      screen.getByRole("button", { name: /lohnsätze speichern/i })
    ).toBeEnabled();

    rerender(
      <EaPayRatesTab
        open
        active={false}
        appSessionId="PAY-TAB"
        runAutoRecompute={jest.fn()}
        onDirtyChange={onDirtyChange}
      />
    );

    rerender(
      <EaPayRatesTab
        open
        active
        appSessionId="PAY-TAB"
        runAutoRecompute={jest.fn()}
        onDirtyChange={onDirtyChange}
      />
    );

    const rowAfter = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const trAfter = rowAfter.closest("tr");
    expect(trAfter).toBeTruthy();
    const inputAfter = within(trAfter as HTMLElement).getByRole("textbox");
    expect(inputAfter).toHaveValue("88");
    expect(mockGetSessionPayRates).toHaveBeenCalledTimes(1);
    expect(onDirtyChange.mock.calls.some(([dirty]) => dirty === true)).toBe(true);
  });

  it("keeps active values stable while unsaved input changes", async () => {
    render(
      <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={jest.fn()} />
    );

    const row = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const user = userEvent.setup();
    const rowScope = within(tr as HTMLElement);
    const input = rowScope.getByRole("textbox");

    expect(rowScope.getAllByText("10 €")).toHaveLength(2);

    await user.clear(input);
    await user.type(input, "99");

    expect(rowScope.getAllByText("10 €")).toHaveLength(2);
    expect(input).toHaveValue("99");
  });

  it("does not prefill 'Neu' from saved edited values and stays clean by default", async () => {
    mockGetSessionPayRates.mockResolvedValueOnce({
      app_session_id: "PAY-TAB",
      administration_level: "bund",
      defaults: { a: 10, b: 20, c: 30, d: 40 },
      edited: { a: 77, b: null, c: null, d: null },
      active: { a: 77, b: 20, c: 30, d: 40 },
    });
    render(
      <EaPayRatesTab open active appSessionId="PAY-TAB" runAutoRecompute={jest.fn()} />
    );

    const row = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const rowScope = within(tr as HTMLElement);
    const input = rowScope.getByRole("textbox");

    expect(input).toHaveValue("");
    expect(rowScope.getByText("10 €")).toBeInTheDocument();
    expect(rowScope.getByText("77 €")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /lohnsätze speichern/i })
    ).toBeDisabled();
  });
});

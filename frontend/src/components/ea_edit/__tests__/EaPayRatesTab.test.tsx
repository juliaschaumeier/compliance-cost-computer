import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EaPayRatesTab from "@/components/ea_edit/EaPayRatesTab";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getSessionWageRates: jest.fn(),
    updateSessionWageRate: jest.fn(),
  },
}));

const mockGetSessionWageRates = apiClient.getSessionWageRates as jest.Mock;
const mockUpdateSessionWageRate = apiClient.updateSessionWageRate as jest.Mock;
const EA_ACTIVITY_ID = "ea_edit:test";

const ADMIN_ROWS = [
  {
    wage_source_kind: "verwaltungsebene",
    wage_source_value: "bund",
    qualification: "einfacher_und_mittlerer_dienst",
    model_hourly_rate: 10,
    hourly_rate_edited: null,
  },
  {
    wage_source_kind: "verwaltungsebene",
    wage_source_value: "bund",
    qualification: "gehobener_dienst",
    model_hourly_rate: 20,
    hourly_rate_edited: null,
  },
  {
    wage_source_kind: "verwaltungsebene",
    wage_source_value: "bund",
    qualification: "hoeherer_dienst",
    model_hourly_rate: 30,
    hourly_rate_edited: null,
  },
  {
    wage_source_kind: "verwaltungsebene",
    wage_source_value: "bund",
    qualification: "durchschnitt",
    model_hourly_rate: 40,
    hourly_rate_edited: null,
  },
];

function eDmDInput(): HTMLElement {
  const label = screen.getByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
  const tr = label.closest("tr") as HTMLElement;
  return within(tr).getByRole("textbox");
}

describe("EaPayRatesTab", () => {
  beforeEach(() => {
    mockGetSessionWageRates.mockReset();
    mockUpdateSessionWageRate.mockReset();
    mockGetSessionWageRates.mockResolvedValue({ app_session_id: "PAY-TAB", rows: ADMIN_ROWS });
    mockUpdateSessionWageRate.mockResolvedValue({ app_session_id: "PAY-TAB", rows: ADMIN_ROWS });
  });

  it("groups rows under their wage source", async () => {
    render(
      <EaPayRatesTab normAddressee="administration" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={jest.fn()} />
    );
    expect(await screen.findByText("Bund")).toBeInTheDocument();
    expect(screen.getByText(/Gehobener Dienst \(gD\)/i)).toBeInTheDocument();
  });

  it("saves a single (source, qualification) override and recomputes", async () => {
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaPayRatesTab normAddressee="administration" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={runAutoRecompute} />
    );
    await screen.findByText("Bund");
    const user = userEvent.setup();
    await user.type(eDmDInput(), "99");
    await user.click(screen.getByRole("button", { name: /lohnsätze speichern/i }));

    await waitFor(() => expect(mockUpdateSessionWageRate).toHaveBeenCalledTimes(1));
    expect(mockUpdateSessionWageRate).toHaveBeenCalledWith({
      appSessionId: "PAY-TAB",
      normAddressee: "administration",
      wageSourceKind: "verwaltungsebene",
      wageSourceValue: "bund",
      qualification: "einfacher_und_mittlerer_dienst",
      hourlyRateEdited: 99,
      eaActivityId: EA_ACTIVITY_ID,
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("clears a previous save status when the user edits again", async () => {
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaPayRatesTab normAddressee="administration" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={runAutoRecompute} />
    );

    const row = await screen.findByText(/Einfacher\/Mittlerer Dienst \(eD\/mD\)/i);
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const input = within(tr as HTMLElement).getByRole("textbox");
    const user = userEvent.setup();

    await user.clear(input);
    await user.type(input, "99");
    await user.click(screen.getByRole("button", { name: /lohnsätze speichern/i }));

    expect(
      await screen.findByText(/lohnsaetze gespeichert|lohnsätze gespeichert/i)
    ).toBeInTheDocument();

    await user.type(input, "1");

    expect(
      screen.queryByText(/lohnsaetze gespeichert|lohnsätze gespeichert/i)
    ).not.toBeInTheDocument();
  });

  it("emits tiles-updated only once on save via recompute", async () => {
    const onTilesUpdated = jest.fn();
    window.addEventListener("tiles-updated", onTilesUpdated);
    try {
      const runAutoRecompute = jest.fn().mockImplementation(async () => {
        window.dispatchEvent(new Event("tiles-updated"));
      });
      render(
        <EaPayRatesTab normAddressee="administration" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={runAutoRecompute} />
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
      <EaPayRatesTab normAddressee="administration" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={jest.fn()} />
    );
    await screen.findByText("Bund");
    const user = userEvent.setup();
    await user.type(eDmDInput(), "abc");
    expect(screen.getByRole("button", { name: /lohnsätze speichern/i })).toBeDisabled();
    expect(screen.getByText(/bitte ungültige zahlenformate korrigieren/i)).toBeInTheDocument();
  });

  it("disables save when there are no changes", async () => {
    render(
      <EaPayRatesTab normAddressee="administration" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={jest.fn()} />
    );
    await screen.findByText("Bund");
    expect(screen.getByRole("button", { name: /lohnsätze speichern/i })).toBeDisabled();
  });

  it("resets active overrides to model values", async () => {
    mockGetSessionWageRates.mockResolvedValueOnce({
      app_session_id: "PAY-TAB",
      rows: [{ ...ADMIN_ROWS[0], hourly_rate_edited: 77 }, ...ADMIN_ROWS.slice(1)],
    });
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaPayRatesTab normAddressee="administration" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={runAutoRecompute} />
    );
    await screen.findByText("Bund");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /auf modellwerte zurücksetzen/i }));

    await waitFor(() => expect(mockUpdateSessionWageRate).toHaveBeenCalledTimes(1));
    expect(mockUpdateSessionWageRate).toHaveBeenCalledWith({
      appSessionId: "PAY-TAB",
      normAddressee: "administration",
      wageSourceKind: "verwaltungsebene",
      wageSourceValue: "bund",
      qualification: "einfacher_und_mittlerer_dienst",
      hourlyRateEdited: null,
      eaActivityId: EA_ACTIVITY_ID,
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("labels a business economic section with its WZ detail", async () => {
    mockGetSessionWageRates.mockResolvedValueOnce({
      app_session_id: "PAY-TAB",
      rows: [
        {
          wage_source_kind: "wirtschaftsabschnitt",
          wage_source_value: "K",
          qualification: "hoch",
          model_hourly_rate: 51,
          hourly_rate_edited: null,
        },
      ],
    });
    render(
      <EaPayRatesTab normAddressee="business" open active appSessionId="PAY-TAB" eaActivityId={EA_ACTIVITY_ID} runAutoRecompute={jest.fn()} />
    );
    expect(
      await screen.findByText(/K · Finanz- und Versicherungsdienstleistungen/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/^Hoch$/i)).toBeInTheDocument();
  });

  it("shows the citizens note instead of a table", async () => {
    render(
      <EaPayRatesTab normAddressee="citizens" open active appSessionId="PAY-TAB" runAutoRecompute={jest.fn()} />
    );
    expect(
      screen.getByText(/Lohnsätze sind für Bürgerinnen und Bürger nicht anwendbar/i)
    ).toBeInTheDocument();
    expect(mockGetSessionWageRates).not.toHaveBeenCalled();
  });
});

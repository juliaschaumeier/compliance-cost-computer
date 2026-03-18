import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EaCaseMetricsTab from "@/components/ea_edit/EaCaseMetricsTab";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getEditableCaseGroups: jest.fn(),
    bulkUpdateCaseGroups: jest.fn(),
  },
}));

const mockGetEditableCaseGroups = apiClient.getEditableCaseGroups as jest.Mock;
const mockBulkUpdateCaseGroups = apiClient.bulkUpdateCaseGroups as jest.Mock;

describe("EaCaseMetricsTab", () => {
  beforeEach(() => {
    mockGetEditableCaseGroups.mockReset();
    mockBulkUpdateCaseGroups.mockReset();
    mockGetEditableCaseGroups.mockResolvedValue({
      rows: [
        {
          case_group_id: 11,
          process_id: 1,
          case_group: "Fallgruppe A",
          description: "Beschreibung",
          change_status: "geaendert",
          addressees_current: 10,
          annual_frequency_current: 2,
          cases_current: 20,
          addressees_current_edited: null,
          annual_frequency_current_edited: null,
          cases_current_edited: null,
          addressees_proposed: 12,
          annual_frequency_proposed: 2,
          cases_proposed: 24,
          addressees_proposed_edited: null,
          annual_frequency_proposed_edited: null,
          cases_proposed_edited: null,
          addressees_current_effective: 10,
          annual_frequency_current_effective: 2,
          cases_current_effective: 20,
          addressees_proposed_effective: 12,
          annual_frequency_proposed_effective: 2,
          cases_proposed_effective: 24,
        },
      ],
    });
    mockBulkUpdateCaseGroups.mockResolvedValue({ updated: 1 });
  });

  it("loads rows and saves reviewed edits", async () => {
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={runAutoRecompute}
      />
    );
    const row = await screen.findByText("Fallgruppe A");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("10");
    expect(inputs[1]).toHaveValue("2");
    expect(inputs[2]).toHaveValue("12");
    expect(inputs[3]).toHaveValue("2");
    const user = userEvent.setup();

    await user.clear(inputs[0]);
    await user.type(inputs[0], "13");
    await user.click(screen.getByRole("button", { name: /prüfen/i }));
    expect(screen.getByText("Gültig Betroffene")).toBeInTheDocument();
    expect(screen.getAllByRole("cell", { name: "10" })).toHaveLength(2);
    expect(screen.getByRole("cell", { name: "13" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /änderungen speichern/i }));

    await waitFor(() => expect(mockBulkUpdateCaseGroups).toHaveBeenCalledTimes(1));
    expect(mockBulkUpdateCaseGroups).toHaveBeenCalledWith({
      appSessionId: "CASE-TAB",
      rows: [
        {
          case_group_id: 11,
          addressees_current: 13,
          annual_frequency_current: null,
          addressees_proposed: null,
          annual_frequency_proposed: null,
        },
      ],
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("prefills active edited values and highlights changed cells only", async () => {
    mockGetEditableCaseGroups.mockResolvedValueOnce({
      rows: [
        {
          case_group_id: 11,
          process_id: 1,
          case_group: "Fallgruppe A",
          description: "Beschreibung",
          change_status: "geaendert",
          addressees_current: 10,
          annual_frequency_current: 2,
          cases_current: 20,
          addressees_current_edited: 15,
          annual_frequency_current_edited: null,
          cases_current_edited: 30,
          addressees_proposed: 12,
          annual_frequency_proposed: 2,
          cases_proposed: 24,
          addressees_proposed_edited: null,
          annual_frequency_proposed_edited: null,
          cases_proposed_edited: null,
          addressees_current_effective: 15,
          annual_frequency_current_effective: 2,
          cases_current_effective: 30,
          addressees_proposed_effective: 12,
          annual_frequency_proposed_effective: 2,
          cases_proposed_effective: 24,
        },
      ],
    });
    render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    const row = await screen.findByText("Fallgruppe A");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("15");

    const user = userEvent.setup();
    await user.clear(inputs[0]);
    await user.type(inputs[0], "16");

    expect(inputs[0].closest("td")).toHaveClass("bg-amber-50");
    expect(inputs[1].closest("td")).not.toHaveClass("bg-amber-50");
  });

  it("renders zeros in a lighter text color", async () => {
    mockGetEditableCaseGroups.mockResolvedValueOnce({
      rows: [
        {
          case_group_id: 11,
          process_id: 1,
          case_group: "Fallgruppe A",
          description: "Beschreibung",
          change_status: "geaendert",
          addressees_current: 0,
          annual_frequency_current: 2,
          cases_current: 0,
          addressees_current_edited: null,
          annual_frequency_current_edited: null,
          cases_current_edited: null,
          addressees_proposed: 12,
          annual_frequency_proposed: 2,
          cases_proposed: 24,
          addressees_proposed_edited: null,
          annual_frequency_proposed_edited: null,
          cases_proposed_edited: null,
          addressees_current_effective: 0,
          annual_frequency_current_effective: 2,
          cases_current_effective: 0,
          addressees_proposed_effective: 12,
          annual_frequency_proposed_effective: 2,
          cases_proposed_effective: 24,
        },
      ],
    });
    render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    const row = await screen.findByText("Fallgruppe A");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[0]).toHaveClass("text-slate-400");
    expect(within(tr as HTMLElement).getByText("0")).toHaveClass("text-slate-400");
  });

  it("prefills decimal edited values in de-DE style without invalid or dirty state", async () => {
    mockGetEditableCaseGroups.mockResolvedValueOnce({
      rows: [
        {
          case_group_id: 11,
          process_id: 1,
          case_group: "Fallgruppe A",
          description: "Beschreibung",
          change_status: "geaendert",
          addressees_current: 1,
          annual_frequency_current: 2,
          cases_current: 2,
          addressees_current_edited: 1.5,
          annual_frequency_current_edited: null,
          cases_current_edited: 3,
          addressees_proposed: 12,
          annual_frequency_proposed: 2,
          cases_proposed: 24,
          addressees_proposed_edited: null,
          annual_frequency_proposed_edited: null,
          cases_proposed_edited: null,
          addressees_current_effective: 1.5,
          annual_frequency_current_effective: 2,
          cases_current_effective: 3,
          addressees_proposed_effective: 12,
          annual_frequency_proposed_effective: 2,
          cases_proposed_effective: 24,
        },
      ],
    });
    render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    const row = await screen.findByText("Fallgruppe A");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("1,5");
    expect(inputs[0]).not.toHaveClass("border-red-400");
    expect(inputs[0].closest("td")).not.toHaveClass("bg-amber-50");
    expect(screen.getByText(/Ungespeicherte Änderungen: 0 Zeilen \/ 0 Zellen/i)).toBeInTheDocument();
  });

  it("blocks review for invalid numeric input", async () => {
    render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    const row = await screen.findByText("Fallgruppe A");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    const user = userEvent.setup();

    await user.clear(inputs[0]);
    await user.type(inputs[0], "abc");

    expect(screen.getByRole("button", { name: /prüfen/i })).toBeDisabled();
    expect(
      screen.getByText(/bitte ungültige zahlenformate korrigieren/i)
    ).toBeInTheDocument();
  });

  it("resets edited values to model values", async () => {
    mockGetEditableCaseGroups.mockResolvedValueOnce({
      rows: [
        {
          case_group_id: 11,
          process_id: 1,
          case_group: "Fallgruppe A",
          description: "Beschreibung",
          change_status: "geaendert",
          addressees_current: 10,
          annual_frequency_current: 2,
          cases_current: 20,
          addressees_current_edited: 15,
          annual_frequency_current_edited: null,
          cases_current_edited: 30,
          addressees_proposed: 12,
          annual_frequency_proposed: 2,
          cases_proposed: 24,
          addressees_proposed_edited: null,
          annual_frequency_proposed_edited: null,
          cases_proposed_edited: null,
          addressees_current_effective: 15,
          annual_frequency_current_effective: 2,
          cases_current_effective: 30,
          addressees_proposed_effective: 12,
          annual_frequency_proposed_effective: 2,
          cases_proposed_effective: 24,
        },
      ],
    });
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={runAutoRecompute}
      />
    );
    await screen.findByText("Fallgruppe A");
    const row = screen.getByText("Fallgruppe A");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("15");
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: /auf modellwerte zurücksetzen/i })
    );

    await waitFor(() => expect(mockBulkUpdateCaseGroups).toHaveBeenCalledTimes(1));
    expect(mockBulkUpdateCaseGroups).toHaveBeenCalledWith({
      appSessionId: "CASE-TAB",
      rows: [
        {
          case_group_id: 11,
          addressees_current: null,
          annual_frequency_current: null,
          addressees_proposed: null,
          annual_frequency_proposed: null,
        },
      ],
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("disables reset when no edited values exist", async () => {
    render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    await screen.findByText("Fallgruppe A");
    const resetButton = screen.getByRole("button", {
      name: /auf modellwerte zurücksetzen/i,
    });
    expect(resetButton).toBeDisabled();
  });

  it("keeps unsaved edits across tab deactivate/reactivate without refetch", async () => {
    const { rerender } = render(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    const row = await screen.findByText("Fallgruppe A");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    const user = userEvent.setup();

    await user.clear(inputs[0]);
    await user.type(inputs[0], "13");
    expect(inputs[0]).toHaveValue("13");
    expect(mockGetEditableCaseGroups).toHaveBeenCalledTimes(1);

    rerender(
      <EaCaseMetricsTab
        open
        active={false}
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    rerender(
      <EaCaseMetricsTab
        open
        active
        appSessionId="CASE-TAB"
        runAutoRecompute={jest.fn()}
      />
    );

    const rowAfter = await screen.findByText("Fallgruppe A");
    const trAfter = rowAfter.closest("tr");
    expect(trAfter).toBeTruthy();
    const inputsAfter = within(trAfter as HTMLElement).getAllByRole("textbox");
    expect(inputsAfter[0]).toHaveValue("13");
    expect(mockGetEditableCaseGroups).toHaveBeenCalledTimes(1);
  });
});

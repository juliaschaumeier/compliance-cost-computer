import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EaEffortMetricsTab from "@/components/ea_edit/EaEffortMetricsTab";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getEditableCaseGroups: jest.fn(),
    getEditableProcessSteps: jest.fn(),
    bulkUpdateProcessSteps: jest.fn(),
  },
}));

const mockGetEditableCaseGroups = apiClient.getEditableCaseGroups as jest.Mock;
const mockGetEditableProcessSteps = apiClient.getEditableProcessSteps as jest.Mock;
const mockBulkUpdateProcessSteps = apiClient.bulkUpdateProcessSteps as jest.Mock;

describe("EaEffortMetricsTab", () => {
  beforeEach(() => {
    mockGetEditableCaseGroups.mockReset();
    mockGetEditableProcessSteps.mockReset();
    mockBulkUpdateProcessSteps.mockReset();
    mockGetEditableCaseGroups.mockResolvedValue({
      rows: [
        {
          case_group_id: 22,
          norm_addressee: "administration",
          process_id: 1,
          case_group: "Fallgruppe B",
        },
      ],
    });
    mockGetEditableProcessSteps.mockResolvedValue({
      rows: [
        {
          step_id: 101,
          case_group_id: 22,
          norm_addressee: "administration",
          step: "Schritt 1",
          description: "Beschreibung",
          change_status: "geaendert",
          time_required_in_min_a_current: 1,
          time_required_in_min_b_current: null,
          time_required_in_min_c_current: null,
          time_required_in_min_d_current: null,
          expenses_current: 0,
          time_required_in_min_a_current_edited: null,
          time_required_in_min_b_current_edited: null,
          time_required_in_min_c_current_edited: null,
          time_required_in_min_d_current_edited: null,
          expenses_current_edited: null,
          time_required_in_min_a_proposed: 2,
          time_required_in_min_b_proposed: null,
          time_required_in_min_c_proposed: null,
          time_required_in_min_d_proposed: null,
          expenses_proposed: 0,
          time_required_in_min_a_proposed_edited: null,
          time_required_in_min_b_proposed_edited: null,
          time_required_in_min_c_proposed_edited: null,
          time_required_in_min_d_proposed_edited: null,
          expenses_proposed_edited: null,
          time_required_in_min_a_current_effective: 1,
          time_required_in_min_b_current_effective: null,
          time_required_in_min_c_current_effective: null,
          time_required_in_min_d_current_effective: null,
          expenses_current_effective: 0,
          time_required_in_min_a_proposed_effective: 2,
          time_required_in_min_b_proposed_effective: null,
          time_required_in_min_c_proposed_effective: null,
          time_required_in_min_d_proposed_effective: null,
          expenses_proposed_effective: 0,
        },
      ],
    });
    mockBulkUpdateProcessSteps.mockResolvedValue({ updated: 1 });
  });

  it("loads case groups/steps and saves reviewed step edits", async () => {
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={runAutoRecompute}
      />
    );

    const row = await screen.findByText("Schritt 1");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("1");
    expect(inputs[4]).toHaveValue("0");
    expect(inputs[5]).toHaveValue("2");
    const user = userEvent.setup();

    await user.clear(inputs[0]);
    await user.type(inputs[0], "7");
    await user.click(screen.getByRole("button", { name: /prüfen/i }));
    expect(screen.getByText("Aktuelles Gesetz Zeit eD/mD")).toBeInTheDocument();
    expect(screen.getAllByRole("cell", { name: "1" })).toHaveLength(2);
    expect(screen.getByRole("cell", { name: "7" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /änderungen speichern/i }));

    await waitFor(() => expect(mockBulkUpdateProcessSteps).toHaveBeenCalledTimes(1));
    expect(mockBulkUpdateProcessSteps).toHaveBeenCalledWith({
      appSessionId: "STEP-TAB",
      rows: [
        {
          step_id: 101,
          time_required_in_min_a_current: 7,
          time_required_in_min_b_current: null,
          time_required_in_min_c_current: null,
          time_required_in_min_d_current: null,
          expenses_current: null,
          time_required_in_min_a_proposed: null,
          time_required_in_min_b_proposed: null,
          time_required_in_min_c_proposed: null,
          time_required_in_min_d_proposed: null,
          expenses_proposed: null,
        },
      ],
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("prefills decimal edited values in de-DE style without invalid or dirty state", async () => {
    mockGetEditableProcessSteps.mockResolvedValueOnce({
      rows: [
        {
          step_id: 101,
          case_group_id: 22,
          norm_addressee: "administration",
          step: "Schritt 1",
          description: "Beschreibung",
          change_status: "geaendert",
          time_required_in_min_a_current: 1,
          time_required_in_min_b_current: null,
          time_required_in_min_c_current: null,
          time_required_in_min_d_current: null,
          expenses_current: 0,
          time_required_in_min_a_current_edited: 1.5,
          time_required_in_min_b_current_edited: null,
          time_required_in_min_c_current_edited: null,
          time_required_in_min_d_current_edited: null,
          expenses_current_edited: null,
          time_required_in_min_a_proposed: 2,
          time_required_in_min_b_proposed: null,
          time_required_in_min_c_proposed: null,
          time_required_in_min_d_proposed: null,
          expenses_proposed: 0,
          time_required_in_min_a_proposed_edited: null,
          time_required_in_min_b_proposed_edited: null,
          time_required_in_min_c_proposed_edited: null,
          time_required_in_min_d_proposed_edited: null,
          expenses_proposed_edited: null,
          time_required_in_min_a_current_effective: 1.5,
          time_required_in_min_b_current_effective: null,
          time_required_in_min_c_current_effective: null,
          time_required_in_min_d_current_effective: null,
          expenses_current_effective: 0,
          time_required_in_min_a_proposed_effective: 2,
          time_required_in_min_b_proposed_effective: null,
          time_required_in_min_c_proposed_effective: null,
          time_required_in_min_d_proposed_effective: null,
          expenses_proposed_effective: 0,
        },
      ],
    });

    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );

    const row = await screen.findByText("Schritt 1");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("1,5");
    expect(inputs[0]).not.toHaveClass("border-red-400");
    expect(inputs[0].closest("td")).not.toHaveClass("bg-amber-50");
    expect(
      screen.getByText(/Ungespeicherte Änderungen: 0 Fallgruppen \/ 0 Schritte \/ 0 Zellen/i)
    ).toBeInTheDocument();
  });

  it("renders zero values in a lighter text color", async () => {
    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    const row = await screen.findByText("Schritt 1");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    expect(inputs[4]).toHaveClass("text-slate-400");
    expect(inputs[9]).toHaveClass("text-slate-400");
  });

  it("blocks review for invalid numeric input", async () => {
    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );

    const row = await screen.findByText("Schritt 1");
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

  it("resets edited values to model values for selected case group", async () => {
    mockGetEditableProcessSteps.mockResolvedValueOnce({
      rows: [
        {
          step_id: 101,
          case_group_id: 22,
          norm_addressee: "administration",
          step: "Schritt 1",
          description: "Beschreibung",
          change_status: "geaendert",
          time_required_in_min_a_current: 1,
          time_required_in_min_b_current: null,
          time_required_in_min_c_current: null,
          time_required_in_min_d_current: null,
          expenses_current: 0,
          time_required_in_min_a_current_edited: 5,
          time_required_in_min_b_current_edited: null,
          time_required_in_min_c_current_edited: null,
          time_required_in_min_d_current_edited: null,
          expenses_current_edited: null,
          time_required_in_min_a_proposed: 2,
          time_required_in_min_b_proposed: null,
          time_required_in_min_c_proposed: null,
          time_required_in_min_d_proposed: null,
          expenses_proposed: 0,
          time_required_in_min_a_proposed_edited: null,
          time_required_in_min_b_proposed_edited: null,
          time_required_in_min_c_proposed_edited: null,
          time_required_in_min_d_proposed_edited: null,
          expenses_proposed_edited: null,
          time_required_in_min_a_current_effective: 5,
          time_required_in_min_b_current_effective: null,
          time_required_in_min_c_current_effective: null,
          time_required_in_min_d_current_effective: null,
          expenses_current_effective: 0,
          time_required_in_min_a_proposed_effective: 2,
          time_required_in_min_b_proposed_effective: null,
          time_required_in_min_c_proposed_effective: null,
          time_required_in_min_d_proposed_effective: null,
          expenses_proposed_effective: 0,
        },
      ],
    });
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={runAutoRecompute}
      />
    );
    await screen.findByText("Schritt 1");
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", { name: /auf modellwerte zurücksetzen/i })
    );

    await waitFor(() => expect(mockBulkUpdateProcessSteps).toHaveBeenCalledTimes(1));
    expect(mockBulkUpdateProcessSteps).toHaveBeenCalledWith({
      appSessionId: "STEP-TAB",
      rows: [
        {
          step_id: 101,
          time_required_in_min_a_current: null,
          time_required_in_min_b_current: null,
          time_required_in_min_c_current: null,
          time_required_in_min_d_current: null,
          expenses_current: null,
          time_required_in_min_a_proposed: null,
          time_required_in_min_b_proposed: null,
          time_required_in_min_c_proposed: null,
          time_required_in_min_d_proposed: null,
          expenses_proposed: null,
        },
      ],
    });
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("disables reset when no edited values exist", async () => {
    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    await screen.findByText("Schritt 1");
    const resetButton = screen.getByRole("button", {
      name: /auf modellwerte zurücksetzen/i,
    });
    expect(resetButton).toBeDisabled();
  });

  it("does not refetch case groups when selecting another case group", async () => {
    mockGetEditableCaseGroups.mockResolvedValueOnce({
      rows: [
        {
          case_group_id: 22,
          norm_addressee: "administration",
          process_id: 1,
          case_group: "Fallgruppe B",
        },
        {
          case_group_id: 23,
          norm_addressee: "administration",
          process_id: 1,
          case_group: "Fallgruppe C",
        },
      ],
    });
    mockGetEditableProcessSteps.mockResolvedValue({
      rows: [],
    });

    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );

    const select = await screen.findByRole("combobox");
    expect(mockGetEditableCaseGroups).toHaveBeenCalledTimes(1);

    const user = userEvent.setup();
    await user.selectOptions(select, "23");

    await waitFor(() => expect(mockGetEditableProcessSteps).toHaveBeenCalledTimes(2));
    expect(mockGetEditableCaseGroups).toHaveBeenCalledTimes(1);
  });

  it("keeps edits across case groups and reviews/saves them in one pass", async () => {
    mockGetEditableCaseGroups.mockResolvedValueOnce({
      rows: [
        {
          case_group_id: 22,
          norm_addressee: "administration",
          process_id: 1,
          case_group: "Fallgruppe B",
        },
        {
          case_group_id: 23,
          norm_addressee: "administration",
          process_id: 1,
          case_group: "Fallgruppe C",
        },
      ],
    });
    mockGetEditableProcessSteps.mockImplementation(async ({ caseGroupId }) => {
      if (caseGroupId === 23) {
        return {
          rows: [
            {
              step_id: 202,
              case_group_id: 23,
              step: "Schritt 2",
              description: "Beschreibung 2",
              change_status: "geaendert",
              time_required_in_min_a_current: 3,
              time_required_in_min_b_current: null,
              time_required_in_min_c_current: null,
              time_required_in_min_d_current: null,
              expenses_current: 0,
              time_required_in_min_a_current_edited: null,
              time_required_in_min_b_current_edited: null,
              time_required_in_min_c_current_edited: null,
              time_required_in_min_d_current_edited: null,
              expenses_current_edited: null,
              time_required_in_min_a_proposed: 4,
              time_required_in_min_b_proposed: null,
              time_required_in_min_c_proposed: null,
              time_required_in_min_d_proposed: null,
              expenses_proposed: 0,
              time_required_in_min_a_proposed_edited: null,
              time_required_in_min_b_proposed_edited: null,
              time_required_in_min_c_proposed_edited: null,
              time_required_in_min_d_proposed_edited: null,
              expenses_proposed_edited: null,
              time_required_in_min_a_current_effective: 3,
              time_required_in_min_b_current_effective: null,
              time_required_in_min_c_current_effective: null,
              time_required_in_min_d_current_effective: null,
              expenses_current_effective: 0,
              time_required_in_min_a_proposed_effective: 4,
              time_required_in_min_b_proposed_effective: null,
              time_required_in_min_c_proposed_effective: null,
              time_required_in_min_d_proposed_effective: null,
              expenses_proposed_effective: 0,
            },
          ],
        };
      }
      return {
        rows: [
          {
            step_id: 101,
            case_group_id: 22,
            step: "Schritt 1",
            description: "Beschreibung",
            change_status: "geaendert",
            time_required_in_min_a_current: 1,
            time_required_in_min_b_current: null,
            time_required_in_min_c_current: null,
            time_required_in_min_d_current: null,
            expenses_current: 0,
            time_required_in_min_a_current_edited: null,
            time_required_in_min_b_current_edited: null,
            time_required_in_min_c_current_edited: null,
            time_required_in_min_d_current_edited: null,
            expenses_current_edited: null,
            time_required_in_min_a_proposed: 2,
            time_required_in_min_b_proposed: null,
            time_required_in_min_c_proposed: null,
            time_required_in_min_d_proposed: null,
            expenses_proposed: 0,
            time_required_in_min_a_proposed_edited: null,
            time_required_in_min_b_proposed_edited: null,
            time_required_in_min_c_proposed_edited: null,
            time_required_in_min_d_proposed_edited: null,
            expenses_proposed_edited: null,
            time_required_in_min_a_current_effective: 1,
            time_required_in_min_b_current_effective: null,
            time_required_in_min_c_current_effective: null,
            time_required_in_min_d_current_effective: null,
            expenses_current_effective: 0,
            time_required_in_min_a_proposed_effective: 2,
            time_required_in_min_b_proposed_effective: null,
            time_required_in_min_c_proposed_effective: null,
            time_required_in_min_d_proposed_effective: null,
            expenses_proposed_effective: 0,
          },
        ],
      };
    });

    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={runAutoRecompute}
      />
    );
    const user = userEvent.setup();

    const firstRow = await screen.findByText("Schritt 1");
    const firstInputs = within(firstRow.closest("tr") as HTMLElement).getAllByRole("textbox");
    await user.clear(firstInputs[0]);
    await user.type(firstInputs[0], "7");

    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "23");

    const secondRow = await screen.findByText("Schritt 2");
    const secondInputs = within(secondRow.closest("tr") as HTMLElement).getAllByRole("textbox");
    await user.clear(secondInputs[0]);
    await user.type(secondInputs[0], "9");

    expect(
      screen.getByText(/Ungespeicherte Änderungen: 2 Fallgruppen \/ 2 Schritte \/ 2 Zellen/i)
    ).toBeInTheDocument();

    const reviewButton = screen.getByRole("button", { name: /prüfen/i });
    expect(reviewButton).toBeEnabled();
    await user.click(reviewButton);

    expect(screen.getByText(/Fallgruppe B · 1 Änderungen/i)).toBeInTheDocument();
    expect(screen.getByText(/Fallgruppe C · 1 Änderungen/i)).toBeInTheDocument();

    const orderedRows = screen
      .getAllByRole("row")
      .map((row) => (row.textContent || "").replace(/\s+/g, " "));
    const groupBIndex = orderedRows.findIndex((text) =>
      text.includes("Fallgruppe B · 1 Änderungen")
    );
    const step1Index = orderedRows.findIndex((text) =>
      text.includes("Schritt 1")
    );
    const groupCIndex = orderedRows.findIndex((text) =>
      text.includes("Fallgruppe C · 1 Änderungen")
    );
    const step2Index = orderedRows.findIndex((text) =>
      text.includes("Schritt 2")
    );

    expect(groupBIndex).toBeGreaterThan(-1);
    expect(step1Index).toBeGreaterThan(groupBIndex);
    expect(groupCIndex).toBeGreaterThan(step1Index);
    expect(step2Index).toBeGreaterThan(groupCIndex);

    await user.click(screen.getByRole("button", { name: /änderungen speichern/i }));

    await waitFor(() => expect(mockBulkUpdateProcessSteps).toHaveBeenCalledTimes(1));
    const call = mockBulkUpdateProcessSteps.mock.calls[0][0];
    expect(call.appSessionId).toBe("STEP-TAB");
    expect(call.rows).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          step_id: 101,
          time_required_in_min_a_current: 7,
        }),
        expect.objectContaining({
          step_id: 202,
          time_required_in_min_a_current: 9,
        }),
      ])
    );
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("keeps unsaved edits across tab deactivate/reactivate without refetch", async () => {
    const { rerender } = render(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    const user = userEvent.setup();

    const row = await screen.findByText("Schritt 1");
    const tr = row.closest("tr");
    expect(tr).toBeTruthy();
    const inputs = within(tr as HTMLElement).getAllByRole("textbox");
    await user.clear(inputs[0]);
    await user.type(inputs[0], "7");
    expect(inputs[0]).toHaveValue("7");
    expect(mockGetEditableCaseGroups).toHaveBeenCalledTimes(1);
    expect(mockGetEditableProcessSteps).toHaveBeenCalledTimes(1);

    rerender(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active={false}
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );
    rerender(
      <EaEffortMetricsTab normAddressee="administration"
        open
        active
        appSessionId="STEP-TAB"
        runAutoRecompute={jest.fn()}
      />
    );

    const rowAfter = await screen.findByText("Schritt 1");
    const trAfter = rowAfter.closest("tr");
    expect(trAfter).toBeTruthy();
    const inputsAfter = within(trAfter as HTMLElement).getAllByRole("textbox");
    expect(inputsAfter[0]).toHaveValue("7");
    expect(mockGetEditableCaseGroups).toHaveBeenCalledTimes(1);
    expect(mockGetEditableProcessSteps).toHaveBeenCalledTimes(1);
  });
});

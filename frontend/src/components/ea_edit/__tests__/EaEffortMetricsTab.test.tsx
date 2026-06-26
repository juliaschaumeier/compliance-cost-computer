import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EaEffortMetricsTab from "@/components/ea_edit/EaEffortMetricsTab";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getEditableCaseGroups: jest.fn(),
    getEditableProcessSteps: jest.fn(),
    bulkUpdateProcessSteps: jest.fn(),
    updatePersonnelEffortTime: jest.fn(),
  },
}));

const mockGetEditableCaseGroups = apiClient.getEditableCaseGroups as jest.Mock;
const mockGetEditableProcessSteps = apiClient.getEditableProcessSteps as jest.Mock;
const mockBulkUpdateProcessSteps = apiClient.bulkUpdateProcessSteps as jest.Mock;
const mockUpdatePersonnelEffortTime = apiClient.updatePersonnelEffortTime as jest.Mock;

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
    mockUpdatePersonnelEffortTime.mockReset();
    mockUpdatePersonnelEffortTime.mockResolvedValue({ updated: 1 });
  });

  // A business step whose only personnel row is "hoch" (slot c) under one WZ
  // section, with the dual-write slot mirror filled.
  function businessHochStep(stepId: number, stepLabel: string, section: string, rate: number) {
    return {
      step_id: stepId,
      case_group_id: 22,
      norm_addressee: "business",
      step: stepLabel,
      description: "Beschreibung",
      change_status: "geaendert",
      time_required_in_min_a_current: null,
      time_required_in_min_b_current: null,
      time_required_in_min_c_current: 30,
      time_required_in_min_d_current: null,
      expenses_current: 0,
      time_required_in_min_a_current_edited: null,
      time_required_in_min_b_current_edited: null,
      time_required_in_min_c_current_edited: null,
      time_required_in_min_d_current_edited: null,
      expenses_current_edited: null,
      time_required_in_min_a_proposed: null,
      time_required_in_min_b_proposed: null,
      time_required_in_min_c_proposed: null,
      time_required_in_min_d_proposed: null,
      expenses_proposed: 0,
      time_required_in_min_a_proposed_edited: null,
      time_required_in_min_b_proposed_edited: null,
      time_required_in_min_c_proposed_edited: null,
      time_required_in_min_d_proposed_edited: null,
      expenses_proposed_edited: null,
      time_required_in_min_a_current_effective: null,
      time_required_in_min_b_current_effective: null,
      time_required_in_min_c_current_effective: 30,
      time_required_in_min_d_current_effective: null,
      expenses_current_effective: 0,
      time_required_in_min_a_proposed_effective: null,
      time_required_in_min_b_proposed_effective: null,
      time_required_in_min_c_proposed_effective: null,
      time_required_in_min_d_proposed_effective: null,
      expenses_proposed_effective: 0,
      personnel_effort_current: [
        {
          qualification: "hoch",
          wage_source_kind: "wirtschaftsabschnitt",
          wage_source_value: section,
          model_hourly_rate: rate,
          time_required_in_min: 30,
          time_required_in_min_edited: null,
        },
      ],
      personnel_effort_proposed: [],
    };
  }

  it("shows different WZ sections per step in the same case group", async () => {
    // Validates: a case group CAN contain steps with different economic sectors
    // (the prompt/model do not force one per case group), and the table then
    // labels each step with its own letter -- both fully editable.
    mockGetEditableCaseGroups.mockResolvedValue({
      rows: [{ case_group_id: 22, norm_addressee: "business", process_id: 1, case_group: "FG" }],
    });
    mockGetEditableProcessSteps.mockResolvedValue({
      rows: [
        businessHochStep(301, "Schritt Kunst", "R", 51.0),
        businessHochStep(302, "Schritt Finanz", "K", 93.1),
      ],
    });
    render(
      <EaEffortMetricsTab normAddressee="business" open active appSessionId="STEP-TAB" runAutoRecompute={jest.fn()} />
    );

    const trR = (await screen.findByText("Schritt Kunst")).closest("tr") as HTMLElement;
    const trK = screen.getByText("Schritt Finanz").closest("tr") as HTMLElement;
    // Each step row shows its own WZ section letter.
    expect(within(trR).getByText("· R")).toBeInTheDocument();
    expect(within(trK).getByText("· K")).toBeInTheDocument();
    // Both steps are fully editable (4 qualifications + expenses per side = 10).
    expect(within(trR).getAllByRole("textbox")).toHaveLength(10);
    expect(within(trK).getAllByRole("textbox")).toHaveLength(10);
  });

  it("hides the reserve columns for citizens, showing only Zeit + Sach", async () => {
    // Citizens have no qualifications/wage rates: only slot a (Zeit) and expenses
    // are ever populated, b/c/d are structural placeholders ("Reserve B/C/D").
    // The effort editor must not render those empty columns (Julia, PR #35).
    mockGetEditableCaseGroups.mockResolvedValueOnce({
      rows: [
        {
          case_group_id: 22,
          norm_addressee: "citizens",
          process_id: 1,
          case_group: "Fallgruppe Bürger",
        },
      ],
    });
    mockGetEditableProcessSteps.mockResolvedValueOnce({
      rows: [
        {
          step_id: 401,
          case_group_id: 22,
          norm_addressee: "citizens",
          step: "Schritt Bürger",
          description: "Beschreibung",
          change_status: "geaendert",
          time_required_in_min_a_current: 15,
          time_required_in_min_b_current: null,
          time_required_in_min_c_current: null,
          time_required_in_min_d_current: null,
          expenses_current: 0,
          time_required_in_min_a_current_edited: null,
          time_required_in_min_b_current_edited: null,
          time_required_in_min_c_current_edited: null,
          time_required_in_min_d_current_edited: null,
          expenses_current_edited: null,
          time_required_in_min_a_proposed: 20,
          time_required_in_min_b_proposed: null,
          time_required_in_min_c_proposed: null,
          time_required_in_min_d_proposed: null,
          expenses_proposed: 0,
          time_required_in_min_a_proposed_edited: null,
          time_required_in_min_b_proposed_edited: null,
          time_required_in_min_c_proposed_edited: null,
          time_required_in_min_d_proposed_edited: null,
          expenses_proposed_edited: null,
          time_required_in_min_a_current_effective: 15,
          time_required_in_min_b_current_effective: null,
          time_required_in_min_c_current_effective: null,
          time_required_in_min_d_current_effective: null,
          expenses_current_effective: 0,
          time_required_in_min_a_proposed_effective: 20,
          time_required_in_min_b_proposed_effective: null,
          time_required_in_min_c_proposed_effective: null,
          time_required_in_min_d_proposed_effective: null,
          expenses_proposed_effective: 0,
        },
      ],
    });

    render(
      <EaEffortMetricsTab normAddressee="citizens" open active appSessionId="STEP-TAB" runAutoRecompute={jest.fn()} />
    );

    const tr = (await screen.findByText("Schritt Bürger")).closest("tr") as HTMLElement;
    // Only Zeit + Sach per side = 4 inputs; the Reserve columns are gone.
    expect(within(tr).getAllByRole("textbox")).toHaveLength(4);
    expect(within(tr).queryByText("–")).not.toBeInTheDocument();
    expect(screen.queryByText("Reserve B")).not.toBeInTheDocument();
    expect(screen.queryByText("Reserve C")).not.toBeInTheDocument();
    expect(screen.queryByText("Reserve D")).not.toBeInTheDocument();
    // The meaningful columns stay (one header per side).
    expect(screen.getAllByText("Zeit")).toHaveLength(2);
    expect(screen.getAllByText("Sach")).toHaveLength(2);
  });

  function seedPersonnelStep(overrides: Record<string, unknown> = {}) {
    mockGetEditableProcessSteps.mockResolvedValue({
      rows: [
        {
          step_id: 201,
          case_group_id: 22,
          norm_addressee: "administration",
          step: "Schritt R",
          description: "Beschreibung",
          change_status: "geaendert",
          // Dual-write mirror in the slot columns (slot b = gehobener Dienst).
          time_required_in_min_a_current: null,
          time_required_in_min_b_current: 10,
          time_required_in_min_c_current: null,
          time_required_in_min_d_current: null,
          expenses_current: 0,
          time_required_in_min_a_current_edited: null,
          time_required_in_min_b_current_edited: null,
          time_required_in_min_c_current_edited: null,
          time_required_in_min_d_current_edited: null,
          expenses_current_edited: null,
          time_required_in_min_a_proposed: null,
          time_required_in_min_b_proposed: 8,
          time_required_in_min_c_proposed: null,
          time_required_in_min_d_proposed: null,
          expenses_proposed: 0,
          time_required_in_min_a_proposed_edited: null,
          time_required_in_min_b_proposed_edited: null,
          time_required_in_min_c_proposed_edited: null,
          time_required_in_min_d_proposed_edited: null,
          expenses_proposed_edited: null,
          time_required_in_min_a_current_effective: null,
          time_required_in_min_b_current_effective: 10,
          time_required_in_min_c_current_effective: null,
          time_required_in_min_d_current_effective: null,
          expenses_current_effective: 0,
          time_required_in_min_a_proposed_effective: null,
          time_required_in_min_b_proposed_effective: 8,
          time_required_in_min_c_proposed_effective: null,
          time_required_in_min_d_proposed_effective: null,
          expenses_proposed_effective: 0,
          personnel_effort_current: [
            {
              qualification: "gehobener_dienst",
              wage_source_kind: "verwaltungsebene",
              wage_source_value: "laender",
              model_hourly_rate: 43.2,
              time_required_in_min: 10,
              time_required_in_min_edited: null,
            },
          ],
          personnel_effort_proposed: [
            {
              qualification: "gehobener_dienst",
              wage_source_kind: "verwaltungsebene",
              wage_source_value: "laender",
              model_hourly_rate: 43.2,
              time_required_in_min: 8,
              time_required_in_min_edited: null,
            },
          ],
          ...overrides,
        },
      ],
    });
  }

  it("renders all qualifications editable under the step's single source", async () => {
    seedPersonnelStep();
    render(
      <EaEffortMetricsTab normAddressee="administration" open active appSessionId="STEP-TAB" runAutoRecompute={jest.fn()} />
    );

    const row = await screen.findByText("Schritt R");
    const tr = row.closest("tr") as HTMLElement;
    // 4 qualifications x 2 periods + 2 expenses = 10 editable inputs (like before
    // the redesign): empty qualifications are editable, not dashes.
    const inputs = within(tr).getAllByRole("textbox");
    expect(inputs).toHaveLength(10);
    expect(within(tr).queryByText("–")).not.toBeInTheDocument();
    // The source is shown once on the step, not on every cell.
    expect(within(tr).getAllByText(/Länder/)).toHaveLength(1);
    // Order per period: eD/mD, gD, hD, Ø, expenses. gD is prefilled, eD/mD empty.
    expect(inputs[0]).toHaveValue("");
    expect(inputs[1]).toHaveValue("10");
  });

  it("edits an existing qualification via the row endpoint, not bulk-update", async () => {
    seedPersonnelStep();
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaEffortMetricsTab normAddressee="administration" open active appSessionId="STEP-TAB" runAutoRecompute={runAutoRecompute} />
    );

    const row = await screen.findByText("Schritt R");
    const tr = row.closest("tr") as HTMLElement;
    const inputs = within(tr).getAllByRole("textbox");
    const user = userEvent.setup();
    // inputs[1] = current gD (prefilled 10).
    await user.clear(inputs[1]);
    await user.type(inputs[1], "5");
    await user.click(screen.getByRole("button", { name: /prüfen/i }));
    await user.click(screen.getByRole("button", { name: /änderungen speichern/i }));

    await waitFor(() => expect(mockUpdatePersonnelEffortTime).toHaveBeenCalledTimes(1));
    expect(mockUpdatePersonnelEffortTime).toHaveBeenCalledWith({
      appSessionId: "STEP-TAB",
      normAddressee: "administration",
      stepId: 201,
      period: "current",
      qualification: "gehobener_dienst",
      wageSourceKind: "verwaltungsebene",
      wageSourceValue: "laender",
      timeRequiredInMinEdited: 5,
    });
    expect(mockBulkUpdateProcessSteps).not.toHaveBeenCalled();
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
  });

  it("creates a row when adding time for an unassigned qualification", async () => {
    // Julia: move minutes to a qualification the LLM did not assign. Editing the
    // empty hD column upserts a row under the step's source.
    seedPersonnelStep();
    render(
      <EaEffortMetricsTab normAddressee="administration" open active appSessionId="STEP-TAB" runAutoRecompute={jest.fn()} />
    );

    const row = await screen.findByText("Schritt R");
    const tr = row.closest("tr") as HTMLElement;
    const inputs = within(tr).getAllByRole("textbox");
    const user = userEvent.setup();
    // inputs[2] = current hD (empty, LLM did not assign it).
    await user.type(inputs[2], "20");
    await user.click(screen.getByRole("button", { name: /prüfen/i }));
    await user.click(screen.getByRole("button", { name: /änderungen speichern/i }));

    await waitFor(() => expect(mockUpdatePersonnelEffortTime).toHaveBeenCalledTimes(1));
    expect(mockUpdatePersonnelEffortTime).toHaveBeenCalledWith({
      appSessionId: "STEP-TAB",
      normAddressee: "administration",
      stepId: 201,
      period: "current",
      qualification: "hoeherer_dienst",
      wageSourceKind: "verwaltungsebene",
      wageSourceValue: "laender",
      timeRequiredInMinEdited: 20,
    });
  });

  it("reset clears personnel time edits via the row endpoint", async () => {
    seedPersonnelStep({
      personnel_effort_current: [
        {
          qualification: "gehobener_dienst",
          wage_source_kind: "verwaltungsebene",
          wage_source_value: "laender",
          model_hourly_rate: 43.2,
          time_required_in_min: 10,
          time_required_in_min_edited: 99,
        },
      ],
    });
    const runAutoRecompute = jest.fn().mockResolvedValue(undefined);
    render(
      <EaEffortMetricsTab normAddressee="administration" open active appSessionId="STEP-TAB" runAutoRecompute={runAutoRecompute} />
    );

    await screen.findByText("Schritt R");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /auf modellwerte zurücksetzen/i }));

    await waitFor(() => expect(mockUpdatePersonnelEffortTime).toHaveBeenCalledTimes(1));
    expect(mockUpdatePersonnelEffortTime).toHaveBeenCalledWith(
      expect.objectContaining({
        stepId: 201,
        period: "current",
        timeRequiredInMinEdited: null,
      })
    );
    // No step-level edits exist, so the slot bulk-update is skipped entirely.
    expect(mockBulkUpdateProcessSteps).not.toHaveBeenCalled();
    expect(runAutoRecompute).toHaveBeenCalledTimes(1);
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

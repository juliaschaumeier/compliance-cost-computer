import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import EaEditDrawerShell from "@/components/ea_edit/EaEditDrawerShell";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/api", () => ({
  apiClient: {
    acquireEaEditActivity: jest.fn(),
    heartbeatEaEditActivity: jest.fn(),
    releaseEaEditActivity: jest.fn(),
    computeTotalCost: jest.fn(),
    resetSessionEaEdits: jest.fn(),
  },
}));

jest.mock("@/lib/useMounted", () => ({
  useMounted: () => true,
}));

jest.mock("@/components/ea_edit/EaPayRatesTab", () => ({
  __esModule: true,
  default: ({
    active,
    readOnly,
    runAutoRecompute,
    onDirtyChange,
  }: {
    active: boolean;
    readOnly?: boolean;
    runAutoRecompute: () => Promise<void>;
    onDirtyChange?: (dirty: boolean) => void;
  }) =>
    active ? (
      <>
        <button
          type="button"
          disabled={readOnly}
          onClick={() => {
            void runAutoRecompute().catch(() => undefined);
          }}
        >
          Trigger Recompute
        </button>
        <button type="button" disabled={readOnly} onClick={() => onDirtyChange?.(true)}>
          Mark Dirty
        </button>
        <button type="button" disabled={readOnly} onClick={() => onDirtyChange?.(false)}>
          Mark Clean
        </button>
      </>
    ) : null,
}));

jest.mock("@/components/ea_edit/EaCaseMetricsTab", () => ({
  __esModule: true,
  default: ({
    active,
    readOnly,
    onDirtyChange,
  }: {
    active: boolean;
    readOnly?: boolean;
    onDirtyChange?: (dirty: boolean) => void;
  }) =>
    active ? (
      <>
        <button type="button" disabled={readOnly} onClick={() => onDirtyChange?.(true)}>
          Mark Case Dirty
        </button>
        <button type="button" disabled={readOnly} onClick={() => onDirtyChange?.(false)}>
          Mark Case Clean
        </button>
      </>
    ) : null,
}));

jest.mock("@/components/ea_edit/EaEffortMetricsTab", () => ({
  __esModule: true,
  default: ({
    active,
    readOnly,
    onDirtyChange,
  }: {
    active: boolean;
    readOnly?: boolean;
    onDirtyChange?: (dirty: boolean) => void;
  }) =>
    active ? (
      <>
        <button type="button" disabled={readOnly} onClick={() => onDirtyChange?.(true)}>
          Mark Effort Dirty
        </button>
        <button type="button" disabled={readOnly} onClick={() => onDirtyChange?.(false)}>
          Mark Effort Clean
        </button>
      </>
    ) : null,
}));

const mockUseApp = useApp as jest.Mock;
const mockAcquireEaEditActivity = apiClient.acquireEaEditActivity as jest.Mock;
const mockHeartbeatEaEditActivity = apiClient.heartbeatEaEditActivity as jest.Mock;
const mockReleaseEaEditActivity = apiClient.releaseEaEditActivity as jest.Mock;
const mockComputeTotalCost = apiClient.computeTotalCost as jest.Mock;
const mockResetSessionEaEdits = apiClient.resetSessionEaEdits as jest.Mock;

describe("EaEditDrawerShell", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockAcquireEaEditActivity.mockReset();
    mockHeartbeatEaEditActivity.mockReset();
    mockReleaseEaEditActivity.mockReset();
    mockComputeTotalCost.mockReset();
    mockResetSessionEaEdits.mockReset();
    mockAcquireEaEditActivity.mockReturnValue(new Promise(() => undefined));
    mockHeartbeatEaEditActivity.mockResolvedValue({
      app_session_id: "EA-TEST",
      activity_id: "ea_edit:test",
      lease_seconds: 120,
      expires_at: 456,
    });
    mockReleaseEaEditActivity.mockResolvedValue({ ok: true });
    mockResetSessionEaEdits.mockResolvedValue({
      app_session_id: "EA-TEST",
      reset_counts: { pay_rates: 1, case_groups: 2, process_steps: 3 },
      recomputed_norm_addressees: ["administration", "business", "citizens"],
    });
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "EA-TEST",
        selectedNormAddressee: "administration",
        isComplianceExportRunning: false,
      },
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const waitForEaActivity = async () => {
    await waitFor(() =>
      expect(
        screen.getByRole("button", {
          name: /alle ea-werte auf modellwerte zurücksetzen/i,
        })
      ).toBeEnabled()
    );
  };

  const mockSuccessfulActivityAcquire = () => {
    mockAcquireEaEditActivity.mockResolvedValue({
      app_session_id: "EA-TEST",
      activity_id: "ea_edit:test",
      lease_seconds: 120,
      expires_at: 123,
    });
  };

  it("debounces recompute calls to a single provider call", async () => {
    mockSuccessfulActivityAcquire();
    mockComputeTotalCost.mockResolvedValue({ total_cost: 1 });
    render(<EaEditDrawerShell open onClose={jest.fn()} />);
    await waitForEaActivity();
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    const button = screen.getByRole("button", { name: /trigger recompute/i });

    await user.click(button);
    await user.click(button);
    await user.click(button);

    expect(mockComputeTotalCost).toHaveBeenCalledTimes(0);
    await act(async () => {
      jest.advanceTimersByTime(400);
    });
    await waitFor(() => expect(mockComputeTotalCost).toHaveBeenCalledTimes(1));
    expect(mockComputeTotalCost).toHaveBeenCalledWith({
      appSessionId: "EA-TEST",
      normAddressee: "administration",
      eaActivityId: "ea_edit:test",
    });
  });

  it("releases the EA activity when the drawer closes", async () => {
    mockSuccessfulActivityAcquire();
    const { rerender } = render(<EaEditDrawerShell open onClose={jest.fn()} />);

    await waitFor(() => expect(mockAcquireEaEditActivity).toHaveBeenCalledTimes(1));
    rerender(<EaEditDrawerShell open={false} onClose={jest.fn()} />);

    await waitFor(() =>
      expect(mockReleaseEaEditActivity).toHaveBeenCalledWith({
        appSessionId: "EA-TEST",
        activityId: "ea_edit:test",
      })
    );
  });

  it("stops the heartbeat loop after a heartbeat failure", async () => {
    mockSuccessfulActivityAcquire();
    mockHeartbeatEaEditActivity.mockRejectedValue(new Error("activity expired"));
    render(<EaEditDrawerShell open onClose={jest.fn()} />);

    await waitForEaActivity();
    await act(async () => {
      jest.advanceTimersByTime(30_000);
    });

    expect(
      await screen.findByText(/ea-bearbeitung ist nicht mehr aktiv/i)
    ).toBeInTheDocument();
    expect(mockHeartbeatEaEditActivity).toHaveBeenCalledTimes(1);

    await act(async () => {
      jest.advanceTimersByTime(90_000);
    });

    expect(mockHeartbeatEaEditActivity).toHaveBeenCalledTimes(1);
  });

  it("keeps a same-session EA conflict drawer inspectable but read-only", async () => {
    const onClose = jest.fn();
    const error = Object.assign(new Error("conflict"), {
      status: 409,
      details: {
        error: "session_activity_conflict",
        active_type: "ea_edit",
        message: "Backend conflict text",
      },
    });
    mockAcquireEaEditActivity.mockRejectedValue(error);
    render(<EaEditDrawerShell open onClose={onClose} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    expect(
      await screen.findByText(/ander(en)? tab oder fenster/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /mark dirty/i })).toBeDisabled();
    expect(
      screen.getByRole("button", {
        name: /alle ea-werte auf modellwerte zurücksetzen/i,
      })
    ).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /fallzahlen/i }));
    expect(screen.getByRole("button", { name: /mark case dirty/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByRole("dialog", { name: /ungespeicherte änderungen/i })
    ).not.toBeInTheDocument();
  });

  it("uses the workflow conflict state for blocked EA editing", async () => {
    const error = Object.assign(new Error("conflict"), {
      status: 409,
      details: {
        error: "session_activity_conflict",
        active_type: "workflow",
        message: "Backend workflow conflict text",
      },
    });
    mockAcquireEaEditActivity.mockRejectedValue(error);

    render(<EaEditDrawerShell open onClose={jest.fn()} />);

    expect(
      await screen.findByText(/laufenden ausführung in dieser session/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /mark dirty/i })).toBeDisabled();
  });

  it("keeps one in-flight recompute request per session", async () => {
    mockSuccessfulActivityAcquire();
    let resolveFirst: (() => void) | null = null;
    mockComputeTotalCost.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveFirst = resolve;
        })
    );

    render(<EaEditDrawerShell open onClose={jest.fn()} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();
    const button = screen.getByRole("button", { name: /trigger recompute/i });

    await user.click(button);
    await act(async () => {
      jest.advanceTimersByTime(400);
    });
    expect(mockComputeTotalCost).toHaveBeenCalledTimes(1);

    await user.click(button);
    await act(async () => {
      jest.advanceTimersByTime(400);
    });
    expect(mockComputeTotalCost).toHaveBeenCalledTimes(1);

    resolveFirst?.();
    await waitFor(() => expect(mockComputeTotalCost).toHaveBeenCalledTimes(1));
  });

  it("shows a status message on recompute failure", async () => {
    mockSuccessfulActivityAcquire();
    mockComputeTotalCost.mockRejectedValue(new Error("boom"));
    render(<EaEditDrawerShell open onClose={jest.fn()} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();
    const button = screen.getByRole("button", { name: /trigger recompute/i });

    await user.click(button);
    await act(async () => {
      jest.advanceTimersByTime(400);
    });

    expect(
      await screen.findByText(/automatische neuberechnung der gesamtkosten ist fehlgeschlagen/i)
    ).toBeInTheDocument();
  });

  it("shows close guard modal when unsaved changes exist", async () => {
    mockSuccessfulActivityAcquire();
    const onClose = jest.fn();
    render(<EaEditDrawerShell open onClose={onClose} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();

    await user.click(screen.getByRole("button", { name: /mark dirty/i }));
    await user.click(screen.getByRole("button", { name: /^schließen$/i }));

    expect(
      await screen.findByRole("button", { name: /weiter bearbeiten/i })
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /weiter bearbeiten/i }));
    expect(screen.queryByText(/ungespeicherte änderungen/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    await user.click(screen.getByRole("button", { name: /verwerfen & schließen/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes immediately when no unsaved changes exist", async () => {
    const onClose = jest.fn();
    render(<EaEditDrawerShell open onClose={onClose} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    await user.click(screen.getByRole("button", { name: /^schließen$/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: /weiter bearbeiten/i })).not.toBeInTheDocument();
  });

  it("uses non-blocking backdrop pointer events so graph can stay interactive", () => {
    render(<EaEditDrawerShell open onClose={jest.fn()} />);

    const overlay = document.querySelector("div.pointer-events-none.fixed.inset-0.z-\\[85\\]");
    expect(overlay).toBeTruthy();
    const panel = screen
      .getByText("Erfüllungsaufwand bearbeiten für Verwaltung")
      .closest("section");
    expect(panel).toHaveClass("pointer-events-auto");
  });

  it("prompts to review dirty tabs on save-and-close", async () => {
    mockSuccessfulActivityAcquire();
    const onClose = jest.fn();
    render(<EaEditDrawerShell open onClose={onClose} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();

    await user.click(screen.getByRole("button", { name: /mark dirty/i }));
    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    await user.click(screen.getByRole("button", { name: /zum speichern führen/i }));

    expect(onClose).not.toHaveBeenCalled();
    expect(
      await screen.findByText(/bitte zuerst prüfen und speichern in/i)
    ).toBeInTheDocument();
  });

  it("clears save guidance hint once all dirty tabs are clean", async () => {
    mockSuccessfulActivityAcquire();
    const onClose = jest.fn();
    render(<EaEditDrawerShell open onClose={onClose} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();

    await user.click(screen.getByRole("button", { name: /mark dirty/i }));
    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    await user.click(screen.getByRole("button", { name: /zum speichern führen/i }));
    expect(
      await screen.findByText(/bitte zuerst prüfen und speichern in/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /mark clean/i }));
    await waitFor(() =>
      expect(
        screen.queryByText(/bitte zuerst prüfen und speichern in/i)
      ).not.toBeInTheDocument()
    );
  });

  it("lists all dirty tabs and switches to the first dirty tab on save-and-close", async () => {
    mockSuccessfulActivityAcquire();
    const onClose = jest.fn();
    render(<EaEditDrawerShell open onClose={onClose} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();

    await user.click(screen.getByRole("button", { name: /fallzahlen/i }));
    await user.click(screen.getByRole("button", { name: /mark case dirty/i }));
    await user.click(screen.getByRole("button", { name: /schrittkosten/i }));
    await user.click(screen.getByRole("button", { name: /mark effort dirty/i }));
    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    await user.click(screen.getByRole("button", { name: /zum speichern führen/i }));

    expect(onClose).not.toHaveBeenCalled();
    expect(
      await screen.findByText(/fallzahlen, schrittkosten/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/bearbeite betroffene und häufigkeit je fallgruppe/i)
    ).toBeInTheDocument();
  });

  it("keeps save guidance for remaining dirty tabs when one tab is cleaned", async () => {
    mockSuccessfulActivityAcquire();
    const onClose = jest.fn();
    render(<EaEditDrawerShell open onClose={onClose} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();

    await user.click(screen.getByRole("button", { name: /fallzahlen/i }));
    await user.click(screen.getByRole("button", { name: /mark case dirty/i }));
    await user.click(screen.getByRole("button", { name: /schrittkosten/i }));
    await user.click(screen.getByRole("button", { name: /mark effort dirty/i }));
    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    await user.click(screen.getByRole("button", { name: /zum speichern führen/i }));

    expect(
      await screen.findByText(/fallzahlen, schrittkosten/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /mark case clean/i }));
    await waitFor(() =>
      expect(
        screen.getByText(/prüfen und speichern in: schrittkosten/i)
      ).toBeInTheDocument()
    );
    expect(screen.queryByText(/fallzahlen, schrittkosten/i)).not.toBeInTheDocument();
  });

  it("focuses 'Weiter bearbeiten' and closes modal on Escape", async () => {
    mockSuccessfulActivityAcquire();
    render(<EaEditDrawerShell open onClose={jest.fn()} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();

    await user.click(screen.getByRole("button", { name: /mark dirty/i }));
    await user.click(screen.getByRole("button", { name: /^schließen$/i }));

    const continueButton = await screen.findByRole("button", {
      name: /weiter bearbeiten/i,
    });
    expect(continueButton).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("resets dirty close guard when session changes", async () => {
    mockSuccessfulActivityAcquire();
    const onClose = jest.fn();
    let sessionId = "EA-TEST";
    mockUseApp.mockImplementation(() => ({
      state: { appSessionId: sessionId },
    }));
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    const { rerender } = render(<EaEditDrawerShell open onClose={onClose} />);
    await waitForEaActivity();

    await user.click(screen.getByRole("button", { name: /mark dirty/i }));
    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    expect(
      await screen.findByRole("dialog", { name: /ungespeicherte änderungen/i })
    ).toBeInTheDocument();

    sessionId = "EA-NEW";
    rerender(<EaEditDrawerShell open onClose={onClose} />);

    await user.click(screen.getByRole("button", { name: /^schließen$/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("blocks EA editing while compliance export generation is running", () => {
    mockUseApp.mockReturnValue({
      state: {
        appSessionId: "EA-TEST",
        selectedNormAddressee: "administration",
        isComplianceExportRunning: true,
      },
    });

    render(<EaEditDrawerShell open onClose={jest.fn()} />);

    expect(
      screen.getByText(/vorblatt\/begründung wird gerade erzeugt/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/bitte warte, bis die pdf-erstellung abgeschlossen ist/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /trigger recompute/i })
    ).not.toBeInTheDocument();
  });

  it("resets all EA edits after explicit confirmation", async () => {
    mockSuccessfulActivityAcquire();
    const dispatchSpy = jest.spyOn(window, "dispatchEvent");
    render(<EaEditDrawerShell open onClose={jest.fn()} />);
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    await waitForEaActivity();

    await user.click(
      screen.getByRole("button", {
        name: /alle ea-werte auf modellwerte zurücksetzen/i,
      })
    );

    expect(
      await screen.findByRole("dialog", {
        name: /alle ea-werte auf modellwerte zurücksetzen/i,
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/lohnsätze, fallzahlen und schrittkosten für alle normadressaten/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^zurücksetzen$/i }));

    await waitFor(() =>
      expect(mockResetSessionEaEdits).toHaveBeenCalledWith({
        appSessionId: "EA-TEST",
        eaActivityId: "ea_edit:test",
      })
    );
    expect(dispatchSpy).toHaveBeenCalledWith(expect.objectContaining({ type: "tiles-updated" }));
    expect(
      await screen.findByText(/alle ea-bearbeitungen wurden auf modellwerte zurückgesetzt/i)
    ).toBeInTheDocument();
    dispatchSpy.mockRestore();
  });

  it("clears the global reset status when the drawer is reopened", async () => {
    mockSuccessfulActivityAcquire();
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    const { rerender } = render(<EaEditDrawerShell open onClose={jest.fn()} />);
    await waitForEaActivity();

    await user.click(
      screen.getByRole("button", {
        name: /alle ea-werte auf modellwerte zurücksetzen/i,
      })
    );
    await user.click(screen.getByRole("button", { name: /^zurücksetzen$/i }));
    expect(
      await screen.findByText(/alle ea-bearbeitungen wurden auf modellwerte zurückgesetzt/i)
    ).toBeInTheDocument();

    rerender(<EaEditDrawerShell open={false} onClose={jest.fn()} />);
    mockAcquireEaEditActivity.mockReturnValue(new Promise(() => undefined));
    rerender(<EaEditDrawerShell open onClose={jest.fn()} />);

    expect(
      screen.queryByText(/alle ea-bearbeitungen wurden auf modellwerte zurückgesetzt/i)
    ).not.toBeInTheDocument();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import TabBar from "@/components/TabBar";
import { useApp } from "@/contexts/AppContext";
import { isLlmConsoleEnabled } from "@/lib/llmConsoleConfig";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/llmConsoleConfig", () => ({
  isLlmConsoleEnabled: jest.fn(),
}));

jest.mock("@/components/SessionMenu", () => ({
  __esModule: true,
  default: ({ compact }: { compact?: boolean }) => (
    <div data-testid={compact ? "session-menu-compact" : "session-menu"} />
  ),
}));

jest.mock("@/components/LlmMonitorConsole", () => ({
  __esModule: true,
  default: ({
    open,
    onClose,
  }: {
    open: boolean;
    onClose: () => void;
  }) => (
    <div data-testid="llm-console" data-open={open ? "true" : "false"}>
      <button type="button" onClick={onClose}>
        Close Console
      </button>
    </div>
  ),
}));

const mockUseApp = useApp as jest.Mock;
const mockIsLlmConsoleEnabled = isLlmConsoleEnabled as jest.Mock;

describe("TabBar LLM console button", () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      state: {
        currentTab: 0,
        summaryReady: false,
        regulationsReady: false,
        processesReady: false,
        caseGroupsReady: false,
        processStepsReady: false,
        effortReady: false,
        totalCostReady: false,
      },
      setCurrentTab: jest.fn(),
    });
    mockIsLlmConsoleEnabled.mockReturnValue(true);
  });

  it("toggles console open/close via the floating button", async () => {
    render(<TabBar />);

    const user = userEvent.setup();
    const toggleButton = await screen.findByRole("button", {
      name: /llm konsole öffnen/i,
    });
    expect(screen.getByTestId("llm-console")).toHaveAttribute("data-open", "false");

    await user.click(toggleButton);
    await waitFor(() =>
      expect(screen.getByTestId("llm-console")).toHaveAttribute("data-open", "true")
    );

    const closeToggleButton = screen.getByRole("button", {
      name: /llm konsole schließen/i,
    });
    await user.click(closeToggleButton);
    await waitFor(() =>
      expect(screen.getByTestId("llm-console")).toHaveAttribute("data-open", "false")
    );
  });

  it("hides floating button when config disables console", () => {
    mockIsLlmConsoleEnabled.mockReturnValue(false);

    render(<TabBar />);

    expect(
      screen.queryByRole("button", { name: /llm konsole/i })
    ).not.toBeInTheDocument();
  });

  it("does not strongly highlight the final step once total costs are ready", () => {
    mockUseApp.mockReturnValue({
      state: {
        currentTab: 6,
        summaryReady: true,
        regulationsReady: true,
        processesReady: true,
        caseGroupsReady: true,
        processStepsReady: true,
        effortReady: true,
        totalCostReady: true,
      },
      setCurrentTab: jest.fn(),
    });

    render(<TabBar />);

    const finalStep = screen.getByRole("button", {
      name: /gesamtkosten berechnen/i,
    });
    expect(finalStep).not.toHaveClass("bg-slate-800");
    expect(finalStep).toHaveClass("bg-white");
    expect(finalStep).toHaveClass("opacity-50");
  });
});

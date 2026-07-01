"use client";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import WorkflowControls from "@/components/WorkflowControls";
import { useApp } from "@/contexts/AppContext";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/components/ea_edit/EaEditDrawerShell", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) => (
    <div data-testid="ea-drawer" data-open={open ? "true" : "false"} />
  ),
}));

const mockUseApp = useApp as jest.Mock;

describe("WorkflowControls", () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        effortReady: false,
        totalCostReady: false,
      },
      setSelectedNormAddressee: jest.fn(),
    });
  });

  it("renders the norm addressee menu and switches the selected view", async () => {
    const setSelectedNormAddressee = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        effortReady: false,
        totalCostReady: false,
      },
      setSelectedNormAddressee,
    });

    render(<WorkflowControls />);
    const user = userEvent.setup();

    const trigger = screen.getByRole("button", {
      name: "Normadressat-Ansicht auswählen",
    });
    expect(trigger).toHaveTextContent("Verwaltung");
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    await user.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Bürger:innen",
      "Wirtschaft",
      "Verwaltung",
    ]);
    expect(screen.getByRole("option", { name: "Verwaltung" })).toHaveAttribute(
      "aria-selected",
      "true"
    );

    await user.click(screen.getByRole("option", { name: "Wirtschaft" }));
    expect(setSelectedNormAddressee).toHaveBeenCalledWith("business");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("enables the EA button once effort is ready", () => {
    const { rerender } = render(<WorkflowControls />);

    expect(
      screen.getByRole("button", { name: /ea bearbeiten/i })
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: /ea bearbeiten/i })).toHaveClass(
      "opacity-60"
    );

    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "citizens",
        effortReady: true,
        totalCostReady: false,
      },
      setSelectedNormAddressee: jest.fn(),
    });

    rerender(<WorkflowControls />);

    expect(
      screen.getByRole("button", { name: /ea bearbeiten/i })
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: /ea bearbeiten/i })
    ).not.toHaveClass("opacity-60");
  });

  it("keeps the EA drawer open when only total cost readiness is reset", async () => {
    const setSelectedNormAddressee = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        effortReady: true,
        totalCostReady: true,
      },
      setSelectedNormAddressee,
    });
    const user = userEvent.setup();
    const { rerender } = render(<WorkflowControls />);

    await user.click(screen.getByRole("button", { name: /ea bearbeiten/i }));
    expect(screen.getByTestId("ea-drawer")).toHaveAttribute("data-open", "true");

    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        effortReady: true,
        totalCostReady: false,
      },
      setSelectedNormAddressee,
    });
    rerender(<WorkflowControls />);

    expect(screen.getByTestId("ea-drawer")).toHaveAttribute("data-open", "true");
  });

  it("closes the EA drawer when effort readiness is reset", async () => {
    const setSelectedNormAddressee = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        effortReady: true,
        totalCostReady: false,
      },
      setSelectedNormAddressee,
    });
    const user = userEvent.setup();
    const { rerender } = render(<WorkflowControls />);

    await user.click(screen.getByRole("button", { name: /ea bearbeiten/i }));
    expect(screen.getByTestId("ea-drawer")).toHaveAttribute("data-open", "true");

    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        effortReady: false,
        totalCostReady: false,
      },
      setSelectedNormAddressee,
    });
    rerender(<WorkflowControls />);

    expect(screen.getByTestId("ea-drawer")).toHaveAttribute("data-open", "false");
  });
});

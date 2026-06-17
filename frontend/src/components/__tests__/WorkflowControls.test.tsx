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
        totalCostReady: false,
      },
      setSelectedNormAddressee: jest.fn(),
    });
  });

  it("renders the norm addressee dropdown and switches the selected view", async () => {
    const setSelectedNormAddressee = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        totalCostReady: false,
      },
      setSelectedNormAddressee,
    });

    render(<WorkflowControls />);
    const user = userEvent.setup();

    const select = screen.getByLabelText("Normadressat-Ansicht auswählen");
    expect(select).toHaveValue("administration");
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Bürger:innen",
      "Wirtschaft",
      "Verwaltung",
    ]);

    await user.selectOptions(select, "business");
    expect(setSelectedNormAddressee).toHaveBeenCalledWith("business");
  });

  it("enables the EA button only when total cost is ready", () => {
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
        totalCostReady: true,
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

  it("closes the EA drawer when total cost readiness is reset", async () => {
    const setSelectedNormAddressee = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
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
        totalCostReady: false,
      },
      setSelectedNormAddressee,
    });
    rerender(<WorkflowControls />);

    expect(screen.getByTestId("ea-drawer")).toHaveAttribute("data-open", "false");
  });
});

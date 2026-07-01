"use client";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Header from "@/components/Header";
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

jest.mock("@/components/ModelSelector", () => ({
  __esModule: true,
  default: () => <div data-testid="model-selector" />,
}));

const mockUseApp = useApp as jest.Mock;

describe("Header norm addressee switch", () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        totalCostReady: false,
      },
      setSelectedNormAddressee: jest.fn(),
    });
  });

  it("renders all three norm addressee options and switches to the clicked one", async () => {
    const setSelectedNormAddressee = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        totalCostReady: false,
      },
      setSelectedNormAddressee,
    });

    render(<Header />);
    const user = userEvent.setup();

    expect(screen.getByRole("button", { name: "Verwaltung" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Wirtschaft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bürger" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Wirtschaft" }));
    await user.click(screen.getByRole("button", { name: "Bürger" }));

    expect(setSelectedNormAddressee).toHaveBeenNthCalledWith(1, "business");
    expect(setSelectedNormAddressee).toHaveBeenNthCalledWith(2, "citizens");
  });

  it("enables the EA button only when total cost is ready", () => {
    const { rerender } = render(<Header />);

    expect(
      screen.getByRole("button", { name: /ea bearbeiten/i })
    ).toBeDisabled();

    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "citizens",
        totalCostReady: true,
      },
      setSelectedNormAddressee: jest.fn(),
    });

    rerender(<Header />);

    expect(
      screen.getByRole("button", { name: /ea bearbeiten/i })
    ).toBeEnabled();
  });

  it("closes the EA drawer when total cost readiness is reset", async () => {
    const user = userEvent.setup();
    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        totalCostReady: true,
      },
      setSelectedNormAddressee: jest.fn(),
    });
    const { rerender } = render(<Header />);

    await user.click(screen.getByRole("button", { name: /ea bearbeiten/i }));
    expect(screen.getByTestId("ea-drawer")).toHaveAttribute("data-open", "true");

    mockUseApp.mockReturnValue({
      state: {
        selectedNormAddressee: "administration",
        totalCostReady: false,
      },
      setSelectedNormAddressee: jest.fn(),
    });
    rerender(<Header />);

    expect(screen.getByTestId("ea-drawer")).toHaveAttribute("data-open", "false");
  });
});

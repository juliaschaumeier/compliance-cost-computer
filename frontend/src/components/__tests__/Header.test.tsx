import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Header from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: jest.fn(),
}));

jest.mock("@/components/SessionMenu", () => ({
  __esModule: true,
  default: () => <div data-testid="session-menu" />,
}));

jest.mock("@/components/AdminUsersPanel", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) => (
    <div data-testid="admin-panel" data-open={open ? "true" : "false"} />
  ),
}));

jest.mock("@/components/ModelSelector", () => ({
  __esModule: true,
  default: () => <div data-testid="model-selector" />,
}));

jest.mock("@/components/HeaderHelpPopover", () => ({
  __esModule: true,
  default: () => <button type="button">Hilfe und Demo</button>,
}));

const mockUseAuth = useAuth as jest.Mock;

describe("Header", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: { user_id: 1, email: "user@example.com", is_admin: false },
      logout: jest.fn().mockResolvedValue(undefined),
    });
  });

  it("renders app context and global session tools", () => {
    render(<Header />);

    expect(
      screen.getByRole("heading", { name: "Compliance-Cost Computer" })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Errechnet den jährlichen Erfüllungsaufwand einer Gesetzesänderung."
      )
    ).toBeInTheDocument();
    expect(screen.getByTestId("session-menu")).toBeInTheDocument();
    expect(screen.getByTestId("model-selector")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Hilfe und Demo" })
    ).toBeInTheDocument();
  });

  it("shows the user email in the account menu and calls logout there", async () => {
    const logout = jest.fn().mockResolvedValue(undefined);
    mockUseAuth.mockReturnValue({
      user: { user_id: 7, email: "ada@example.com", is_admin: false },
      logout,
    });

    render(<Header />);
    const user = userEvent.setup();

    expect(screen.queryByText("ada@example.com")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Benutzerverwaltung" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Benutzerkonto öffnen" }));
    expect(screen.getByText("ada@example.com")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /abmelden/i }));
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it("shows the admin users button only for admins", () => {
    mockUseAuth.mockReturnValue({
      user: { user_id: 1, email: "root@example.com", is_admin: true },
      logout: jest.fn().mockResolvedValue(undefined),
    });

    render(<Header />);

    expect(
      screen.getByRole("button", { name: "Benutzerverwaltung" })
    ).toBeInTheDocument();
  });
});

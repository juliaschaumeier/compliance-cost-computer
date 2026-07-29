import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AdminUsersPanel from "@/components/AdminUsersPanel";
import { apiClient } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  apiClient: {
    listUsers: jest.fn(),
    createUser: jest.fn(),
    updateUser: jest.fn(),
  },
}));

const mockListUsers = apiClient.listUsers as jest.Mock;
const mockCreateUser = apiClient.createUser as jest.Mock;
const mockUpdateUser = apiClient.updateUser as jest.Mock;

describe("AdminUsersPanel", () => {
  beforeEach(() => {
    mockListUsers.mockReset();
    mockCreateUser.mockReset();
    mockUpdateUser.mockReset();
    mockListUsers.mockResolvedValue([
      {
        user_id: 1,
        email: "admin@example.com",
        is_admin: true,
        is_active: true,
        created_at: "2026-07-17",
        total_estimated_cost_usd: 1.23,
        missing_estimated_cost_count: 0,
      },
      {
        user_id: 2,
        email: "member@example.com",
        is_admin: false,
        is_active: true,
        created_at: "2026-07-17",
        total_estimated_cost_usd: 0.0042,
        missing_estimated_cost_count: 1,
      },
    ]);
    mockCreateUser.mockResolvedValue({
      user_id: 3,
      email: "new@example.com",
      is_admin: false,
      is_active: true,
    });
    mockUpdateUser.mockResolvedValue({
      user_id: 2,
      email: "member@example.com",
      is_admin: false,
      is_active: true,
    });
  });

  it("reveals and hides the new-user password field", async () => {
    const user = userEvent.setup();
    render(<AdminUsersPanel open onClose={jest.fn()} />);

    const input = await screen.findByLabelText("Passwort (min. 8 Zeichen)", {
      selector: "input",
    });
    expect(input).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: "Passwort anzeigen" }));
    expect(input).toHaveAttribute("type", "text");

    await user.click(screen.getByRole("button", { name: "Passwort verbergen" }));
    expect(input).toHaveAttribute("type", "password");
  });

  it("resets an existing user's password", async () => {
    const user = userEvent.setup();
    render(<AdminUsersPanel open onClose={jest.fn()} />);

    const member = await screen.findByText("member@example.com");
    const row = member.closest("li");
    expect(row).not.toBeNull();

    await user.click(
      within(row as HTMLElement).getByRole("button", {
        name: "Passwort zurücksetzen",
      })
    );
    await user.type(
      within(row as HTMLElement).getByLabelText("Neues Passwort"),
      "new-password-123"
    );
    await user.click(within(row as HTMLElement).getByRole("button", { name: "Speichern" }));

    await waitFor(() =>
      expect(mockUpdateUser).toHaveBeenCalledWith(2, {
        password: "new-password-123",
      })
    );
    expect(await screen.findByText("Passwort zurückgesetzt.")).toBeInTheDocument();
  });

  it("shows compact user cost pills and marks incomplete estimates", async () => {
    render(<AdminUsersPanel open onClose={jest.fn()} />);

    const admin = await screen.findByText("admin@example.com");
    const adminRow = admin.closest("li");
    expect(adminRow).not.toBeNull();
    const adminCost = within(adminRow as HTMLElement).getByText("1,23 $");
    expect(adminCost).toHaveClass("ccc-status-success");
    expect(adminCost).toHaveAttribute(
      "aria-label",
      "Geschätzte Nutzungskosten 1,23 $, vollständig"
    );

    const member = await screen.findByText("member@example.com");
    const memberRow = member.closest("li");
    expect(memberRow).not.toBeNull();
    const memberCost = within(memberRow as HTMLElement).getByText("0,0042 $");
    expect(memberCost).toHaveClass("bg-slate-100");
    expect(memberCost).toHaveClass("text-slate-600");
    expect(memberCost).toHaveAttribute(
      "aria-label",
      "Geschätzte Nutzungskosten 0,0042 $, unvollständig"
    );
  });
});

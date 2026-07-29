import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import LoginForm from "@/components/LoginForm";
import { useAuth } from "@/contexts/AuthContext";
import { AUTH_EXPIRED_MESSAGE } from "@/lib/authExpired";

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: jest.fn(),
}));

const mockUseAuth = useAuth as jest.Mock;

describe("LoginForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows the auth-expired notice from the auth context", () => {
    mockUseAuth.mockReturnValue({
      authNotice: AUTH_EXPIRED_MESSAGE,
      clearAuthNotice: jest.fn(),
      login: jest.fn(),
    });

    render(<LoginForm />);

    expect(screen.getByText(AUTH_EXPIRED_MESSAGE)).toBeInTheDocument();
  });

  it("clears an expired-login notice before submitting new credentials", async () => {
    const clearAuthNotice = jest.fn();
    const login = jest.fn().mockRejectedValue(
      Object.assign(new Error("Unauthorized"), { status: 401 })
    );
    mockUseAuth.mockReturnValue({
      authNotice: AUTH_EXPIRED_MESSAGE,
      clearAuthNotice,
      login,
    });

    render(<LoginForm />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/e-mail/i), "ada@example.com");
    await user.type(screen.getByLabelText(/passwort/i), "wrong");
    await user.click(screen.getByRole("button", { name: /anmelden/i }));

    expect(clearAuthNotice).toHaveBeenCalledTimes(1);
    expect(login).toHaveBeenCalledWith("ada@example.com", "wrong");
    await waitFor(() => {
      expect(
        screen.getByText("E-Mail oder Passwort ist ungültig.")
      ).toBeInTheDocument();
    });
  });
});

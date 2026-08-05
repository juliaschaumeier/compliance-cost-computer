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

    expect(screen.getByTestId("login-screen")).toHaveClass("fixed", "inset-0");
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
    await user.click(screen.getByRole("checkbox", { name: /keine vertraulichen texte/i }));
    await user.click(screen.getByRole("button", { name: /anmelden/i }));

    expect(clearAuthNotice).toHaveBeenCalledTimes(1);
    expect(login).toHaveBeenCalledWith("ada@example.com", "wrong");
    await waitFor(() => {
      expect(
        screen.getByText("E-Mail oder Passwort ist ungültig.")
      ).toBeInTheDocument();
    });
  });

  it("requires the confidentiality acknowledgement before login", async () => {
    const login = jest.fn();
    mockUseAuth.mockReturnValue({
      authNotice: null,
      clearAuthNotice: jest.fn(),
      login,
    });

    render(<LoginForm />);
    const user = userEvent.setup();
    const submit = screen.getByRole("button", { name: /anmelden/i });
    const acknowledgement = screen.getByRole("checkbox", {
      name: /keine vertraulichen texte/i,
    });

    expect(acknowledgement).not.toBeChecked();
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText(/e-mail/i), "ada@example.com");
    await user.type(screen.getByLabelText(/passwort/i), "secret123");
    expect(submit).toBeDisabled();

    await user.click(acknowledgement);
    expect(submit).toBeEnabled();

    await user.click(submit);
    expect(login).toHaveBeenCalledWith("ada@example.com", "secret123");
  });

  it("resets the confidentiality acknowledgement after successful login", async () => {
    const login = jest.fn().mockResolvedValue(undefined);
    mockUseAuth.mockReturnValue({
      authNotice: null,
      clearAuthNotice: jest.fn(),
      login,
    });

    render(<LoginForm />);
    const user = userEvent.setup();
    const acknowledgement = screen.getByRole("checkbox", {
      name: /keine vertraulichen texte/i,
    });

    await user.type(screen.getByLabelText(/e-mail/i), "ada@example.com");
    await user.type(screen.getByLabelText(/passwort/i), "secret123");
    await user.click(acknowledgement);
    await user.click(screen.getByRole("button", { name: /anmelden/i }));

    await waitFor(() => {
      expect(acknowledgement).not.toBeChecked();
    });
  });
});

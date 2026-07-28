import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/lib/api";
import { AUTH_EXPIRED_MESSAGE, notifyAuthExpired } from "@/lib/authExpired";

jest.mock("@/lib/api", () => ({
  apiClient: {
    getMe: jest.fn(),
    login: jest.fn(),
    logout: jest.fn(),
  },
}));

function AuthProbe() {
  const { authNotice, user, loading, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="loading">{loading ? "loading" : "ready"}</div>
      <div data-testid="user">{user ? user.email : "anon"}</div>
      <div data-testid="auth-notice">{authNotice || "none"}</div>
      <button onClick={() => login("ada@example.com", "secret123")}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
  });

  it("loads the current user on mount", async () => {
    (apiClient.getMe as jest.Mock).mockResolvedValue({
      user_id: 1,
      email: "ada@example.com",
      is_admin: false,
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("ready");
    });
    expect(screen.getByTestId("user").textContent).toBe("ada@example.com");
  });

  it("treats a 401 from getMe as logged out", async () => {
    (apiClient.getMe as jest.Mock).mockRejectedValue(
      Object.assign(new Error("Unauthorized"), { status: 401 })
    );

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("ready");
    });
    expect(screen.getByTestId("user").textContent).toBe("anon");
    expect(screen.getByTestId("auth-notice").textContent).toBe("none");
  });

  it("clears the user and records a notice when auth expires after bootstrap", async () => {
    (apiClient.getMe as jest.Mock).mockResolvedValue({
      user_id: 1,
      email: "ada@example.com",
      is_admin: false,
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("ada@example.com");
    });

    act(() => {
      notifyAuthExpired();
    });

    expect(screen.getByTestId("loading").textContent).toBe("ready");
    expect(screen.getByTestId("user").textContent).toBe("anon");
    expect(screen.getByTestId("auth-notice").textContent).toBe(
      AUTH_EXPIRED_MESSAGE
    );
  });

  it("logs in and refreshes the user", async () => {
    (apiClient.getMe as jest.Mock)
      .mockRejectedValueOnce(
        Object.assign(new Error("Unauthorized"), { status: 401 })
      )
      .mockResolvedValueOnce({
        user_id: 2,
        email: "grace@example.com",
        is_admin: true,
      });
    (apiClient.login as jest.Mock).mockResolvedValue({
      user_id: 2,
      email: "grace@example.com",
      is_admin: true,
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("anon");
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "login" }));

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("grace@example.com");
    });
    expect(apiClient.login).toHaveBeenCalledWith("ada@example.com", "secret123");
  });

  it("clears the user and session storage on logout", async () => {
    (apiClient.getMe as jest.Mock).mockResolvedValue({
      user_id: 1,
      email: "ada@example.com",
      is_admin: false,
    });
    (apiClient.logout as jest.Mock).mockResolvedValue(undefined);
    sessionStorage.setItem("app_session_id", "a".repeat(32));

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("ada@example.com");
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("anon");
    });
    expect(sessionStorage.getItem("app_session_id")).toBeNull();
    expect(apiClient.logout).toHaveBeenCalledTimes(1);
  });
});

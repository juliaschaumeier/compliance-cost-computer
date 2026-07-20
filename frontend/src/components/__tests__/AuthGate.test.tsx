import { render, screen } from "@testing-library/react";

import AuthGate from "@/components/AuthGate";
import { useAuth } from "@/contexts/AuthContext";

jest.mock("@/contexts/AuthContext", () => ({
  useAuth: jest.fn(),
}));

jest.mock("@/components/LoginForm", () => ({
  __esModule: true,
  default: () => <div data-testid="login-form" />,
}));

const mockUseAuth = useAuth as jest.Mock;

describe("AuthGate", () => {
  it("shows a loading state while auth is resolving", () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true });

    render(
      <AuthGate>
        <div data-testid="app" />
      </AuthGate>
    );

    expect(screen.getByText(/wird geladen/i)).toBeInTheDocument();
    expect(screen.queryByTestId("app")).not.toBeInTheDocument();
  });

  it("renders the login form when unauthenticated", () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false });

    render(
      <AuthGate>
        <div data-testid="app" />
      </AuthGate>
    );

    expect(screen.getByTestId("login-form")).toBeInTheDocument();
    expect(screen.queryByTestId("app")).not.toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    mockUseAuth.mockReturnValue({
      user: { user_id: 1, email: "ada@example.com", is_admin: false },
      loading: false,
    });

    render(
      <AuthGate>
        <div data-testid="app" />
      </AuthGate>
    );

    expect(screen.getByTestId("app")).toBeInTheDocument();
    expect(screen.queryByTestId("login-form")).not.toBeInTheDocument();
  });
});

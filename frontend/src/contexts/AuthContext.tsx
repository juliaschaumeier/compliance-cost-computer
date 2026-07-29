"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { apiClient, type ApiClientError } from "@/lib/api";
import { AUTH_EXPIRED_MESSAGE, subscribeAuthExpired } from "@/lib/authExpired";
import type { AuthUser } from "@/types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  authNotice: string | null;
  clearAuthNotice: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function isUnauthorized(error: unknown): boolean {
  return (error as ApiClientError)?.status === 401;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [authNotice, setAuthNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const me = await apiClient.getMe();
      setUser(me);
    } catch (error) {
      if (!isUnauthorized(error) && process.env.NODE_ENV === "development") {
        console.debug("[AuthContext] Failed to load current user", error);
      }
      setUser(null);
    }
  }, []);

  useEffect(() => {
    return subscribeAuthExpired(() => {
      setUser(null);
      setLoading(false);
      setAuthNotice(AUTH_EXPIRED_MESSAGE);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const bootstrap = async () => {
      await refresh();
      if (!cancelled) {
        setLoading(false);
      }
    };
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      await apiClient.login(email, password);
      setAuthNotice(null);
      await refresh();
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    try {
      await apiClient.logout();
    } finally {
      // Clear per-session state so a different user does not inherit the
      // previous user's session id or workflow readiness.
      try {
        sessionStorage.clear();
      } catch {
        // sessionStorage may be unavailable (e.g. private browsing); ignore.
      }
      setUser(null);
    }
  }, []);

  const clearAuthNotice = useCallback(() => {
    setAuthNotice(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        refresh,
        authNotice,
        clearAuthNotice,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

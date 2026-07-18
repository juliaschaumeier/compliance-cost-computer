"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { apiClient, type ApiClientError } from "@/lib/api";
import { useMounted } from "@/lib/useMounted";
import type { AdminUser } from "@/types";

type AdminUsersPanelProps = {
  open: boolean;
  onClose: () => void;
};

function PasswordVisibilityIcon({ visible }: { visible: boolean }) {
  if (visible) {
    return (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M2 2l20 20" />
        <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
        <path d="M7.1 7.1C4.9 8.3 3.2 10 2 12c2.1 3.5 5.5 6 10 6 1.6 0 3-.3 4.2-.9" />
        <path d="M14.1 5.3A10.5 10.5 0 0 0 12 5C7.5 5 4.1 7.5 2 12" />
        <path d="M18.8 8.8A13.3 13.3 0 0 1 22 12c-.7 1.2-1.5 2.3-2.5 3.2" />
      </svg>
    );
  }
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function PasswordVisibilityButton({
  visible,
  onClick,
}: {
  visible: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={visible ? "Passwort verbergen" : "Passwort anzeigen"}
      title={visible ? "Passwort verbergen" : "Passwort anzeigen"}
      className="flex h-9 w-10 shrink-0 items-center justify-center rounded-r-xl border-l border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-800"
    >
      <PasswordVisibilityIcon visible={visible} />
    </button>
  );
}

function getErrorMessage(error: unknown, fallback: string): string {
  const message = (error as ApiClientError)?.message;
  return typeof message === "string" && message.trim() ? message : fallback;
}

export default function AdminUsersPanel({ open, onClose }: AdminUsersPanelProps) {
  const isMounted = useMounted();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [pendingUserId, setPendingUserId] = useState<number | null>(null);
  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [showResetPassword, setShowResetPassword] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoadError(null);
    try {
      const list = await apiClient.listUsers();
      setUsers(list);
    } catch (error) {
      setUsers([]);
      setLoadError(getErrorMessage(error, "Benutzer konnten nicht geladen werden."));
    }
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    setActionError(null);
    setActionStatus(null);
    void loadUsers();
  }, [open, loadUsers]);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isCreating) {
      return;
    }
    setActionError(null);
    setActionStatus(null);
    setIsCreating(true);
    try {
      await apiClient.createUser(newEmail.trim(), newPassword, newIsAdmin);
      setNewEmail("");
      setNewPassword("");
      setShowNewPassword(false);
      setNewIsAdmin(false);
      setActionStatus("Benutzer angelegt.");
      await loadUsers();
    } catch (error) {
      setActionError(getErrorMessage(error, "Benutzer konnte nicht angelegt werden."));
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggleActive = async (user: AdminUser) => {
    if (pendingUserId !== null) {
      return;
    }
    setActionError(null);
    setActionStatus(null);
    setPendingUserId(user.user_id);
    try {
      await apiClient.updateUser(user.user_id, { is_active: !user.is_active });
      setActionStatus(
        user.is_active ? "Benutzer deaktiviert." : "Benutzer reaktiviert."
      );
      await loadUsers();
    } catch (error) {
      setActionError(
        getErrorMessage(error, "Benutzer konnte nicht aktualisiert werden.")
      );
    } finally {
      setPendingUserId(null);
    }
  };

  const beginPasswordReset = (user: AdminUser) => {
    setActionError(null);
    setActionStatus(null);
    setResetUserId(user.user_id);
    setResetPassword("");
    setShowResetPassword(false);
  };

  const cancelPasswordReset = () => {
    setResetUserId(null);
    setResetPassword("");
    setShowResetPassword(false);
  };

  const handlePasswordReset = async (event: React.FormEvent) => {
    event.preventDefault();
    if (resetUserId === null || pendingUserId !== null) {
      return;
    }
    setActionError(null);
    setActionStatus(null);
    setPendingUserId(resetUserId);
    try {
      await apiClient.updateUser(resetUserId, { password: resetPassword });
      setActionStatus("Passwort zurückgesetzt.");
      cancelPasswordReset();
      await loadUsers();
    } catch (error) {
      setActionError(
        getErrorMessage(error, "Passwort konnte nicht zurückgesetzt werden.")
      );
    } finally {
      setPendingUserId(null);
    }
  };

  if (!isMounted || !open) {
    return null;
  }

  const body = (
    <div className="pointer-events-none fixed inset-0 z-[85]">
      <div className="absolute inset-0 bg-slate-900/25" onClick={onClose} />
      <div className="flex h-full items-stretch justify-end">
        <section className="pointer-events-auto relative h-full w-full max-w-[640px] border-l border-slate-300 bg-white shadow-2xl">
          <header className="border-b border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  Benutzerverwaltung
                </div>
                <div className="mt-0.5 text-[11px] font-medium text-slate-500">
                  Konten anlegen, sperren und Passwörter neu setzen.
                </div>
              </div>
              <button
                onClick={onClose}
                className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                Schließen
              </button>
            </div>
          </header>
          <div className="h-[calc(100%-52px)] overflow-auto px-4 py-4">
            <form
              onSubmit={handleCreate}
              className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Neuen Benutzer anlegen
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="text-[11px] font-semibold text-slate-500">
                    E-Mail
                  </span>
                  <input
                    type="email"
                    required
                    value={newEmail}
                    onChange={(event) => setNewEmail(event.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
                  />
                </label>
                <label className="block">
                  <span className="text-[11px] font-semibold text-slate-500">
                    Passwort (min. 8 Zeichen)
                  </span>
                  <div className="mt-1 flex rounded-xl border border-slate-200 bg-white focus-within:border-slate-500">
                    <input
                      type={showNewPassword ? "text" : "password"}
                      required
                      minLength={8}
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                      className="min-w-0 flex-1 rounded-l-xl px-3 py-2 text-sm text-slate-900 focus:outline-none"
                    />
                    <PasswordVisibilityButton
                      visible={showNewPassword}
                      onClick={() => setShowNewPassword((prev) => !prev)}
                    />
                  </div>
                </label>
              </div>
              <label className="mt-3 flex items-center gap-2 text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={newIsAdmin}
                  onChange={(event) => setNewIsAdmin(event.target.checked)}
                  className="h-4 w-4"
                />
                Administrator
              </label>
              <button
                type="submit"
                disabled={isCreating}
                className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {isCreating ? "Wird angelegt..." : "Benutzer anlegen"}
              </button>
            </form>

            {actionError && (
              <div className="ccc-status-error mt-3 rounded-xl border px-3 py-2 text-xs font-semibold">
                {actionError}
              </div>
            )}
            {actionStatus && (
              <div className="ccc-status-success mt-3 rounded-xl border px-3 py-2 text-xs font-semibold">
                {actionStatus}
              </div>
            )}

            <div className="mt-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Benutzer
              </div>
              {loadError ? (
                <div className="ccc-status-error mt-3 rounded-xl border px-3 py-2 text-xs font-semibold">
                  {loadError}
                </div>
              ) : (
                <ul className="mt-3 space-y-2">
                  {users.map((user) => (
                    <li
                      key={user.user_id}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-slate-900">
                            {user.email}
                          </div>
                          <div className="mt-0.5 flex flex-wrap gap-1 text-[10px] font-semibold uppercase tracking-wide">
                            {user.is_admin && (
                              <span className="ccc-status-warning rounded-full border px-2 py-0.5">
                                Admin
                              </span>
                            )}
                            <span
                              className={`rounded-full border px-2 py-0.5 ${
                                user.is_active
                                  ? "ccc-status-success"
                                  : "border-slate-200 bg-slate-100 text-slate-600"
                              }`}
                            >
                              {user.is_active ? "Aktiv" : "Inaktiv"}
                            </span>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <button
                            type="button"
                            onClick={() => beginPasswordReset(user)}
                            disabled={pendingUserId === user.user_id}
                            className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Passwort zurücksetzen
                          </button>
                          <button
                            type="button"
                            onClick={() => handleToggleActive(user)}
                            disabled={pendingUserId === user.user_id}
                            className={`rounded-xl border bg-white px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
                              user.is_active
                                ? "ccc-danger-outline hover:bg-[var(--ccc-status-alert-bg)]"
                                : "border-slate-200 text-slate-700 hover:bg-slate-50"
                            }`}
                          >
                            {user.is_active ? "Deaktivieren" : "Reaktivieren"}
                          </button>
                        </div>
                      </div>
                      {resetUserId === user.user_id && (
                        <form
                          onSubmit={handlePasswordReset}
                          className="mt-3 flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-center"
                        >
                          <label className="min-w-0 flex-1">
                            <span className="text-[11px] font-semibold text-slate-500">
                              Neues Passwort
                            </span>
                            <div className="mt-1 flex rounded-xl border border-slate-200 bg-white focus-within:border-slate-500">
                              <input
                                type={showResetPassword ? "text" : "password"}
                                required
                                minLength={8}
                                value={resetPassword}
                                onChange={(event) => setResetPassword(event.target.value)}
                                className="min-w-0 flex-1 rounded-l-xl px-3 py-2 text-sm text-slate-900 focus:outline-none"
                              />
                              <PasswordVisibilityButton
                                visible={showResetPassword}
                                onClick={() => setShowResetPassword((prev) => !prev)}
                              />
                            </div>
                          </label>
                          <div className="flex gap-2 sm:pt-5">
                            <button
                              type="submit"
                              disabled={pendingUserId === user.user_id}
                              className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                            >
                              Speichern
                            </button>
                            <button
                              type="button"
                              onClick={cancelPasswordReset}
                              className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-white"
                            >
                              Abbrechen
                            </button>
                          </div>
                        </form>
                      )}
                    </li>
                  ))}
                  {users.length === 0 && (
                    <li className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
                      Keine Benutzer vorhanden.
                    </li>
                  )}
                </ul>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );

  return createPortal(body, document.body);
}

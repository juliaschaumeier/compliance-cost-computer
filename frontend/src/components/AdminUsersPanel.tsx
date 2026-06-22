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
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [pendingUserId, setPendingUserId] = useState<number | null>(null);

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
              <div className="text-sm font-semibold text-slate-900">
                Benutzerverwaltung
              </div>
              <button
                onClick={onClose}
                className="rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700"
              >
                Schließen
              </button>
            </div>
          </header>
          <div className="h-[calc(100%-52px)] overflow-auto px-4 py-4">
            <form
              onSubmit={handleCreate}
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
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
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-slate-400 focus:outline-none"
                  />
                </label>
                <label className="block">
                  <span className="text-[11px] font-semibold text-slate-500">
                    Passwort (min. 8 Zeichen)
                  </span>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-slate-400 focus:outline-none"
                  />
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
              <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
                {actionError}
              </div>
            )}
            {actionStatus && (
              <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
                {actionStatus}
              </div>
            )}

            <div className="mt-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Benutzer
              </div>
              {loadError ? (
                <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
                  {loadError}
                </div>
              ) : (
                <ul className="mt-3 space-y-2">
                  {users.map((user) => (
                    <li
                      key={user.user_id}
                      className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-slate-900">
                          {user.email}
                        </div>
                        <div className="mt-0.5 flex flex-wrap gap-1 text-[10px] font-semibold uppercase tracking-wide">
                          {user.is_admin && (
                            <span className="rounded-full bg-slate-900 px-2 py-0.5 text-white">
                              Admin
                            </span>
                          )}
                          <span
                            className={`rounded-full px-2 py-0.5 ${
                              user.is_active
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-slate-200 text-slate-600"
                            }`}
                          >
                            {user.is_active ? "Aktiv" : "Inaktiv"}
                          </span>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleToggleActive(user)}
                        disabled={pendingUserId === user.user_id}
                        className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
                          user.is_active
                            ? "border-rose-200 text-rose-700 hover:bg-rose-50"
                            : "border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                        }`}
                      >
                        {user.is_active ? "Deaktivieren" : "Reaktivieren"}
                      </button>
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

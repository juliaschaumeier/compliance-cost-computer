"use client";

import { useState } from "react";

import { useAuth } from "@/contexts/AuthContext";
import { type ApiClientError } from "@/lib/api";

export default function LoginForm() {
  const { authNotice, clearAuthNotice, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [dataNoticeAccepted, setDataNoticeAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSubmitting || !dataNoticeAccepted) {
      return;
    }
    clearAuthNotice();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email.trim(), password);
      setDataNoticeAccepted(false);
    } catch (err) {
      const status = (err as ApiClientError)?.status;
      if (status === 401) {
        setError("E-Mail oder Passwort ist ungültig.");
      } else {
        setError("Anmeldung fehlgeschlagen. Bitte erneut versuchen.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      data-testid="login-screen"
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-auto bg-white px-4 py-6"
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-lg font-bold text-white shadow-inner">
            CCC
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900">
              Compliance-Cost Computer
            </h1>
            <p className="text-xs text-slate-500">Bitte anmelden, um fortzufahren.</p>
          </div>
        </div>
        <div className="mt-6 space-y-3">
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              E-Mail
            </span>
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-slate-400 focus:outline-none"
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Passwort
            </span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-slate-400 focus:outline-none"
            />
          </label>
          <label className="flex items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold leading-5 text-slate-700">
            <input
              type="checkbox"
              checked={dataNoticeAccepted}
              onChange={(event) => setDataNoticeAccepted(event.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
            />
            <span>
              Ich bestätige, dass ich keine vertraulichen Texte,
              personenbezogenen Daten oder sonstigen sensiblen Angaben hochlade
              oder eingebe.
            </span>
          </label>
        </div>
        {authNotice && (
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
            {authNotice}
          </div>
        )}
        {error && (
          <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={isSubmitting || !dataNoticeAccepted}
          className="mt-5 w-full rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {isSubmitting ? "Wird angemeldet..." : "Anmelden"}
        </button>
      </form>
    </div>
  );
}

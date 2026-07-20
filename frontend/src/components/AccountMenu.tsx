"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useAnchoredPopoverPosition } from "@/lib/useAnchoredPopoverPosition";
import { useMounted } from "@/lib/useMounted";
import type { AuthUser } from "@/types";

type AccountMenuProps = {
  user: AuthUser;
  logout: () => Promise<void>;
};

export default function AccountMenu({ user, logout }: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const isMounted = useMounted();
  const { position } = useAnchoredPopoverPosition({
    open,
    triggerRef,
    width: 300,
    align: "right",
    offset: 12,
    padding: 12,
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (
        popoverRef.current?.contains(target) ||
        triggerRef.current?.contains(target)
      ) {
        return;
      }
      setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const handleLogout = async () => {
    if (isLoggingOut) {
      return;
    }
    setIsLoggingOut(true);
    try {
      await logout();
      setOpen(false);
    } finally {
      setIsLoggingOut(false);
    }
  };

  const popover = (
    <div
      ref={popoverRef}
      data-testid="account-menu-popover"
      className="fixed z-[70] w-[300px] rounded-2xl border border-slate-200 bg-white p-4 text-slate-800 shadow-2xl"
      style={{ top: position.top, left: position.left }}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Angemeldet als
      </div>
      <div className="mt-2 truncate text-sm font-semibold text-slate-950" title={user.email}>
        {user.email}
      </div>
      <div className="mt-2 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
        {user.is_admin ? "Admin" : "Benutzer"}
      </div>
      <button
        type="button"
        onClick={handleLogout}
        disabled={isLoggingOut}
        className="mt-4 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isLoggingOut ? "Abmelden..." : "Abmelden"}
      </button>
    </div>
  );

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/30 bg-white/10 text-white shadow-sm transition hover:bg-white/20"
        aria-label="Benutzerkonto öffnen"
        title="Benutzerkonto"
        aria-expanded={open}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="h-[18px] w-[18px]"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20 21a8 8 0 0 0-16 0" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </button>
      {open && isMounted ? createPortal(popover, document.body) : null}
    </>
  );
}

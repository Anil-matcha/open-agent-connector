"use client";

import React, { useState, useSyncExternalStore } from "react";
import { API_BASE, clearAdminToken, getAdminToken, setAdminToken } from "@/lib/api";
import { LogIn, LogOut, ShieldCheck, Users } from "lucide-react";

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

/**
 * Shows whether the console is acting as the operator (admin token) or in the shared public sandbox,
 * and lets the operator sign in with the admin token. Hosted deployments can replace this component.
 */
export function AccessControl() {
  const operator = useSyncExternalStore(subscribeToStorage, () => Boolean(getAdminToken()), () => false);
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function signIn(event: React.FormEvent) {
    event.preventDefault();
    const candidate = token.trim();
    if (!candidate) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: candidate }),
      });
      const data = await res.json();
      if (res.ok && data.valid) {
        setAdminToken(candidate);
        window.location.reload();
        return;
      }
      setError("That is not a valid admin token.");
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    clearAdminToken();
    window.location.reload();
  }

  return (
    <div className="border-t border-zinc-100 px-3 py-2.5 text-[11px]">
      {operator ? (
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 font-medium text-emerald-700">
            <ShieldCheck size={13} /> Operator
          </span>
          <button type="button" onClick={signOut} className="flex items-center gap-1 text-zinc-500 hover:text-zinc-900">
            <LogOut size={12} /> Sign out
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between gap-2">
            <span
              className="flex items-center gap-1.5 font-medium text-zinc-600"
              title="Without an admin token you work in a shared public sandbox, separate from the operator's data."
            >
              <Users size={13} /> Public sandbox
            </span>
            <button type="button" onClick={() => setOpen((v) => !v)} className="flex items-center gap-1 text-zinc-500 hover:text-zinc-900">
              <LogIn size={12} /> Operator
            </button>
          </div>
          {open && (
            <form onSubmit={signIn} className="mt-2 flex flex-col gap-1.5">
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Admin token"
                autoComplete="off"
                className="w-full rounded-md border border-zinc-200 px-2 py-1 font-mono text-[11px] text-zinc-800 focus:outline-none focus:ring-1 focus:ring-zinc-400"
              />
              {error && <span className="text-rose-600">{error}</span>}
              <button type="submit" disabled={busy || !token.trim()} className="rounded-md bg-zinc-900 px-2 py-1 text-white disabled:opacity-50">
                {busy ? "Checking..." : "Sign in as operator"}
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}

"use client";

import React, { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { API_BASE, clearAdminToken, fetchApi, getAdminToken, setAdminToken } from "@/lib/api";
import { LogIn, LogOut, ShieldCheck, User, Users } from "lucide-react";

type Mode = "loading" | "operator" | "account" | "public";

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

/**
 * Shows who the console is acting as: the operator (admin token), a signed-in account, or the
 * shared public sandbox. Each sees only its own tenant's data.
 */
export function AccessControl() {
  const operatorSignedIn = useSyncExternalStore(subscribeToStorage, () => Boolean(getAdminToken()), () => false);
  const [accountMode, setAccountMode] = useState<Exclude<Mode, "operator">>("loading");
  const mode: Mode = operatorSignedIn ? "operator" : accountMode;
  const [email, setEmail] = useState<string | null>(null);
  const [signupOpen, setSignupOpen] = useState(false);
  const [showOperator, setShowOperator] = useState(false);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchApi<{ user: { email: string } }>("/api/accounts/me")
      .then((res) => {
        setEmail(res.user.email);
        setAccountMode("account");
      })
      .catch(() => setAccountMode("public"));
    fetchApi<{ signupMode: string }>("/api/accounts/config")
      .then((c) => setSignupOpen(c.signupMode !== "disabled"))
      .catch(() => {});
  }, []);

  async function signInOperator(event: React.FormEvent) {
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

  async function signOut() {
    if (mode === "account") {
      try {
        await fetchApi("/api/accounts/logout", { method: "POST" });
      } catch {
        // the cookie is cleared server-side on success; reload either way
      }
    }
    clearAdminToken();
    window.location.assign("/");
  }

  if (mode === "loading") return <div className="border-t border-zinc-100 px-3 py-2.5 text-[11px] text-zinc-300">...</div>;

  return (
    <div className="border-t border-zinc-100 px-3 py-2.5 text-[11px]">
      {mode === "operator" && (
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 font-medium text-emerald-700">
            <ShieldCheck size={13} /> Operator
          </span>
          <button type="button" onClick={signOut} className="flex items-center gap-1 text-zinc-500 hover:text-zinc-900">
            <LogOut size={12} /> Sign out
          </button>
        </div>
      )}

      {mode === "account" && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <Link href="/account" className="flex min-w-0 items-center gap-1.5 font-medium text-zinc-700 hover:text-zinc-900" title={email ?? ""}>
              <User size={13} className="shrink-0" />
              <span className="truncate">{email}</span>
            </Link>
            <button type="button" onClick={signOut} className="flex shrink-0 items-center gap-1 text-zinc-500 hover:text-zinc-900">
              <LogOut size={12} /> Sign out
            </button>
          </div>
        </div>
      )}

      {mode === "public" && (
        <>
          <div className="flex items-center justify-between gap-2">
            <span
              className="flex items-center gap-1.5 font-medium text-zinc-600"
              title="Without signing in you work in a shared public sandbox, separate from private accounts."
            >
              <Users size={13} /> Public sandbox
            </span>
            <Link href="/login" className="flex items-center gap-1 text-zinc-600 hover:text-zinc-900">
              <LogIn size={12} /> Sign in
            </Link>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-zinc-400">
            {signupOpen ? (
              <Link href="/signup" className="hover:text-zinc-700">Create account</Link>
            ) : (
              <span />
            )}
            <button type="button" onClick={() => setShowOperator((v) => !v)} className="hover:text-zinc-700">
              Operator
            </button>
          </div>
          {showOperator && (
            <form onSubmit={signInOperator} className="mt-2 flex flex-col gap-1.5">
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Admin token"
                autoComplete="off"
                className="w-full rounded-md border border-zinc-200 px-2 py-1 font-mono text-[11px] text-zinc-800 focus:outline-none focus:ring-1 focus:ring-zinc-400"
              />
              {error && <span className="text-rose-600">{error}</span>}
              <button
                type="submit"
                disabled={busy || !token.trim()}
                className="rounded-md bg-zinc-900 px-2 py-1 text-white disabled:opacity-50"
              >
                {busy ? "Checking..." : "Sign in as operator"}
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}

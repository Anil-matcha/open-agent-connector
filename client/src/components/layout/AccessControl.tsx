"use client";

import React, { useState, useEffect, useRef, useSyncExternalStore } from "react";
import Link from "next/link";
import { API_BASE, clearAdminToken, getAdminToken, setAdminToken } from "@/lib/api";
import { useMobileNav } from "@/components/layout/MobileNavContext";
import {
  ShieldCheck,
  Users,
  LogOut,
  LogIn,
  KeyRound,
  History,
  ExternalLink,
  Copy,
  Check,
  ChevronsUpDown,
  Edit3,
  Sparkles,
} from "lucide-react";

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase() || "OP";
}

export function AccessControl() {
  const { close: closeMobileNav } = useMobileNav();
  const operator = useSyncExternalStore(
    subscribeToStorage,
    () => Boolean(getAdminToken()),
    () => false
  );

  const containerRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [signInOpen, setSignInOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  // Customizable user profile
  const [userName, setUserName] = useState("Operator");
  const [userSubtitle, setUserSubtitle] = useState("Root Admin • Self-Hosted");
  const [isEditingProfile, setIsEditingProfile] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedName = localStorage.getItem("connector_user_name");
      const storedSubtitle = localStorage.getItem("connector_user_subtitle");
      if (storedName) setUserName(storedName);
      if (storedSubtitle) setUserSubtitle(storedSubtitle);
    }
  }, []);

  // Dismiss on outside click and Escape key
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setMenuOpen(false);
        setSignInOpen(false);
        setIsEditingProfile(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        setSignInOpen(false);
        setIsEditingProfile(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  function handleNameChange(newName: string) {
    setUserName(newName);
    if (typeof window !== "undefined") {
      localStorage.setItem("connector_user_name", newName);
    }
  }

  function handleSubtitleChange(newSubtitle: string) {
    setUserSubtitle(newSubtitle);
    if (typeof window !== "undefined") {
      localStorage.setItem("connector_user_subtitle", newSubtitle);
    }
  }

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault();
    const candidate = tokenInput.trim();
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
        setSignInOpen(false);
        window.location.reload();
        return;
      }
      setError("Invalid admin token.");
    } catch {
      setError("Cannot connect to server.");
    } finally {
      setBusy(false);
    }
  }

  function handleSignOut() {
    clearAdminToken();
    setMenuOpen(false);
    window.location.reload();
  }

  function handleCopyToken() {
    const t = getAdminToken();
    if (!t) return;
    navigator.clipboard.writeText(t);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const initials = getInitials(operator ? userName : "Public Sandbox");

  return (
    <div ref={containerRef} className="relative border-t border-zinc-200/80 bg-zinc-50/50 p-2">
      {/* Popover Menu for Operator Mode */}
      {operator && menuOpen && (
        <div className="absolute bottom-full left-2 right-2 mb-2 z-50 rounded-xl bg-white border border-zinc-200 shadow-xl shadow-zinc-950/10 p-1.5 animate-in fade-in zoom-in-95 duration-150 select-none">
          {/* Profile Header Card */}
          <div className="px-2.5 py-2 rounded-lg bg-zinc-50 border border-zinc-100 mb-1">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase font-semibold tracking-wider text-zinc-400">
                Session Info
              </span>
              <button
                type="button"
                onClick={() => setIsEditingProfile((v) => !v)}
                className="text-[10px] text-zinc-500 hover:text-zinc-900 flex items-center gap-1 transition-colors cursor-pointer"
                title="Edit name and title"
              >
                <Edit3 size={11} />
                <span>{isEditingProfile ? "Done" : "Edit"}</span>
              </button>
            </div>

            {isEditingProfile ? (
              <div className="space-y-1.5 my-1">
                <div>
                  <label className="text-[9px] uppercase font-medium text-zinc-400 block mb-0.5">
                    User Name
                  </label>
                  <input
                    type="text"
                    value={userName}
                    onChange={(e) => handleNameChange(e.target.value)}
                    placeholder="Operator name"
                    className="w-full text-xs px-2 py-1 bg-white border border-zinc-200 rounded text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-400"
                  />
                </div>
                <div>
                  <label className="text-[9px] uppercase font-medium text-zinc-400 block mb-0.5">
                    Subtitle / Role
                  </label>
                  <input
                    type="text"
                    value={userSubtitle}
                    onChange={(e) => handleSubtitleChange(e.target.value)}
                    placeholder="e.g. Root Admin • Self-Hosted"
                    className="w-full text-xs px-2 py-1 bg-white border border-zinc-200 rounded text-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-400"
                  />
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-md bg-zinc-900 text-white font-medium text-xs flex items-center justify-center shrink-0">
                  {initials}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold text-zinc-900 truncate">
                      {userName}
                    </span>
                    <span className="px-1 py-0.2 rounded text-[8px] font-mono font-medium bg-emerald-100 text-emerald-800 shrink-0">
                      Root
                    </span>
                  </div>
                  <p className="text-[10px] text-zinc-500 truncate">{userSubtitle}</p>
                </div>
              </div>
            )}

            {/* Gateway status */}
            <div className="mt-2 pt-1.5 border-t border-zinc-200/60 flex items-center justify-between text-[10px] text-zinc-500">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Active Gateway
              </span>
              <span className="font-mono text-[9px] text-zinc-400">MCP + REST</span>
            </div>
          </div>

          {/* Quick Actions List */}
          <div className="space-y-0.5">
            <button
              type="button"
              onClick={handleCopyToken}
              className="w-full flex items-center justify-between px-2.5 py-1.5 text-xs text-zinc-700 hover:text-zinc-900 hover:bg-zinc-100/80 rounded-md transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <ShieldCheck size={14} className="text-zinc-500" />
                <span>Copy Admin Token</span>
              </div>
              {copied ? (
                <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-600">
                  <Check size={12} /> Copied
                </span>
              ) : (
                <Copy size={12} className="text-zinc-400" />
              )}
            </button>

            <Link
              href="/tokens"
              onClick={() => {
                setMenuOpen(false);
                closeMobileNav();
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-zinc-700 hover:text-zinc-900 hover:bg-zinc-100/80 rounded-md transition-colors"
            >
              <KeyRound size={14} className="text-zinc-500" />
              <span>Manage Access Tokens</span>
            </Link>

            <Link
              href="/logs"
              onClick={() => {
                setMenuOpen(false);
                closeMobileNav();
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-zinc-700 hover:text-zinc-900 hover:bg-zinc-100/80 rounded-md transition-colors"
            >
              <History size={14} className="text-zinc-500" />
              <span>Audit Run Logs</span>
            </Link>

            <a
              href={`${API_BASE}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => {
                setMenuOpen(false);
                closeMobileNav();
              }}
              className="w-full flex items-center justify-between px-2.5 py-1.5 text-xs text-zinc-700 hover:text-zinc-900 hover:bg-zinc-100/80 rounded-md transition-colors"
            >
              <div className="flex items-center gap-2">
                <ExternalLink size={14} className="text-zinc-500" />
                <span>API Documentation</span>
              </div>
              <span className="text-[10px] text-zinc-400 font-mono">/docs</span>
            </a>
          </div>

          {/* Divider */}
          <div className="my-1 border-t border-zinc-100" />

          {/* Sign Out Button */}
          <button
            type="button"
            onClick={handleSignOut}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-rose-600 hover:bg-rose-50/80 rounded-md transition-colors font-medium cursor-pointer"
          >
            <LogOut size={14} />
            <span>Sign out</span>
          </button>
        </div>
      )}

      {/* Popover Menu for Public Sandbox Sign In */}
      {!operator && signInOpen && (
        <div className="absolute bottom-full left-2 right-2 mb-2 z-50 rounded-xl bg-white border border-zinc-200 shadow-xl shadow-zinc-950/10 p-3 animate-in fade-in zoom-in-95 duration-150 select-none">
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-zinc-900">
              <LogIn size={14} /> Sign in as Operator
            </span>
            <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-zinc-100 text-zinc-600">
              Admin
            </span>
          </div>

          <p className="text-[11px] text-zinc-500 leading-tight mb-2.5">
            Enter your admin secret token to manage credentials, encrypted connections, and scoped runtime tokens.
          </p>

          <form onSubmit={handleSignIn} className="space-y-2">
            <input
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Admin token..."
              autoFocus
              autoComplete="off"
              className="w-full rounded-md border border-zinc-200 px-2.5 py-1.5 font-mono text-xs text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-400 bg-zinc-50/50"
            />
            {error && <span className="text-[11px] text-rose-600 block">{error}</span>}
            <div className="flex items-center gap-1.5 pt-0.5">
              <button
                type="submit"
                disabled={busy || !tokenInput.trim()}
                className="flex-1 rounded-md bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50 transition-colors cursor-pointer"
              >
                {busy ? "Verifying..." : "Sign in"}
              </button>
              <button
                type="button"
                onClick={() => setSignInOpen(false)}
                className="px-2.5 py-1.5 text-xs text-zinc-500 hover:text-zinc-800 rounded-md hover:bg-zinc-100 transition-colors cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Main Profile Trigger Card */}
      {operator ? (
        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          className={`w-full flex items-center gap-2.5 p-1.5 rounded-lg text-left transition-all duration-150 border cursor-pointer group ${
            menuOpen
              ? "bg-white border-zinc-200 shadow-xs"
              : "border-transparent hover:border-zinc-200 hover:bg-white hover:shadow-xs"
          }`}
        >
          {/* Avatar with initials & active status dot */}
          <div className="relative shrink-0">
            <div className="w-8 h-8 rounded-lg bg-zinc-900 text-white font-medium text-xs flex items-center justify-center ring-1 ring-zinc-800/20 shadow-xs group-hover:scale-102 transition-transform">
              {initials}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-white" />
          </div>

          {/* User Details */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-zinc-900 truncate">
                {userName}
              </span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/70 shrink-0">
                Root
              </span>
            </div>
            <p className="text-[10px] text-zinc-500 truncate leading-tight mt-0.5">
              {userSubtitle}
            </p>
          </div>

          {/* ChevronsUpDown indicator */}
          <ChevronsUpDown
            size={14}
            className={`text-zinc-400 transition-colors shrink-0 ${
              menuOpen ? "text-zinc-700" : "group-hover:text-zinc-700"
            }`}
          />
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setSignInOpen((v) => !v)}
          className={`w-full flex items-center gap-2.5 p-1.5 rounded-lg text-left transition-all duration-150 border cursor-pointer group ${
            signInOpen
              ? "bg-white border-zinc-200 shadow-xs"
              : "border-transparent hover:border-zinc-200 hover:bg-white hover:shadow-xs"
          }`}
        >
          {/* Avatar for Sandbox */}
          <div className="relative shrink-0">
            <div className="w-8 h-8 rounded-lg bg-zinc-200 text-zinc-600 font-medium text-xs flex items-center justify-center ring-1 ring-zinc-300 shadow-xs">
              <Users size={14} />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-white" />
          </div>

          {/* Sandbox Details */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-zinc-700 truncate">
                Public Sandbox
              </span>
              <span className="px-1 py-0.2 rounded text-[8px] font-mono bg-amber-50 text-amber-700 border border-amber-200/60 shrink-0">
                Demo
              </span>
            </div>
            <p className="text-[10px] text-zinc-400 truncate leading-tight mt-0.5">
              Click to sign in
            </p>
          </div>

          <LogIn
            size={13}
            className="text-zinc-400 group-hover:text-zinc-700 transition-colors shrink-0"
          />
        </button>
      )}
    </div>
  );
}

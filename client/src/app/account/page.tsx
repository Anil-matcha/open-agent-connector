"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { fetchApi } from "@/lib/api";

interface Me {
  email: string;
  tenantId: string;
  createdAt?: string;
}

export default function AccountPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [deletePassword, setDeletePassword] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [deleteMsg, setDeleteMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchApi<{ user: Me }>("/api/accounts/me")
      .then((res) => setMe(res.user))
      .catch(() => setMe(null))
      .finally(() => setLoaded(true));
  }, []);

  async function changePassword(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setPasswordMsg(null);
    try {
      await fetchApi("/api/accounts/change-password", {
        method: "POST",
        body: JSON.stringify({ currentPassword, newPassword }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setPasswordMsg({ ok: true, text: "Password updated. Your other devices were signed out." });
    } catch (err) {
      setPasswordMsg({ ok: false, text: err instanceof Error ? err.message : "Could not change password." });
    } finally {
      setBusy(false);
    }
  }

  async function deleteAccount(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setDeleteMsg(null);
    try {
      await fetchApi("/api/accounts/delete", { method: "POST", body: JSON.stringify({ password: deletePassword }) });
      window.location.assign("/");
    } catch (err) {
      setDeleteMsg(err instanceof Error ? err.message : "Could not delete the account.");
      setBusy(false);
    }
  }

  const inputClass =
    "block h-8 w-full max-w-xs rounded-md border border-zinc-200 bg-white px-3 text-xs text-zinc-900 focus:border-zinc-400 focus:outline-none focus:ring-1 focus:ring-zinc-300";

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header title="Account" description="Your sign-in details and data." />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-2xl space-y-6">
            {!loaded ? null : !me ? (
              <div className="rounded-lg border border-zinc-200 bg-white p-5 text-sm text-zinc-600">
                You are not signed in with an account.{" "}
                <Link href="/login" className="font-medium text-zinc-900 underline">
                  Sign in
                </Link>
              </div>
            ) : (
              <>
                <section className="rounded-lg border border-zinc-200 bg-white p-5">
                  <h2 className="text-sm font-semibold text-zinc-900">Profile</h2>
                  <p className="mt-2 text-xs text-zinc-600">{me.email}</p>
                  <p className="mt-1 text-[11px] text-zinc-400">
                    Everything you connect lives in your own private workspace.
                  </p>
                </section>

                <section className="rounded-lg border border-zinc-200 bg-white p-5">
                  <h2 className="text-sm font-semibold text-zinc-900">Change password</h2>
                  <form onSubmit={changePassword} className="mt-3 space-y-3">
                    <input className={inputClass} type="password" placeholder="Current password" autoComplete="current-password" required value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
                    <input className={inputClass} type="password" placeholder="New password (10+ characters)" autoComplete="new-password" required minLength={10} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
                    {passwordMsg && (
                      <p className={`text-xs ${passwordMsg.ok ? "text-emerald-700" : "text-rose-600"}`}>{passwordMsg.text}</p>
                    )}
                    <Button type="submit" size="sm" loading={busy}>Update password</Button>
                  </form>
                </section>

                <section className="rounded-lg border border-rose-200 bg-white p-5">
                  <h2 className="text-sm font-semibold text-rose-700">Delete account</h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    Permanently removes your account, connections, tokens, run history and saved OAuth app
                    settings. This cannot be undone.
                  </p>
                  <form onSubmit={deleteAccount} className="mt-3 space-y-3">
                    <input className={inputClass} type="password" placeholder="Your password" autoComplete="current-password" required value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} />
                    <input className={inputClass} placeholder='Type "delete" to confirm' autoComplete="off" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
                    {deleteMsg && <p className="text-xs text-rose-600">{deleteMsg}</p>}
                    <Button type="submit" size="sm" variant="danger" loading={busy} disabled={confirmText.trim().toLowerCase() !== "delete"}>
                      Delete my account
                    </Button>
                  </form>
                </section>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

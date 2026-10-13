"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { AuthShell, Field, FormMessage, SubmitButton } from "@/components/auth/AuthShell";

interface AccountsConfig {
  signupMode: "disabled" | "invite" | "open";
  emailVerification: boolean;
  passwordMinLength: number;
}

export default function SignupPage() {
  const [config, setConfig] = useState<AccountsConfig | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchApi<AccountsConfig>("/api/accounts/config")
      .then(setConfig)
      .catch(() => setError("Could not reach the server."));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetchApi<{ status: string }>("/api/accounts/signup", {
        method: "POST",
        body: JSON.stringify({ email, password, inviteCode: inviteCode || undefined }),
      });
      if (res.status === "verification_required") {
        window.location.assign(`/verify?email=${encodeURIComponent(email)}`);
        return;
      }
      // Invite-only setups without email verification: the account is ready, sign straight in.
      await fetchApi("/api/accounts/login", { method: "POST", body: JSON.stringify({ email, password }) });
      window.location.assign("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed.");
      setBusy(false);
    }
  }

  const closed = config?.signupMode === "disabled";

  return (
    <AuthShell
      title="Create your account"
      subtitle="Your connections and tokens stay private to you."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-zinc-700 underline">
            Sign in
          </Link>
        </>
      }
    >
      {closed ? (
        <FormMessage kind="info">Sign-ups are currently closed.</FormMessage>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {error && <FormMessage kind="error">{error}</FormMessage>}
          <Field label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <Field
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            minLength={config?.passwordMinLength ?? 10}
            hint={`At least ${config?.passwordMinLength ?? 10} characters.`}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {config?.signupMode === "invite" && (
            <Field label="Invite code" required autoComplete="off" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} />
          )}
          <SubmitButton busy={busy || config === null}>Create account</SubmitButton>
          <p className="text-center text-[11px] text-zinc-400">
            By creating an account you agree to the{" "}
            <Link href="/terms" className="underline">Terms</Link> and{" "}
            <Link href="/privacy" className="underline">Privacy Policy</Link>.
          </p>
        </form>
      )}
    </AuthShell>
  );
}

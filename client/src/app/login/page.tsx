"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { AuthShell, Field, FormMessage, SubmitButton } from "@/components/auth/AuthShell";

function LoginForm() {
  const params = useSearchParams();
  const notice = params.get("reset") === "1" ? "Password updated. Sign in with your new password." : null;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [signupOpen, setSignupOpen] = useState(false);

  useEffect(() => {
    fetchApi<{ signupMode: string }>("/api/accounts/config")
      .then((c) => setSignupOpen(c.signupMode !== "disabled"))
      .catch(() => {});
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await fetchApi("/api/accounts/login", { method: "POST", body: JSON.stringify({ email, password }) });
      window.location.assign("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign in failed.";
      if (message.toLowerCase().includes("verify your email")) {
        window.location.assign(`/verify?email=${encodeURIComponent(email)}`);
        return;
      }
      setError(message);
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Sign in"
      subtitle="Use your account to keep your connections private."
      footer={
        signupOpen ? (
          <>
            New here?{" "}
            <Link href="/signup" className="font-medium text-zinc-700 underline">
              Create an account
            </Link>
          </>
        ) : undefined
      }
    >
      <form onSubmit={submit} className="space-y-4">
        {notice && <FormMessage kind="info">{notice}</FormMessage>}
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <Field label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        <SubmitButton busy={busy}>Sign in</SubmitButton>
        <p className="text-center text-xs">
          <Link href="/forgot-password" className="text-zinc-500 underline hover:text-zinc-800">
            Forgot your password?
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

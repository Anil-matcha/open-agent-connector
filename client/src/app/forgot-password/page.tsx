"use client";

import React, { useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { AuthShell, Field, FormMessage, SubmitButton } from "@/components/auth/AuthShell";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await fetchApi("/api/accounts/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
      window.location.assign(`/reset-password?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed.");
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Reset your password"
      subtitle="We will email you a 6-digit code if an account exists for that address."
      footer={
        <Link href="/login" className="font-medium text-zinc-700 underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <Field label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <SubmitButton busy={busy}>Send code</SubmitButton>
      </form>
    </AuthShell>
  );
}

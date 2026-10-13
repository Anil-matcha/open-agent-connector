"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { AuthShell, Field, FormMessage, SubmitButton } from "@/components/auth/AuthShell";

function VerifyForm() {
  const params = useSearchParams();
  const initialEmail = params.get("email") ?? "";
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(initialEmail ? `We emailed a 6-digit code to ${initialEmail}.` : null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await fetchApi("/api/accounts/verify-email", { method: "POST", body: JSON.stringify({ email, code }) });
      window.location.assign("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await fetchApi("/api/accounts/resend-verification", { method: "POST", body: JSON.stringify({ email }) });
      setNotice("If that address is waiting for verification, a new code is on its way.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend the code.");
    }
  }

  return (
    <AuthShell
      title="Verify your email"
      subtitle="Enter the code we sent you. It expires in 10 minutes."
      footer={
        <Link href="/login" className="font-medium text-zinc-700 underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        {notice && <FormMessage kind="info">{notice}</FormMessage>}
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <Field label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field
          label="Code"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="[0-9]{6}"
          maxLength={6}
          required
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        />
        <SubmitButton busy={busy}>Verify and continue</SubmitButton>
        <p className="text-center text-xs">
          <button type="button" onClick={resend} disabled={!email} className="text-zinc-500 underline hover:text-zinc-800 disabled:opacity-50">
            Send a new code
          </button>
        </p>
      </form>
    </AuthShell>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyForm />
    </Suspense>
  );
}

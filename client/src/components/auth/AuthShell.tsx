import React from "react";
import Link from "next/link";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="h-full overflow-y-auto bg-zinc-50">
      <main className="mx-auto flex min-h-full w-full max-w-sm flex-col justify-center px-6 py-12">
        <Link href="/" className="mb-8 flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-zinc-900 text-xs font-bold text-white">
            C
          </div>
          <span className="text-sm font-semibold tracking-tight text-zinc-900">ConnectorHub</span>
        </Link>
        <h1 className="text-xl font-semibold tracking-tight text-zinc-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>}
        <div className="mt-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">{children}</div>
        {footer && <div className="mt-4 text-center text-xs text-zinc-500">{footer}</div>}
        <p className="mt-8 text-center text-[11px] text-zinc-400">
          <Link href="/privacy" className="hover:text-zinc-600">Privacy</Link>
          {" · "}
          <Link href="/terms" className="hover:text-zinc-600">Terms</Link>
        </p>
      </main>
    </div>
  );
}

export function Field({
  label,
  hint,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-zinc-700">{label}</span>
      <input
        {...props}
        className="h-9 w-full rounded-md border border-zinc-200 bg-white px-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none focus:ring-1 focus:ring-zinc-300"
      />
      {hint && <span className="mt-1 block text-[11px] text-zinc-400">{hint}</span>}
    </label>
  );
}

export function FormMessage({ kind, children }: { kind: "error" | "info"; children: React.ReactNode }) {
  return (
    <p
      role={kind === "error" ? "alert" : "status"}
      className={`rounded-md px-3 py-2 text-xs ${
        kind === "error" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"
      }`}
    >
      {children}
    </p>
  );
}

export function SubmitButton({ busy, children }: { busy: boolean; children: React.ReactNode }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="h-9 w-full rounded-md border border-zinc-900 bg-zinc-900 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {busy ? "Please wait..." : children}
    </button>
  );
}

import React from "react";
import Link from "next/link";

export const COMPANY = "Vadoo Internet Services Private Limited";
export const CONTACT_EMAIL = "support@vadoo.tv";
export const SERVICE_NAME = "Open Agent Connector";
export const SERVICE_URL = "https://connector.suparagent.ai";
export const LAST_UPDATED = "13 October 2026";

export function LegalPage({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="h-full overflow-y-auto bg-white">
      <main className="mx-auto max-w-3xl px-6 py-12 text-[15px] leading-7 text-zinc-700">
        <nav className="mb-8 flex items-center gap-4 text-sm text-zinc-500">
          <Link href="/" className="hover:text-zinc-900">
            {SERVICE_NAME}
          </Link>
          <span aria-hidden>/</span>
          <Link href="/privacy" className="hover:text-zinc-900">
            Privacy Policy
          </Link>
          <Link href="/terms" className="hover:text-zinc-900">
            Terms of Service
          </Link>
        </nav>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">{title}</h1>
        <p className="mt-2 text-sm text-zinc-500">Last updated: {LAST_UPDATED}</p>
        <div className="mt-8 space-y-6">{children}</div>
        <footer className="mt-12 border-t border-zinc-200 pt-6 text-sm text-zinc-500">
          {COMPANY} &middot;{" "}
          <a className="underline" href={`mailto:${CONTACT_EMAIL}`}>
            {CONTACT_EMAIL}
          </a>
        </footer>
      </main>
    </div>
  );
}

export function Section({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold text-zinc-900">{heading}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

export function List({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="list-disc space-y-1.5 pl-6">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

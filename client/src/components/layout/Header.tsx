"use client";

import React from "react";
import { Terminal, ExternalLink } from "lucide-react";

interface HeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function Header({ title, description, action }: HeaderProps) {
  return (
    <header className="h-14 px-6 bg-white border-b border-zinc-200 flex items-center justify-between shrink-0">
      <div>
        <h1 className="text-sm font-semibold text-zinc-900 tracking-tight">{title}</h1>
        {description && (
          <p className="text-xs text-zinc-500 hidden sm:block">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-3">
        {action}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-zinc-600 hover:text-zinc-900 border border-zinc-200 rounded-md hover:bg-zinc-50 transition-colors"
        >
          <ExternalLink size={12} />
          <span>API Docs</span>
        </a>
      </div>
    </header>
  );
}

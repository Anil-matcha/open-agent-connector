"use client";

import React from "react";
import { ExternalLink, Menu } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { useMobileNav } from "@/components/layout/MobileNavContext";

interface HeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function Header({ title, description, action }: HeaderProps) {
  const { open } = useMobileNav();

  return (
    <header className="h-14 px-4 sm:px-6 bg-white border-b border-zinc-200 flex items-center justify-between shrink-0 gap-3">
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Mobile Hamburger Menu Toggle */}
        <button
          type="button"
          onClick={open}
          className="md:hidden p-1.5 -ml-1 text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 rounded-md transition-colors shrink-0"
          aria-label="Open navigation menu"
        >
          <Menu size={18} />
        </button>

        <div className="min-w-0">
          <h1 className="text-sm font-semibold text-zinc-900 tracking-tight truncate">
            {title}
          </h1>
          {description && (
            <p className="text-xs text-zinc-500 hidden sm:block truncate">
              {description}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {action}
        <a
          href={`${API_BASE}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-2 sm:px-2.5 py-1 text-xs text-zinc-600 hover:text-zinc-900 border border-zinc-200 rounded-md hover:bg-zinc-50 transition-colors"
        >
          <ExternalLink size={12} />
          <span className="hidden xs:inline">API Docs</span>
        </a>
      </div>
    </header>
  );
}

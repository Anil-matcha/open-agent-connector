"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { API_BASE } from "@/lib/api";
import { AccessControl } from "@/components/layout/AccessControl";
import { useMobileNav } from "@/components/layout/MobileNavContext";
import {
  LayoutDashboard,
  Layers,
  Zap,
  KeyRound,
  ShieldCheck,
  History,
  X,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { isOpen, close } = useMobileNav();
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        setServerOnline(res.ok);
      } catch {
        setServerOnline(false);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { label: "Overview", href: "/", icon: <LayoutDashboard size={15} /> },
    { label: "Providers", href: "/providers", icon: <Layers size={15} /> },
    { label: "Actions", href: "/actions", icon: <Zap size={15} /> },
    {
      label: "Connections",
      href: "/connections",
      icon: <KeyRound size={15} />,
    },
    { label: "Run Logs", href: "/logs", icon: <History size={15} /> },
    {
      label: "Access Tokens",
      href: "/tokens",
      icon: <ShieldCheck size={15} />,
    },
  ];

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 backdrop-blur-xs md:hidden animate-in fade-in duration-200"
          onClick={close}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-zinc-200 flex flex-col shrink-0 select-none shadow-2xl transition-transform duration-200 ease-in-out md:static md:w-56 md:h-screen md:shadow-none md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-zinc-100 shrink-0">
          <Link href="/" onClick={close} className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-zinc-900 flex items-center justify-center text-white font-bold text-xs">
              C
            </div>
            <span className="font-semibold text-xs tracking-tight text-zinc-900">
              ConnectorHub
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <div
              title={serverOnline ? "Server connected" : "Server unreachable"}
              className="flex items-center gap-1.5"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  serverOnline === null
                    ? "bg-zinc-300"
                    : serverOnline
                      ? "bg-emerald-500 animate-pulse"
                      : "bg-rose-500"
                }`}
              />
            </div>

            {/* Mobile close button */}
            <button
              type="button"
              onClick={close}
              className="md:hidden p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
              aria-label="Close navigation"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-3 flex-1 space-y-0.5 overflow-y-auto">
          <div className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1 select-none">
            Platform
          </div>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={close}
                className={`flex items-center gap-2.5 px-2.5 py-2 md:py-1.5 text-xs rounded-md transition-colors ${
                  isActive
                    ? "bg-zinc-100 text-zinc-900 font-medium"
                    : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50"
                }`}
              >
                <span className={isActive ? "text-zinc-900" : "text-zinc-400"}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Account / Access Control */}
        <AccessControl />
      </aside>
    </>
  );
}

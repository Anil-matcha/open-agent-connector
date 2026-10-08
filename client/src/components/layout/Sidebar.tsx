"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Layers,
  Zap,
  KeyRound,
  ShieldCheck,
  History,
  Activity,
  Terminal,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch("http://localhost:8000/health");
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
    { label: "Connections", href: "/connections", icon: <KeyRound size={15} /> },
    { label: "Run Logs", href: "/logs", icon: <History size={15} /> },
    { label: "Access Tokens", href: "/tokens", icon: <ShieldCheck size={15} /> },
  ];

  return (
    <aside className="w-56 h-screen bg-white border-r border-zinc-200 flex flex-col shrink-0 select-none">
      {/* Brand */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-zinc-100">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-zinc-900 flex items-center justify-center text-white font-bold text-xs">
            C
          </div>
          <span className="font-semibold text-xs tracking-tight text-zinc-900">
            ConnectorHub
          </span>
        </Link>
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
              className={`flex items-center gap-2.5 px-2.5 py-1.5 text-xs rounded-md transition-colors ${
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

      {/* Footer Info */}
      <div className="p-3 border-t border-zinc-100 text-[11px] text-zinc-400 flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <span>Backend:</span>
          <span className="font-mono text-[10px] text-zinc-600">FastAPI</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Database:</span>
          <span className="font-mono text-[10px] text-zinc-600">SQLite</span>
        </div>
        <div className="flex items-center justify-between">
          <span>MCP Protocol:</span>
          <span className="font-mono text-[10px] text-emerald-600 font-medium">Ready</span>
        </div>
      </div>
    </aside>
  );
}

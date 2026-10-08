"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ProviderIcon } from "@/components/ui/ProviderIcon";
import { fetchApi } from "@/lib/api";
import {
  Layers,
  Zap,
  KeyRound,
  History,
  ArrowUpRight,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from "lucide-react";
import Link from "next/link";

interface Stats {
  totalRuns: number;
  successfulRuns: number;
  successRate: number;
  totalConnections: number;
  totalProviders: number;
  totalActions: number;
}

interface RunLog {
  id: string;
  actionId: string;
  service: string;
  caller: string;
  ok: boolean;
  statusCode: number;
  durationMs: number;
  startedAt: string;
  errorMessage?: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentRuns, setRecentRuns] = useState<RunLog[]>([]);
  const [copiedMcp, setCopiedMcp] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const statsRes = await fetchApi<{ data: Stats }>("/api/stats");
        setStats(statsRes.data);

        const runsRes = await fetchApi<{ data: RunLog[] }>("/api/runs?limit=6");
        setRecentRuns(runsRes.data);
      } catch (err) {
        console.error("Failed to load dashboard data", err);
      }
    }
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const mcpConfigSnippet = JSON.stringify(
    {
      mcpServers: {
        "connector-hub": {
          url: "http://localhost:8000/mcp",
          headers: {
            Authorization: "Bearer your-token-if-configured",
          },
        },
      },
    },
    null,
    2
  );

  function copyMcpSnippet() {
    navigator.clipboard.writeText(mcpConfigSnippet);
    setCopiedMcp(true);
    setTimeout(() => setCopiedMcp(false), 2000);
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Overview"
          description="Gateway status, provider connections, and execution statistics."
        />

        <main className="flex-1 overflow-y-auto min-h-0">
          <div className="p-6 flex flex-col gap-6 max-w-6xl">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3.5 bg-white border border-zinc-200 rounded-lg flex flex-col gap-1">
              <div className="flex items-center justify-between text-zinc-500 text-xs">
                <span>Total Providers</span>
                <Layers size={14} className="text-zinc-400" />
              </div>
              <div className="text-xl font-semibold text-zinc-900">
                {stats ? stats.totalProviders : "-"}
              </div>
              <div className="text-[11px] text-zinc-400">Available services</div>
            </div>

            <div className="p-3.5 bg-white border border-zinc-200 rounded-lg flex flex-col gap-1">
              <div className="flex items-center justify-between text-zinc-500 text-xs">
                <span>Active Actions</span>
                <Zap size={14} className="text-zinc-400" />
              </div>
              <div className="text-xl font-semibold text-zinc-900">
                {stats ? stats.totalActions : "-"}
              </div>
              <div className="text-[11px] text-zinc-400">Callable functions</div>
            </div>

            <div className="p-3.5 bg-white border border-zinc-200 rounded-lg flex flex-col gap-1">
              <div className="flex items-center justify-between text-zinc-500 text-xs">
                <span>Connected Accounts</span>
                <KeyRound size={14} className="text-zinc-400" />
              </div>
              <div className="text-xl font-semibold text-zinc-900">
                {stats ? stats.totalConnections : "-"}
              </div>
              <div className="text-[11px] text-zinc-400">Encrypted in SQLite</div>
            </div>

            <div className="p-3.5 bg-white border border-zinc-200 rounded-lg flex flex-col gap-1">
              <div className="flex items-center justify-between text-zinc-500 text-xs">
                <span>Execution Success</span>
                <History size={14} className="text-zinc-400" />
              </div>
              <div className="text-xl font-semibold text-zinc-900">
                {stats ? `${stats.successRate}%` : "-"}
              </div>
              <div className="text-[11px] text-zinc-400">
                {stats ? `${stats.totalRuns} total requests` : "-"}
              </div>
            </div>
          </div>

          {/* Quick MCP Setup Panel */}
          <div className="p-4 bg-white border border-zinc-200 rounded-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-900">
                  Model Context Protocol (MCP) Ready
                </span>
                <Badge variant="success">Active on /mcp</Badge>
              </div>
              <p className="text-xs text-zinc-500 max-w-xl">
                AI agents in Cursor, Claude Desktop, or LangChain can automatically discover,
                inspect, and execute all actions through the 5 meta-tools without leaking credentials.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={copyMcpSnippet}
              className="shrink-0"
            >
              {copiedMcp ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
              <span>{copiedMcp ? "Copied Config" : "Copy MCP JSON Config"}</span>
            </Button>
          </div>

          {/* Recent Runs Table */}
          <div className="bg-white border border-zinc-200 rounded-lg flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between">
              <div>
                <h2 className="text-xs font-semibold text-zinc-900">Recent Executions</h2>
                <p className="text-[11px] text-zinc-500">Live execution audit trail</p>
              </div>
              <Link
                href="/logs"
                className="text-xs text-zinc-600 hover:text-zinc-900 flex items-center gap-1 font-medium"
              >
                <span>View all</span>
                <ArrowUpRight size={12} />
              </Link>
            </div>

            {recentRuns.length === 0 ? (
              <div className="p-8 text-center text-xs text-zinc-400">
                No runs recorded yet. Test an action in the Actions playground!
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-50 border-b border-zinc-100 text-zinc-500 font-medium select-none">
                    <tr>
                      <th className="px-4 py-2">Status</th>
                      <th className="px-4 py-2">Action</th>
                      <th className="px-4 py-2">Caller</th>
                      <th className="px-4 py-2">Latency</th>
                      <th className="px-4 py-2">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {recentRuns.map((run) => (
                      <tr key={run.id} className="hover:bg-zinc-50/50">
                        <td className="px-4 py-2.5">
                          {run.ok ? (
                            <span className="flex items-center gap-1.5 text-emerald-700 font-medium">
                              <CheckCircle2 size={13} className="text-emerald-600" />
                              200 OK
                            </span>
                          ) : (
                            <span className="flex items-center gap-1.5 text-rose-700 font-medium">
                              <AlertCircle size={13} className="text-rose-600" />
                              {run.statusCode} Error
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-zinc-800">
                          <div className="flex items-center gap-2">
                            <ProviderIcon service={run.service} size="xs" />
                            <span>{run.actionId}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge variant="neutral">{run.caller}</Badge>
                        </td>
                        <td className="px-4 py-2.5 text-zinc-500">
                          {run.durationMs}ms
                        </td>
                        <td className="px-4 py-2.5 text-zinc-400 text-[11px]">
                          {new Date(run.startedAt).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
        </main>
      </div>
    </div>
  );
}

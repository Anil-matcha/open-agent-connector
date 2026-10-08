"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { fetchApi } from "@/lib/api";
import { KeyRound, Trash2, Plus, RefreshCw, CheckCircle2 } from "lucide-react";
import Link from "next/link";

interface ConnectionItem {
  id: string;
  service: string;
  connectionName: string;
  authType: string;
  accountId?: string;
  displayName?: string;
  grantedScopes?: string[];
  updatedAt: string;
}

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadConnections() {
    setLoading(true);
    try {
      const res = await fetchApi<{ data: ConnectionItem[] }>("/api/connections");
      setConnections(res.data);
    } catch (err) {
      console.error("Failed to load connections", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadConnections();
  }, []);

  async function handleDisconnect(service: string, connectionName: string) {
    if (!confirm(`Are you sure you want to disconnect '${service}' (${connectionName})?`)) {
      return;
    }
    try {
      await fetchApi(`/api/connections/${service}?connectionName=${connectionName}`, {
        method: "DELETE",
      });
      loadConnections();
    } catch (err: any) {
      alert(err.message || "Failed to disconnect.");
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Connected Accounts"
          description="Manage stored user credentials and account authorizations."
          action={
            <Link href="/providers">
              <Button size="sm" variant="primary">
                <Plus size={13} />
                <span>Connect Provider</span>
              </Button>
            </Link>
          }
        />

        <main className="flex-1 overflow-y-auto min-h-0">
          <div className="p-6 flex flex-col gap-6 max-w-6xl">
          <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between">
              <div>
                <h2 className="text-xs font-semibold text-zinc-900">Active Credentials</h2>
                <p className="text-[11px] text-zinc-500">
                  Credentials are encrypted at rest with AES-256-GCM.
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={loadConnections} loading={loading}>
                <RefreshCw size={11} />
                <span>Refresh</span>
              </Button>
            </div>

            {connections.length === 0 ? (
              <div className="p-12 text-center flex flex-col items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-400">
                  <KeyRound size={18} />
                </div>
                <div className="text-xs text-zinc-600 font-medium">No accounts connected yet</div>
                <p className="text-[11px] text-zinc-400 max-w-xs">
                  Connect your GitHub, Slack, or other accounts to allow AI agents to interact on your behalf.
                </p>
                <Link href="/providers">
                  <Button size="sm" variant="primary">
                    Browse Providers
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-50 border-b border-zinc-100 text-zinc-500 font-medium">
                    <tr>
                      <th className="px-4 py-2">Service</th>
                      <th className="px-4 py-2">Alias</th>
                      <th className="px-4 py-2">Account Profile</th>
                      <th className="px-4 py-2">Auth Type</th>
                      <th className="px-4 py-2">Last Updated</th>
                      <th className="px-4 py-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {connections.map((c) => (
                      <tr key={c.id} className="hover:bg-zinc-50/50">
                        <td className="px-4 py-3">
                          <span className="font-semibold text-zinc-900 capitalize">
                            {c.service}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="neutral">{c.connectionName}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col">
                            <span className="font-medium text-zinc-800">
                              {c.displayName || c.accountId || "Connected Account"}
                            </span>
                            {c.accountId && c.displayName && (
                              <span className="text-[10px] text-zinc-400 font-mono">
                                {c.accountId}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-zinc-600 capitalize">
                            {c.authType.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-zinc-400 text-[11px]">
                          {new Date(c.updatedAt).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDisconnect(c.service, c.connectionName)}
                            className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                          >
                            <Trash2 size={12} />
                            <span>Disconnect</span>
                          </Button>
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

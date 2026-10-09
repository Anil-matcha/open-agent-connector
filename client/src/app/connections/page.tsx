"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ProviderIcon } from "@/components/ui/ProviderIcon";
import { fetchApi } from "@/lib/api";
import { 
  KeyRound, 
  Trash2, 
  Plus, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Play, 
  RotateCcw, 
  PowerOff,
  ShieldAlert,
  Clock
} from "lucide-react";
import Link from "next/link";

interface ConnectionItem {
  id: string;
  service: string;
  connectionName: string;
  authType: string;
  accountId?: string;
  displayName?: string;
  grantedScopes?: string[];
  status?: "active" | "expired" | "revoked" | "error" | string;
  statusMessage?: string;
  lastValidatedAt?: string;
  expiresAt?: string;
  updatedAt: string;
}

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testFeedback, setTestFeedback] = useState<{ id: string; success: boolean; message: string } | null>(null);
  
  // Reconnect / Rotate Modal State
  const [reconnectConn, setReconnectConn] = useState<ConnectionItem | null>(null);
  const [rotateKey, setRotateKey] = useState("");
  const [rotating, setRotating] = useState(false);
  const [rotateError, setRotateError] = useState<string | null>(null);

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

  async function handleTest(conn: ConnectionItem) {
    setTestingId(conn.id);
    setTestFeedback(null);
    try {
      const res = await fetchApi<{ success: boolean; status: string; message?: string; profile?: any }>(
        `/api/connections/${conn.id}/test`,
        { method: "POST" }
      );
      if (res.success) {
        setTestFeedback({
          id: conn.id,
          success: true,
          message: `Live credentials validated successfully (${res.profile?.account_id || "Active"})`,
        });
      } else {
        setTestFeedback({
          id: conn.id,
          success: false,
          message: res.message || "Credential verification failed",
        });
      }
      loadConnections();
    } catch (err: any) {
      setTestFeedback({
        id: conn.id,
        success: false,
        message: err.message || "Connection test failed",
      });
      loadConnections();
    } finally {
      setTestingId(null);
    }
  }

  async function handleDisconnect(conn: ConnectionItem) {
    if (!confirm(`Are you sure you want to revoke '${conn.service}' (${conn.connectionName})? Agents will no longer be able to execute actions with this account until reconnected.`)) {
      return;
    }
    try {
      await fetchApi(`/api/connections/${conn.id}/disconnect`, {
        method: "POST",
      });
      loadConnections();
    } catch (err: any) {
      alert(err.message || "Failed to disconnect.");
    }
  }

  async function handleDelete(conn: ConnectionItem) {
    if (!confirm(`Permanently delete stored connection for '${conn.service}' (${conn.connectionName})? This cannot be undone.`)) {
      return;
    }
    try {
      await fetchApi(`/api/connections/${conn.id}`, {
        method: "DELETE",
      });
      loadConnections();
    } catch (err: any) {
      alert(err.message || "Failed to delete connection.");
    }
  }

  async function handleRotateSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reconnectConn) return;
    setRotating(true);
    setRotateError(null);

    try {
      await fetchApi(`/api/connections/${reconnectConn.id}/reconnect`, {
        method: "POST",
        body: JSON.stringify({
          values: {
            apiKey: rotateKey.trim(),
            accessToken: rotateKey.trim(),
          },
        }),
      });
      setReconnectConn(null);
      setRotateKey("");
      loadConnections();
    } catch (err: any) {
      setRotateError(err.message || "Failed to reconnect credentials.");
    } finally {
      setRotating(false);
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Connected Accounts"
          description="Manage stored credentials, live lifecycle health, and provider authorizations."
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
            {testFeedback && (
              <div
                className={`p-3 text-xs rounded-lg border flex items-center justify-between ${
                  testFeedback.success
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                    : "bg-rose-50 border-rose-200 text-rose-800"
                }`}
              >
                <div className="flex items-center gap-2">
                  {testFeedback.success ? (
                    <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                  ) : (
                    <AlertCircle size={15} className="text-rose-600 shrink-0" />
                  )}
                  <span>{testFeedback.message}</span>
                </div>
                <button
                  onClick={() => setTestFeedback(null)}
                  className="text-[11px] underline opacity-70 hover:opacity-100"
                >
                  Dismiss
                </button>
              </div>
            )}

            <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden flex flex-col shadow-sm">
              <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between">
                <div>
                  <h2 className="text-xs font-semibold text-zinc-900">Configured Connections</h2>
                  <p className="text-[11px] text-zinc-500">
                    Credentials are encrypted with AES-256-GCM. Status is monitored in real-time.
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
                    Connect your GitHub, Slack, or other accounts to allow AI agents to safely execute actions on your behalf.
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
                        <th className="px-4 py-2.5">Service & Alias</th>
                        <th className="px-4 py-2.5">Account Profile</th>
                        <th className="px-4 py-2.5">Status</th>
                        <th className="px-4 py-2.5">Auth Type</th>
                        <th className="px-4 py-2.5">Last Validated</th>
                        <th className="px-4 py-2.5 text-right">Lifecycle Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                      {connections.map((c) => {
                        const status = c.status || "active";
                        const isTesting = testingId === c.id;

                        return (
                          <tr key={c.id} className="hover:bg-zinc-50/60 transition-colors">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2.5">
                                <ProviderIcon service={c.service} size="md" />
                                <div className="flex flex-col">
                                  <span className="font-semibold text-zinc-900 capitalize">
                                    {c.service}
                                  </span>
                                  <span className="text-[10px] text-zinc-400 font-mono">
                                    alias: {c.connectionName}
                                  </span>
                                </div>
                              </div>
                            </td>

                            <td className="px-4 py-3">
                              <div className="flex flex-col">
                                <span className="font-medium text-zinc-800">
                                  {c.displayName || c.accountId || "Connected Account"}
                                </span>
                                {c.accountId && c.displayName && (
                                  <span className="text-[10px] text-zinc-400 font-mono">
                                    @{c.accountId}
                                  </span>
                                )}
                              </div>
                            </td>

                            <td className="px-4 py-3">
                              <div className="flex flex-col gap-1 items-start">
                                {status === "active" && (
                                  <Badge variant="success">Active</Badge>
                                )}
                                {status === "revoked" && (
                                  <Badge variant="warning">Revoked</Badge>
                                )}
                                {status === "error" && (
                                  <Badge variant="danger">Error</Badge>
                                )}
                                {status === "expired" && (
                                  <Badge variant="danger">Expired</Badge>
                                )}
                                {c.statusMessage && (
                                  <span className="text-[10px] text-rose-600 max-w-xs truncate" title={c.statusMessage}>
                                    {c.statusMessage}
                                  </span>
                                )}
                              </div>
                            </td>

                            <td className="px-4 py-3">
                              <span className="text-zinc-600 capitalize">
                                {c.authType.replace("_", " ")}
                              </span>
                            </td>

                            <td className="px-4 py-3 text-zinc-500 text-[11px]">
                              {c.lastValidatedAt ? (
                                <div className="flex items-center gap-1">
                                  <Clock size={11} className="text-zinc-400" />
                                  <span>{new Date(c.lastValidatedAt).toLocaleString()}</span>
                                </div>
                              ) : (
                                <span className="text-zinc-400">Never tested</span>
                              )}
                            </td>

                            <td className="px-4 py-3 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleTest(c)}
                                  loading={isTesting}
                                  title="Test live credentials with provider"
                                  className="h-7 px-2 text-[11px]"
                                >
                                  <Play size={10} className="text-zinc-600" />
                                  <span>Test</span>
                                </Button>

                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    setReconnectConn(c);
                                    setRotateKey("");
                                    setRotateError(null);
                                  }}
                                  title="Rotate / update credentials"
                                  className="h-7 px-2 text-[11px]"
                                >
                                  <RotateCcw size={10} className="text-zinc-600" />
                                  <span>Rotate</span>
                                </Button>

                                {status === "active" ? (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleDisconnect(c)}
                                    title="Revoke connection"
                                    className="h-7 px-2 text-[11px] text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                                  >
                                    <PowerOff size={11} />
                                    <span>Revoke</span>
                                  </Button>
                                ) : null}

                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleDelete(c)}
                                  title="Permanently delete connection"
                                  className="h-7 px-2 text-[11px] text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                                >
                                  <Trash2 size={11} />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Credential Rotation / Reconnect Modal */}
      {reconnectConn && (
        <Modal
          isOpen={true}
          onClose={() => setReconnectConn(null)}
          title={`Update Credentials for ${reconnectConn.service}`}
          description={`Update or rotate secret credentials for alias '${reconnectConn.connectionName}'. Credentials will be tested live before saving.`}
          maxWidth="md"
        >
          <form onSubmit={handleRotateSubmit} className="flex flex-col gap-4">
            {rotateError && (
              <div className="p-3 text-xs text-rose-800 bg-rose-50 border border-rose-200 rounded-md flex items-start gap-2">
                <AlertCircle size={14} className="text-rose-600 mt-0.5 shrink-0" />
                <div>
                  <div className="font-semibold">Validation Error</div>
                  <div className="mt-0.5">{rotateError}</div>
                </div>
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-zinc-700">
                New API Key / Access Token
              </label>
              <input
                type="password"
                value={rotateKey}
                onChange={(e) => setRotateKey(e.target.value)}
                placeholder="Enter new token..."
                required
                className="h-9 px-3 text-xs font-mono bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
              />
              <p className="text-[11px] text-zinc-400">
                The new credential will be verified in real-time with the provider, encrypted with AES-256-GCM, and replace the previous key.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-100">
              <Button type="button" variant="ghost" onClick={() => setReconnectConn(null)} disabled={rotating}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" loading={rotating}>
                {rotating ? "Validating & Rotating..." : "Rotate & Activate"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

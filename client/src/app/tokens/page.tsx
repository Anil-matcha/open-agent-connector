"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { fetchApi } from "@/lib/api";
import { ShieldCheck, Plus, Trash2, Copy, Check, Key } from "lucide-react";

interface TokenItem {
  id: string;
  name: string;
  allowedActions: string[];
  blockedActions: string[];
  allowedProxies: string[];
  createdAt: string;
  lastUsedAt?: string;
}

export default function TokensPage() {
  const [tokens, setTokens] = useState<TokenItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [allowedPattern, setAllowedPattern] = useState("*");
  const [createdRawToken, setCreatedRawToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  async function loadTokens() {
    try {
      const res = await fetchApi<{ data: TokenItem[] }>("/api/runtime-tokens");
      setTokens(res.data);
    } catch (err) {
      console.error("Failed to load tokens", err);
    }
  }

  useEffect(() => {
    loadTokens();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const patterns = allowedPattern.split(",").map((p) => p.trim()).filter(Boolean);
      const res = await fetchApi<{ data: { rawToken: string } }>("/api/runtime-tokens", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          allowedActions: patterns.length > 0 ? patterns : ["*"],
        }),
      });
      setCreatedRawToken(res.data.rawToken);
      loadTokens();
    } catch (err: any) {
      alert(err.message || "Failed to create token.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRevoke(id: string, tokenName: string) {
    if (!confirm(`Revoke token '${tokenName}'? Clients using this token will be denied.`)) return;
    try {
      await fetchApi(`/api/runtime-tokens/${id}`, { method: "DELETE" });
      loadTokens();
    } catch (err: any) {
      alert(err.message || "Failed to revoke token.");
    }
  }

  function copyToken() {
    if (!createdRawToken) return;
    navigator.clipboard.writeText(createdRawToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Access Tokens"
          description="Issue scoped Bearer tokens to restrict which actions an AI agent can execute."
          action={
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                setName("");
                setAllowedPattern("*");
                setCreatedRawToken(null);
                setIsModalOpen(true);
              }}
            >
              <Plus size={13} />
              <span>Create Token</span>
            </Button>
          }
        />

        <main className="flex-1 overflow-y-auto min-h-0">
          <div className="p-6 flex flex-col gap-6 max-w-6xl">
          <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between">
              <div>
                <h2 className="text-xs font-semibold text-zinc-900">Active Bearer Tokens</h2>
                <p className="text-[11px] text-zinc-500">
                  Tokens carry granular allow/block rules evaluated on every request.
                </p>
              </div>
            </div>

            {tokens.length === 0 ? (
              <div className="p-12 text-center text-xs text-zinc-400">
                No runtime tokens created yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-50 border-b border-zinc-100 text-zinc-500 font-medium">
                    <tr>
                      <th className="px-4 py-2">Name</th>
                      <th className="px-4 py-2">Allowed Actions</th>
                      <th className="px-4 py-2">Created</th>
                      <th className="px-4 py-2">Last Used</th>
                      <th className="px-4 py-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {tokens.map((t) => (
                      <tr key={t.id} className="hover:bg-zinc-50/50">
                        <td className="px-4 py-3 font-medium text-zinc-900">
                          {t.name}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1 flex-wrap">
                            {t.allowedActions.map((pattern) => (
                              <code
                                key={pattern}
                                className="px-1.5 py-0.5 bg-zinc-100 rounded text-[11px] text-zinc-700 font-mono"
                              >
                                {pattern}
                              </code>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-zinc-400 text-[11px]">
                          {new Date(t.createdAt).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-zinc-400 text-[11px]">
                          {t.lastUsedAt ? new Date(t.lastUsedAt).toLocaleDateString() : "Never"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRevoke(t.id, t.name)}
                            className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                          >
                            <Trash2 size={12} />
                            <span>Revoke</span>
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

        {/* Create Token Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Create Scoped Token"
          description="Generate a bearer token with custom action access rules."
        >
          {createdRawToken ? (
            <div className="flex flex-col gap-3">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-emerald-800 text-xs">
                Token generated! Please copy it now; you will not be able to see it again.
              </div>

              <div className="flex items-center gap-2 p-2 bg-zinc-50 border border-zinc-200 rounded-md font-mono text-xs break-all">
                <span className="flex-1">{createdRawToken}</span>
                <Button size="sm" variant="outline" onClick={copyToken}>
                  {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  <span>{copied ? "Copied" : "Copy"}</span>
                </Button>
              </div>

              <Button
                variant="primary"
                onClick={() => setIsModalOpen(false)}
                className="mt-2"
              >
                Done
              </Button>
            </div>
          ) : (
            <form onSubmit={handleCreate} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-600">Token Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Agent Production, Code Review Bot"
                  required
                  className="h-9 px-3 text-sm bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-600">
                  Allowed Actions (Wildcard Patterns)
                </label>
                <input
                  type="text"
                  value={allowedPattern}
                  onChange={(e) => setAllowedPattern(e.target.value)}
                  placeholder="* or github.*, slack.post_message"
                  required
                  className="h-9 px-3 text-sm bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 font-mono text-xs text-zinc-900"
                />
                <p className="text-[11px] text-zinc-400">
                  Comma-separated patterns. Use <code>*</code> for all actions, or <code>github.*</code> to restrict.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setIsModalOpen(false)}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" loading={loading}>
                  Generate Token
                </Button>
              </div>
            </form>
          )}
        </Modal>
        </main>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ProviderIcon } from "@/components/ui/ProviderIcon";
import { ConnectModal } from "@/components/providers/ConnectModal";
import { fetchApi } from "@/lib/api";
import { Search, ChevronRight, CheckCircle2, ArrowUpRight } from "lucide-react";

interface ProviderItem {
  service: string;
  displayName: string;
  category: string;
  authTypes: string[];
  authConfigs?: any[];
  description: string;
  homepageUrl: string;
  actionCount: number;
}

interface ConnectionItem {
  id: string;
  service: string;
  connectionName: string;
  displayName?: string;
}

type FilterType = "all" | "connected" | "not_connected" | "oauth_needs_config";

export default function ProvidersPage() {
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterType>("all");
  const [connectModalData, setConnectModalData] = useState<ProviderItem | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadData() {
    try {
      const pRes = await fetchApi<{ data: ProviderItem[] }>("/v1/providers");
      setProviders(pRes.data || []);

      const cRes = await fetchApi<{ data: ConnectionItem[] }>("/api/connections");
      setConnections(cRes.data || []);
    } catch (err) {
      console.error("Failed to load providers", err);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function isConnected(provider: ProviderItem) {
    return connections.some((c) => c.service === provider.service);
  }

  function hasOAuth(provider: ProviderItem) {
    return provider.authTypes?.some((t) => t.toLowerCase().includes("oauth")) ?? false;
  }

  function getActionLabel(provider: ProviderItem) {
    if (isConnected(provider)) {
      return "Manage";
    }
    if (hasOAuth(provider)) {
      return "1-Click Connect";
    }
    return "Connect";
  }

  const counts = {
    all: providers.length,
    connected: providers.filter((p) => isConnected(p)).length,
    notConnected: providers.filter((p) => !isConnected(p)).length,
    oauthNeedsConfig: providers.filter((p) => hasOAuth(p) && !isConnected(p)).length,
  };

  const filterButtons: { id: FilterType; label: string; count: number }[] = [
    { id: "all", label: "All", count: counts.all },
    { id: "connected", label: "Connected", count: counts.connected },
    { id: "not_connected", label: "Not connected", count: counts.notConnected },
    { id: "oauth_needs_config", label: "OAuth 2.0", count: counts.oauthNeedsConfig },
  ];

  const filteredProviders = providers.filter((p) => {
    if (filter === "connected" && !isConnected(p)) return false;
    if (filter === "not_connected" && isConnected(p)) return false;
    if (filter === "oauth_needs_config" && (!hasOAuth(p) || isConnected(p))) return false;

    if (search.trim()) {
      const q = search.toLowerCase().trim();
      const matchName = p.displayName.toLowerCase().includes(q);
      const matchService = p.service.toLowerCase().includes(q);
      const matchDesc = p.description?.toLowerCase().includes(q);
      return matchName || matchService || matchDesc;
    }

    return true;
  });

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Providers"
          description="Browse available services and configure authenticated credentials."
        />

        <main className="flex-1 overflow-y-auto min-h-0 p-3.5 sm:p-6 flex flex-col gap-4">
          {successMessage && (
            <div className="p-3 text-xs rounded-lg border bg-emerald-50 border-emerald-200 text-emerald-800 flex items-center justify-between shadow-xs animate-fadeIn">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={15} className="text-emerald-600 shrink-0" />
                <span className="font-medium">{successMessage}</span>
              </div>
              <button
                onClick={() => setSuccessMessage(null)}
                className="text-[11px] underline opacity-70 hover:opacity-100 cursor-pointer"
              >
                Dismiss
              </button>
            </div>
          )}

          <div className="bg-white border border-zinc-200 rounded-xl p-4 sm:p-6 flex flex-col gap-4 shadow-xs">
            {/* Top Bar: Title & Search */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-zinc-900 tracking-tight">
                Providers
              </h2>
              <div className="relative w-full sm:w-72">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none"
                />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search providers"
                  className="w-full h-8 pl-8 pr-3 text-xs bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 placeholder:text-zinc-400 text-zinc-800 transition-colors"
                />
              </div>
            </div>

            {/* Filter Buttons & Showing Count */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
                {filterButtons.map((btn) => {
                  const isActive = filter === btn.id;
                  return (
                    <button
                      key={btn.id}
                      onClick={() => setFilter(btn.id)}
                      className={`px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer shrink-0 ${
                        isActive
                          ? "bg-zinc-900 text-white shadow-xs"
                          : "bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                      }`}
                    >
                      <span>{btn.label}</span>
                      <span
                        className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold leading-none ${
                          isActive
                            ? "bg-zinc-700 text-zinc-100"
                            : "bg-zinc-100 text-zinc-500"
                        }`}
                      >
                        {btn.count}
                      </span>
                    </button>
                  );
                })}
              </div>

              <span className="text-xs text-zinc-400 font-normal shrink-0">
                Showing {filteredProviders.length} / {providers.length}
              </span>
            </div>

            {/* Providers Grid (3 columns) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-1">
              {filteredProviders.map((provider) => {
                const connected = isConnected(provider);
                const actionLabel = getActionLabel(provider);

                return (
                  <div
                    key={provider.service}
                    className="group flex items-center justify-between px-3.5 py-2.5 bg-white border border-zinc-200 rounded-lg hover:border-zinc-300 hover:bg-zinc-50/50 transition-all min-h-[50px]"
                  >
                    {/* Left: Icon, Name link to actions, Configured badge */}
                    <Link
                      href={`/actions?service=${provider.service}`}
                      className="flex items-center gap-2.5 min-w-0 mr-2 group/title"
                      title={`View ${provider.actionCount} actions for ${provider.displayName}`}
                    >
                      <div className="w-7 h-7 rounded-md flex items-center justify-center shrink-0 overflow-hidden bg-zinc-50 group-hover/title:opacity-85 transition-opacity">
                        <ProviderIcon
                          service={provider.service}
                          displayName={provider.displayName}
                          size="md"
                        />
                      </div>
                      <span className="text-xs font-semibold text-zinc-900 group-hover/title:text-blue-600 truncate transition-colors">
                        {provider.displayName}
                      </span>
                      {connected && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium text-emerald-700 border border-emerald-200 bg-emerald-50 shrink-0">
                          <CheckCircle2 size={10} className="text-emerald-600" />
                          Configured
                        </span>
                      )}
                    </Link>

                    {/* Right: Actions redirect link & Connect/Manage button */}
                    <div className="shrink-0 flex items-center gap-2">
                      <Link
                        href={`/actions?service=${provider.service}`}
                        className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 rounded transition-colors"
                        title={`Browse ${provider.actionCount} actions`}
                      >
                        <span>{provider.actionCount} actions</span>
                        <ArrowUpRight size={10} className="text-zinc-400" />
                      </Link>

                      <button
                        onClick={() => setConnectModalData(provider)}
                        className="flex items-center text-zinc-400 group-hover:text-zinc-700 hover:text-zinc-900 transition-colors cursor-pointer text-left"
                      >
                        <span className="text-[11px] font-normal truncate">
                          {actionLabel}
                        </span>
                        <ChevronRight
                          size={13}
                          className="ml-0.5 text-zinc-400 group-hover:text-zinc-600 transition-colors shrink-0"
                        />
                      </button>
                    </div>
                  </div>
                );
              })}

              {filteredProviders.length === 0 && (
                <div className="col-span-full py-12 text-center text-xs text-zinc-400">
                  No providers found matching &quot;{search}&quot;
                </div>
              )}
            </div>
          </div>

          {/* Connect Modal */}
          {connectModalData && (
            <ConnectModal
              isOpen={Boolean(connectModalData)}
              onClose={() => setConnectModalData(null)}
              service={connectModalData.service}
              displayName={connectModalData.displayName}
              authTypes={connectModalData.authTypes}
              authConfigs={connectModalData.authConfigs}
              onSuccess={() => {
                const name = connectModalData.displayName;
                loadData();
                setSuccessMessage(`Successfully connected ${name}! Connection is now active.`);
                setTimeout(() => setSuccessMessage(null), 5000);
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}

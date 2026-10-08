"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CustomSelect } from "@/components/ui/CustomSelect";
import { ProviderIcon } from "@/components/ui/ProviderIcon";
import { ConnectModal } from "@/components/providers/ConnectModal";
import { fetchApi } from "@/lib/api";
import { KeyRound, ArrowRight, CheckCircle2, ShieldAlert } from "lucide-react";
import Link from "next/link";


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

export default function ProvidersPage() {
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [connectModalData, setConnectModalData] = useState<ProviderItem | null>(null);

  async function loadData() {
    try {
      const pRes = await fetchApi<{ data: ProviderItem[] }>("/v1/providers");
      setProviders(pRes.data);

      const cRes = await fetchApi<{ data: ConnectionItem[] }>("/api/connections");
      setConnections(cRes.data);
    } catch (err) {
      console.error("Failed to load providers", err);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const categories = Array.from(new Set(providers.map((p) => p.category)));
  const categoryOptions = [
    { value: "all", label: "All Categories" },
    ...categories.map((c) => ({ value: c, label: c })),
  ];

  const filteredProviders = providers.filter((p) => {
    const matchesCategory =
      selectedCategory === "all" || p.category.toLowerCase() === selectedCategory.toLowerCase();
    const matchesSearch =
      p.displayName.toLowerCase().includes(search.toLowerCase()) ||
      p.service.toLowerCase().includes(search.toLowerCase()) ||
      p.description.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  function isConnected(provider: ProviderItem) {
    if (provider.authTypes.includes("no_auth") && provider.authTypes.length === 1) return true;
    return connections.some((c) => c.service === provider.service);
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Provider Catalog"
          description="Browse available services and configure authenticated credentials."
        />

        <main className="flex-1 overflow-y-auto min-h-0">
          <div className="p-6 flex flex-col gap-6 max-w-6xl">
          {/* Filter Bar with CustomSelect */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 border border-zinc-200 rounded-lg">
            <div className="w-full sm:w-64">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search providers..."
                className="w-full h-9 px-3 text-xs bg-zinc-50 border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 placeholder:text-zinc-400"
              />
            </div>

            {/* Custom Category Dropdown */}
            <div className="w-full sm:w-56">
              <CustomSelect
                options={categoryOptions}
                value={selectedCategory}
                onChange={setSelectedCategory}
              />
            </div>
          </div>

          {/* Providers Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredProviders.map((provider) => {
              const isPublic = provider.authTypes.includes("no_auth") && provider.authTypes.length === 1;
              const connected = isConnected(provider);
              return (
                <div
                  key={provider.service}
                  className="bg-white border border-zinc-200 rounded-lg p-4 flex flex-col justify-between gap-3 hover:border-zinc-300 transition-colors"
                >
                  <div className="flex flex-col gap-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <ProviderIcon
                          service={provider.service}
                          displayName={provider.displayName}
                          size="md"
                        />
                        <div>
                          <h3 className="text-xs font-semibold text-zinc-900">
                            {provider.displayName}
                          </h3>
                          <span className="text-[10px] text-zinc-400 font-mono">
                            {provider.service}
                          </span>
                        </div>
                      </div>
                      {connected ? (

                        <Badge variant="success">
                          <CheckCircle2 size={10} className="mr-1" />
                          Ready
                        </Badge>
                      ) : (
                        <Badge variant="neutral">Not Connected</Badge>
                      )}
                    </div>

                    <p className="text-xs text-zinc-600 line-clamp-2">
                      {provider.description}
                    </p>

                    <div className="flex items-center gap-1.5 flex-wrap pt-1">
                      <Badge variant="neutral">{provider.category}</Badge>
                      <span className="text-[11px] text-zinc-400">
                        {provider.actionCount} actions
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-zinc-100">
                    <Link
                      href={`/actions?service=${provider.service}`}
                      className="text-xs text-zinc-500 hover:text-zinc-900 flex items-center gap-1 font-medium"
                    >
                      <span>Actions</span>
                      <ArrowRight size={11} />
                    </Link>

                    {!isPublic ? (
                      <Button
                        size="sm"
                        variant={connected ? "outline" : "primary"}
                        onClick={() => setConnectModalData(provider)}
                      >
                        <KeyRound size={11} />
                        <span>{connected ? "Configure" : "Connect"}</span>
                      </Button>
                    ) : (
                      <span className="text-[11px] text-emerald-600 font-medium">
                        Public API (No Auth)
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
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
            onSuccess={loadData}
          />
        )}
        </main>
      </div>
    </div>
  );
}

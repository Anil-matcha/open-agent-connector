"use client";

import React, { useEffect, useState, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CustomSelect } from "@/components/ui/CustomSelect";
import { ProviderIcon } from "@/components/ui/ProviderIcon";
import { ActionRunnerModal } from "@/components/providers/ActionRunnerModal";
import { fetchApi } from "@/lib/api";
import {
  Play,
  Search,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  X,
  Layers,
  Sparkles,
  SlidersHorizontal,
} from "lucide-react";

interface ActionItem {
  id: string;
  name: string;
  description: string;
  service?: string;
  providerName?: string;
  category?: string;
  inputSchema: any;
  outputSchema?: any;
  requiredScopes?: string[];
}

interface ProviderSummary {
  service: string;
  displayName: string;
}

function ActionsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const urlService = searchParams.get("service") || "all";
  const urlCategory = searchParams.get("category") || "all";

  const [actions, setActions] = useState<ActionItem[]>([]);
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [selectedService, setSelectedService] = useState(urlService);
  const [selectedCategory, setSelectedCategory] = useState(urlCategory);
  const [search, setSearch] = useState("");
  const [runningAction, setRunningAction] = useState<ActionItem | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(25);
  const [loading, setLoading] = useState(true);

  // Sync state if URL search param changes
  useEffect(() => {
    if (urlService) setSelectedService(urlService);
    if (urlCategory) setSelectedCategory(urlCategory);
  }, [urlService, urlCategory]);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [pRes, aRes] = await Promise.all([
          fetchApi<{ data: ProviderSummary[] }>("/v1/providers"),
          fetchApi<{ data: ActionItem[] }>("/v1/actions"),
        ]);
        setProviders(pRes.data);
        setActions(aRes.data);
      } catch (err) {
        console.error("Failed to load actions", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Compute available categories based on currently selected service
  const availableCategories = useMemo(() => {
    const relevantActions =
      selectedService === "all"
        ? actions
        : actions.filter(
            (a) =>
              a.service === selectedService ||
              a.id.startsWith(`${selectedService}.`)
          );

    const cats = Array.from(
      new Set(
        relevantActions
          .map((a) => a.category?.trim())
          .filter((c): c is string => Boolean(c))
      )
    ).sort();

    return ["all", ...cats];
  }, [actions, selectedService]);

  // Reset category if selected category is not in the new provider's categories
  useEffect(() => {
    if (
      selectedCategory !== "all" &&
      !availableCategories.includes(selectedCategory)
    ) {
      setSelectedCategory("all");
    }
    setCurrentPage(1);
  }, [selectedService, availableCategories, selectedCategory]);

  // Reset page when search or filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [search, selectedService, selectedCategory, pageSize]);

  // Provider dropdown options
  const providerOptions = useMemo(() => {
    return [
      {
        value: "all",
        label: `All Providers (${actions.length})`,
      },
      ...providers.map((p) => {
        const count = actions.filter(
          (a) => a.service === p.service || a.id.startsWith(`${p.service}.`)
        ).length;
        return {
          value: p.service,
          label: `${p.displayName} (${count})`,
        };
      }),
    ];
  }, [providers, actions]);

  // Category dropdown options
  const categoryOptions = useMemo(() => {
    return availableCategories.map((c) => ({
      value: c,
      label: c === "all" ? "All Categories" : c,
    }));
  }, [availableCategories]);

  // Page size options
  const pageSizeOptions = [
    { value: "20", label: "20 per page" },
    { value: "25", label: "25 per page" },
    { value: "50", label: "50 per page" },
    { value: "100", label: "100 per page" },
    { value: "all", label: "Show all" },
  ];

  // Filter actions
  const filteredActions = useMemo(() => {
    return actions.filter((action) => {
      const matchesService =
        selectedService === "all" ||
        action.service === selectedService ||
        action.id.startsWith(`${selectedService}.`);

      const matchesCategory =
        selectedCategory === "all" ||
        (action.category &&
          action.category.toLowerCase() === selectedCategory.toLowerCase());

      const query = search.toLowerCase().trim();
      if (!query) return matchesService && matchesCategory;

      const propKeys = Object.keys(action.inputSchema?.properties || {});
      const matchesSearch =
        action.name.toLowerCase().includes(query) ||
        action.id.toLowerCase().includes(query) ||
        action.description.toLowerCase().includes(query) ||
        (action.category && action.category.toLowerCase().includes(query)) ||
        propKeys.some((k) => k.toLowerCase().includes(query));

      return matchesService && matchesCategory && matchesSearch;
    });
  }, [actions, selectedService, selectedCategory, search]);

  // Pagination calculation
  const totalItems = filteredActions.length;
  const effectivePageSize = pageSize === -1 ? totalItems || 1 : pageSize;
  const totalPages = Math.max(1, Math.ceil(totalItems / effectivePageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedActions = useMemo(() => {
    if (pageSize === -1) return filteredActions;
    const startIndex = (safeCurrentPage - 1) * effectivePageSize;
    return filteredActions.slice(startIndex, startIndex + effectivePageSize);
  }, [filteredActions, safeCurrentPage, effectivePageSize, pageSize]);

  const startIndexNumber =
    totalItems === 0 ? 0 : (safeCurrentPage - 1) * effectivePageSize + 1;
  const endIndexNumber =
    pageSize === -1
      ? totalItems
      : Math.min(safeCurrentPage * effectivePageSize, totalItems);

  function copyActionId(id: string) {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  }

  function clearAllFilters() {
    setSearch("");
    setSelectedService("all");
    setSelectedCategory("all");
    setCurrentPage(1);
    router.push("/actions");
  }

  const hasActiveFilters =
    Boolean(search) || selectedService !== "all" || selectedCategory !== "all";

  return (
    <div className="p-6 flex flex-col gap-5 max-w-6xl mx-auto w-full">
      {/* Top Filter and Controls Bar */}
      <div className="bg-white border border-zinc-200/80 rounded-xl p-4 shadow-2xs flex flex-col gap-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          {/* Search Bar */}
          <div className="md:col-span-5 relative">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by action name, ID, category, or parameter..."
              className="w-full h-10 pl-9 pr-8 text-xs bg-zinc-50/60 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1.5 focus:ring-zinc-900 focus:bg-white placeholder:text-zinc-400 transition"
            />
            <Search
              size={14}
              className="text-zinc-400 absolute left-3 top-3 pointer-events-none"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-2.5 text-zinc-400 hover:text-zinc-700 p-0.5 rounded"
                title="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Provider Filter */}
          <div className="md:col-span-3">
            <CustomSelect
              options={providerOptions}
              value={selectedService}
              onChange={(val) => {
                setSelectedService(val);
                router.push(val === "all" ? "/actions" : `/actions?service=${val}`);
              }}
            />
          </div>

          {/* Category Filter */}
          <div className="md:col-span-2">
            <CustomSelect
              options={categoryOptions}
              value={selectedCategory}
              onChange={setSelectedCategory}
            />
          </div>

          {/* Page Size Filter */}
          <div className="md:col-span-2">
            <CustomSelect
              options={pageSizeOptions}
              value={pageSize === -1 ? "all" : String(pageSize)}
              onChange={(val) => setPageSize(val === "all" ? -1 : Number(val))}
            />
          </div>
        </div>

        {/* Quick Category Chips */}
        {availableCategories.length > 2 && (
          <div className="flex items-center gap-1.5 overflow-x-auto pt-1 pb-0.5 scrollbar-none text-[11px]">
            <span className="text-zinc-400 font-medium shrink-0 flex items-center gap-1 mr-1">
              <SlidersHorizontal size={12} />
              Category:
            </span>
            {availableCategories.map((cat) => {
              const isSelected = selectedCategory === cat;
              const label = cat === "all" ? "All" : cat;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-2.5 py-1 rounded-md shrink-0 font-medium transition-all ${
                    isSelected
                      ? "bg-zinc-900 text-white shadow-2xs"
                      : "bg-zinc-100/80 text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Results Header & Summary Stats */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-zinc-900">
            {totalItems} {totalItems === 1 ? "Action" : "Actions"} Available
          </span>
          {totalItems > 0 && pageSize !== -1 && (
            <span className="text-xs text-zinc-400">
              (Showing {startIndexNumber}–{endIndexNumber})
            </span>
          )}
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="text-[11px] text-zinc-500 hover:text-zinc-900 underline flex items-center gap-1 ml-2 font-medium"
            >
              <X size={11} /> Clear filters
            </button>
          )}
        </div>

        {/* Pagination Jump on top right if multiple pages */}
        {totalPages > 1 && pageSize !== -1 && (
          <div className="flex items-center gap-1 text-xs text-zinc-500">
            <span>
              Page {safeCurrentPage} of {totalPages}
            </span>
            <div className="flex items-center ml-2 border border-zinc-200 rounded-md bg-white overflow-hidden shadow-2xs">
              <button
                disabled={safeCurrentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="p-1 hover:bg-zinc-50 disabled:opacity-30 disabled:hover:bg-white text-zinc-700"
                title="Previous page"
              >
                <ChevronLeft size={14} />
              </button>
              <div className="w-[1px] h-3.5 bg-zinc-200" />
              <button
                disabled={safeCurrentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="p-1 hover:bg-zinc-50 disabled:opacity-30 disabled:hover:bg-white text-zinc-700"
                title="Next page"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Actions List with Serial Numbers & Provider Icons */}
      <div className="bg-white border border-zinc-200/90 rounded-xl overflow-hidden shadow-2xs divide-y divide-zinc-100">
        {loading ? (
          <div className="p-16 text-center flex flex-col items-center justify-center gap-2">
            <div className="w-6 h-6 border-2 border-zinc-300 border-t-zinc-900 rounded-full animate-spin" />
            <span className="text-xs text-zinc-400 font-medium">
              Loading action registry...
            </span>
          </div>
        ) : filteredActions.length === 0 ? (
          <div className="p-16 text-center flex flex-col items-center justify-center gap-3">
            <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-400">
              <Layers size={18} />
            </div>
            <div className="flex flex-col gap-1 max-w-sm">
              <p className="text-xs font-semibold text-zinc-800">
                No matching actions found
              </p>
              <p className="text-[11px] text-zinc-500">
                Try adjusting your search query, selecting another category, or
                resetting filters.
              </p>
            </div>
            {hasActiveFilters && (
              <Button size="sm" variant="secondary" onClick={clearAllFilters}>
                Clear All Filters
              </Button>
            )}
          </div>
        ) : (
          paginatedActions.map((action, idx) => {
            // Compute global sequential Serial Number (1, 2, 3...)
            const serialNumber =
              pageSize === -1
                ? idx + 1
                : (safeCurrentPage - 1) * effectivePageSize + idx + 1;

            const serviceName =
              action.service || action.id.split(".")[0] || "provider";
            const providerDisplayName = action.providerName || serviceName;

            const paramProps = action.inputSchema?.properties || {};
            const paramKeys = Object.keys(paramProps).filter(
              (k) => k !== "connectionName"
            );
            const requiredFields: string[] =
              action.inputSchema?.required || [];

            return (
              <div
                key={action.id}
                className="p-4 sm:p-5 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 hover:bg-zinc-50/70 transition-colors group"
              >
                {/* Left section: Serial number, Provider icon, Action details */}
                <div className="flex items-start gap-3.5 min-w-0 flex-1">
                  {/* Clean Serial Number Column */}
                  <div className="flex flex-col items-center justify-center shrink-0 pt-0.5">
                    <span
                      className="font-mono text-[11px] font-semibold text-zinc-400 bg-zinc-100 group-hover:bg-zinc-200/80 group-hover:text-zinc-700 px-2 py-0.5 rounded-md border border-zinc-200/70 transition-colors min-w-[34px] text-center"
                      title={`Action #${serialNumber}`}
                    >
                      #{serialNumber}
                    </span>
                  </div>

                  {/* Provider icon */}
                  <div className="shrink-0 pt-0.5">
                    <ProviderIcon
                      service={serviceName}
                      displayName={providerDisplayName}
                      size="md"
                    />
                  </div>

                  {/* Action Info & Metadata */}
                  <div className="flex flex-col gap-1.5 min-w-0 flex-1">
                    {/* Header Row: Action Name, ID with copy, Category */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs sm:text-sm font-semibold text-zinc-900 group-hover:text-black">
                        {action.name}
                      </span>

                      {/* Clickable Action ID chip */}
                      <button
                        onClick={() => copyActionId(action.id)}
                        className="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-600 bg-zinc-100/90 hover:bg-zinc-200/90 px-1.5 py-0.5 rounded-md border border-zinc-200/60 transition-colors cursor-pointer"
                        title="Click to copy Action ID"
                      >
                        <span>{action.id}</span>
                        {copiedId === action.id ? (
                          <Check size={10} className="text-emerald-600" />
                        ) : (
                          <Copy size={10} className="text-zinc-400" />
                        )}
                      </button>

                      {/* Provider pill */}
                      <span className="text-[10px] font-medium text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200/50 uppercase tracking-wider">
                        {providerDisplayName}
                      </span>

                      {/* Category Badge */}
                      {action.category && (
                        <Badge variant="neutral">{action.category}</Badge>
                      )}
                    </div>

                    {/* Description */}
                    <p className="text-xs text-zinc-600 leading-relaxed pr-2">
                      {action.description}
                    </p>

                    {/* Parameters & Scopes Footer */}
                    <div className="flex items-center gap-2 flex-wrap pt-1 text-[11px]">
                      {/* Parameter Badges */}
                      {paramKeys.length > 0 ? (
                        <div className="flex items-center gap-1 flex-wrap text-zinc-500">
                          <span className="text-zinc-400">Parameters:</span>
                          {paramKeys.slice(0, 4).map((pk) => {
                            const isReq = requiredFields.includes(pk);
                            return (
                              <span
                                key={pk}
                                className={`font-mono px-1.5 py-0.2 rounded text-[10px] ${
                                  isReq
                                    ? "bg-amber-50 text-amber-800 border border-amber-200 font-semibold"
                                    : "bg-zinc-100 text-zinc-600"
                                }`}
                              >
                                {pk}
                                {isReq && "*"}
                              </span>
                            );
                          })}
                          {paramKeys.length > 4 && (
                            <span className="text-zinc-400 text-[10px]">
                              +{paramKeys.length - 4} more
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-zinc-400 text-[10px]">
                          No required parameters
                        </span>
                      )}

                      {/* Required OAuth Scopes */}
                      {action.requiredScopes &&
                        action.requiredScopes.length > 0 && (
                          <span className="text-[10px] text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded border border-zinc-200/60 font-mono">
                            Scope: {action.requiredScopes.join(", ")}
                          </span>
                        )}
                    </div>
                  </div>
                </div>

                {/* Right Action Trigger */}
                <div className="flex items-center gap-2 shrink-0 self-end lg:self-center pl-10 lg:pl-0">
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => setRunningAction(action)}
                    className="shadow-2xs"
                  >
                    <Play size={11} className="fill-current mr-1" />
                    <span>Run Action</span>
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Pagination Controls */}
      {totalPages > 1 && pageSize !== -1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 py-2 px-1">
          <div className="text-xs text-zinc-500">
            Showing{" "}
            <span className="font-semibold text-zinc-800">
              {startIndexNumber}–{endIndexNumber}
            </span>{" "}
            of{" "}
            <span className="font-semibold text-zinc-800">{totalItems}</span>{" "}
            actions
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="secondary"
              disabled={safeCurrentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={13} className="mr-0.5" />
              Previous
            </Button>

            {/* Page number buttons */}
            <div className="flex items-center gap-1 px-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum = i + 1;
                if (totalPages > 5) {
                  if (safeCurrentPage <= 3) {
                    pageNum = i + 1;
                  } else if (safeCurrentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = safeCurrentPage - 2 + i;
                  }
                }

                const isActive = pageNum === safeCurrentPage;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`w-7 h-7 text-xs font-medium rounded-md transition-colors ${
                      isActive
                        ? "bg-zinc-900 text-white font-semibold shadow-xs"
                        : "text-zinc-600 hover:bg-zinc-200/80"
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <Button
              size="sm"
              variant="secondary"
              disabled={safeCurrentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
              <ChevronRight size={13} className="ml-0.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Interactive Action Runner Playground Modal */}
      <ActionRunnerModal
        isOpen={Boolean(runningAction)}
        onClose={() => setRunningAction(null)}
        action={runningAction}
      />
    </div>
  );
}

export default function ActionsPage() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Action Registry"
          description="Explore callable tool contracts, inspect schemas, and test execution."
        />

        <main className="flex-1 overflow-y-auto min-h-0">
          <Suspense
            fallback={
              <div className="p-16 text-center text-xs text-zinc-400">
                Loading actions...
              </div>
            }
          >
            <ActionsContent />
          </Suspense>
        </main>
      </div>
    </div>
  );
}

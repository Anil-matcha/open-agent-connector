"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CustomSelect } from "@/components/ui/CustomSelect";
import { Modal } from "@/components/ui/Modal";
import { fetchApi } from "@/lib/api";
import { CheckCircle2, AlertCircle, RefreshCw, Eye } from "lucide-react";

interface RunItem {
  id: string;
  actionId: string;
  service: string;
  caller: string;
  ok: boolean;
  statusCode: number;
  durationMs: number;
  inputSummary?: string;
  outputSummary?: string;
  errorMessage?: string;
  startedAt: string;
}

export default function LogsPage() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [inspectRun, setInspectRun] = useState<RunItem | null>(null);

  async function loadRuns() {
    setLoading(true);
    try {
      const okParam = statusFilter === "ok" ? "&ok=true" : statusFilter === "failed" ? "&ok=false" : "";
      const res = await fetchApi<{ data: RunItem[] }>(`/api/runs?limit=50${okParam}`);
      setRuns(res.data);
    } catch (err) {
      console.error("Failed to load runs", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
  }, [statusFilter]);

  const filterOptions = [
    { value: "all", label: "All Executions" },
    { value: "ok", label: "Successful (200 OK)" },
    { value: "failed", label: "Failed / Errored" },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50">
      <Sidebar />

      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        <Header
          title="Run Audit Logs"
          description="Chronological record of all action invocations, latencies, and payloads."
        />

        <main className="flex-1 overflow-y-auto min-h-0">
          <div className="p-6 flex flex-col gap-6 max-w-6xl">
          {/* Controls Bar with CustomSelect */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 border border-zinc-200 rounded-lg">
            <div className="w-full sm:w-56">
              <CustomSelect
                options={filterOptions}
                value={statusFilter}
                onChange={setStatusFilter}
              />
            </div>

            <Button size="sm" variant="outline" onClick={loadRuns} loading={loading}>
              <RefreshCw size={11} />
              <span>Refresh Logs</span>
            </Button>
          </div>

          {/* Table */}
          <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden flex flex-col">
            {runs.length === 0 ? (
              <div className="p-12 text-center text-xs text-zinc-400">
                No execution logs found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-50 border-b border-zinc-100 text-zinc-500 font-medium">
                    <tr>
                      <th className="px-4 py-2">Status</th>
                      <th className="px-4 py-2">Action ID</th>
                      <th className="px-4 py-2">Caller</th>
                      <th className="px-4 py-2">Duration</th>
                      <th className="px-4 py-2">Timestamp</th>
                      <th className="px-4 py-2 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {runs.map((r) => (
                      <tr key={r.id} className="hover:bg-zinc-50/50">
                        <td className="px-4 py-2.5">
                          {r.ok ? (
                            <span className="flex items-center gap-1.5 text-emerald-700 font-medium">
                              <CheckCircle2 size={13} className="text-emerald-500" />
                              200 OK
                            </span>
                          ) : (
                            <span className="flex items-center gap-1.5 text-rose-700 font-medium">
                              <AlertCircle size={13} className="text-rose-500" />
                              {r.statusCode} Error
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-zinc-800">
                          {r.actionId}
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge variant="neutral">{r.caller}</Badge>
                        </td>
                        <td className="px-4 py-2.5 text-zinc-500 font-mono">
                          {r.durationMs}ms
                        </td>
                        <td className="px-4 py-2.5 text-zinc-400 text-[11px]">
                          {new Date(r.startedAt).toLocaleTimeString()}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setInspectRun(r)}
                          >
                            <Eye size={12} />
                            <span>Inspect</span>
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

        {/* Inspection Modal */}
        {inspectRun && (
          <Modal
            isOpen={Boolean(inspectRun)}
            onClose={() => setInspectRun(null)}
            title="Execution Details"
            description={`Execution ID: ${inspectRun.id}`}
            maxWidth="lg"
          >
            <div className="flex flex-col gap-4 text-xs">
              <div className="grid grid-cols-2 gap-2 p-2.5 bg-zinc-50 border border-zinc-200 rounded-md">
                <div>
                  <span className="text-zinc-400">Action:</span>{" "}
                  <code className="text-zinc-800">{inspectRun.actionId}</code>
                </div>
                <div>
                  <span className="text-zinc-400">Duration:</span>{" "}
                  <span className="text-zinc-800">{inspectRun.durationMs}ms</span>
                </div>
                <div>
                  <span className="text-zinc-400">Caller:</span>{" "}
                  <span className="text-zinc-800">{inspectRun.caller}</span>
                </div>
                <div>
                  <span className="text-zinc-400">Started:</span>{" "}
                  <span className="text-zinc-800">{inspectRun.startedAt}</span>
                </div>
              </div>

              {inspectRun.errorMessage && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-md text-rose-800">
                  <span className="font-semibold block mb-0.5">Error Message</span>
                  <p className="font-mono text-[11px]">{inspectRun.errorMessage}</p>
                </div>
              )}

              <div>
                <span className="font-medium text-zinc-700 block mb-1">
                  Request Input
                </span>
                <pre className="p-2.5 bg-zinc-50 border border-zinc-200 rounded text-[11px] font-mono text-zinc-800 overflow-x-auto max-h-40">
                  {inspectRun.inputSummary || "{}"}
                </pre>
              </div>

              <div>
                <span className="font-medium text-zinc-700 block mb-1">
                  Response Output
                </span>
                <pre className="p-2.5 bg-zinc-50 border border-zinc-200 rounded text-[11px] font-mono text-zinc-800 overflow-x-auto max-h-48">
                  {inspectRun.outputSummary || "{}"}
                </pre>
              </div>
            </div>
          </Modal>
        )}
        </main>
      </div>
    </div>
  );
}

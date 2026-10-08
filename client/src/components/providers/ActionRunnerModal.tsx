"use client";

import React, { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { CustomSelect } from "@/components/ui/CustomSelect";
import { Badge } from "@/components/ui/Badge";
import { ProviderIcon } from "@/components/ui/ProviderIcon";
import { fetchApi } from "@/lib/api";
import { CheckCircle2, AlertCircle, Clock, KeyRound, Copy, Check, ArrowRight } from "lucide-react";
import Link from "next/link";

interface ConnectionItem {
  id: string;
  service: string;
  connectionName: string;
  authType: string;
  accountId?: string;
  displayName?: string;
  updatedAt: string;
}

interface ActionRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
  action: {
    id: string;
    name: string;
    description: string;
    service?: string;
    inputSchema: any;
    outputSchema?: any;
    requiredScopes?: string[];
  } | null;
}

export function ActionRunnerModal({
  isOpen,
  onClose,
  action,
}: ActionRunnerModalProps) {
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [connectionName, setConnectionName] = useState("default");
  const [customAliasMode, setCustomAliasMode] = useState(false);
  const [inputs, setInputs] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [fetchingConnections, setFetchingConnections] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const service = action ? (action.service || action.id.split(".")[0]) : "";

  // Reset inputs when action changes
  useEffect(() => {
    if (action) {
      const defaultInputs: Record<string, any> = {};
      const props = action.inputSchema?.properties || {};
      Object.entries(props).forEach(([k, v]: [string, any]) => {
        if (v.default !== undefined) {
          defaultInputs[k] = v.default;
        }
      });
      setInputs(defaultInputs);
      setResult(null);
      setError(null);
    }
  }, [action]);

  // Load connections for the service
  useEffect(() => {
    if (!isOpen || !service) {
      setConnections([]);
      return;
    }

    async function loadServiceConnections() {
      setFetchingConnections(true);
      try {
        const res = await fetchApi<{ data: ConnectionItem[] }>(
          `/api/connections?service=${service}`
        );
        const conns = res.data || [];
        setConnections(conns);
        if (conns.length > 0) {
          setConnectionName(conns[0].connectionName);
          setCustomAliasMode(false);
        } else {
          setConnectionName("default");
          setCustomAliasMode(true);
        }
      } catch (err) {
        console.error("Failed to load connections for service", err);
        setConnections([]);
      } finally {
        setFetchingConnections(false);
      }
    }

    loadServiceConnections();
  }, [isOpen, service]);

  if (!action) return null;

  const schemaProperties = action.inputSchema?.properties || {};
  const requiredFields = action.inputSchema?.required || [];

  const connectionOptions = connections.map((c) => ({
    value: c.connectionName,
    label: `${c.connectionName} (${c.displayName || c.accountId || c.authType})`,
    description: `Configured on ${new Date(c.updatedAt).toLocaleDateString()}`,
  }));

  function handleInputChange(key: string, value: any, type: string) {
    if (type === "integer" || type === "number") {
      setInputs((prev) => ({ ...prev, [key]: value !== "" ? Number(value) : undefined }));
    } else if (type === "boolean") {
      setInputs((prev) => ({ ...prev, [key]: value === "true" || value === true }));
    } else {
      setInputs((prev) => ({ ...prev, [key]: value }));
    }
  }

  async function handleExecute(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const cleanedInput: Record<string, any> = {};
      Object.entries(inputs).forEach(([k, v]) => {
        if (v !== undefined && v !== "") cleanedInput[k] = v;
      });

      const res = await fetchApi(`/v1/actions/${action?.id}`, {
        method: "POST",
        body: JSON.stringify({
          input: cleanedInput,
          connectionName: connectionName.trim() || "default",
        }),
      });

      setResult(res);
    } catch (err: any) {
      setError(err.message || "Action execution failed.");
    } finally {
      setLoading(false);
    }
  }

  function copyResultJson() {
    if (!result?.data) return;
    navigator.clipboard.writeText(JSON.stringify(result.data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <ProviderIcon service={service} size="sm" />
          <span>Run {action.name}</span>
        </div>
      }
      description={action.description}
      maxWidth="lg"
    >
      <form onSubmit={handleExecute} className="flex flex-col gap-4">
        {/* Connection Selector */}
        {connections.length > 0 && !customAliasMode ? (
          <div className="flex flex-col gap-1.5">
            <CustomSelect
              label="Connected Account"
              options={connectionOptions}
              value={connectionName}
              onChange={setConnectionName}
            />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setCustomAliasMode(true)}
                className="text-[11px] text-zinc-500 hover:text-zinc-800 underline"
              >
                Use custom alias
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2 p-3 bg-zinc-50 border border-zinc-200 rounded-md">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-800">
                <KeyRound size={14} className="text-zinc-500" />
                <span>Account Connection</span>
              </div>
              {connections.length > 0 && (
                <button
                  type="button"
                  onClick={() => setCustomAliasMode(false)}
                  className="text-[11px] text-zinc-500 hover:text-zinc-800 underline"
                >
                  Choose existing ({connections.length})
                </button>
              )}
            </div>

            {connections.length === 0 && !fetchingConnections && (
              <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 p-2 rounded">
                No active connection saved for <strong>{service}</strong>. Please connect your credentials in the{" "}
                <Link href="/providers" className="underline font-semibold" onClick={onClose}>
                  Providers
                </Link>{" "}
                tab, or ensure the alias below exists.
              </p>
            )}

            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-medium text-zinc-600">
                Connection Alias
              </label>
              <input
                type="text"
                value={connectionName}
                onChange={(e) => setConnectionName(e.target.value)}
                placeholder="default"
                className="h-8 px-2.5 text-xs bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900"
              />
            </div>
          </div>
        )}

        {/* Dynamic Inputs from JSON Schema */}
        {Object.keys(schemaProperties).length > 0 ? (
          <div className="flex flex-col gap-3 p-3 bg-zinc-50 border border-zinc-200 rounded-md">
            <span className="text-xs font-semibold text-zinc-700">Input Parameters</span>
            {Object.entries(schemaProperties).map(([key, prop]: [string, any]) => {
              const isRequired = requiredFields.includes(key);
              const isMultiline =
                key.toLowerCase().includes("body") ||
                key.toLowerCase().includes("content") ||
                key.toLowerCase().includes("description") ||
                (prop.description && prop.description.toLowerCase().includes("markdown"));
              const hasEnum = Array.isArray(prop.enum);

              return (
                <div key={key} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-zinc-700">
                      <code>{key}</code>
                      {isRequired && <span className="text-rose-500 ml-0.5">*</span>}
                    </label>
                    <span className="text-[10px] text-zinc-400 font-mono">
                      {prop.type || (hasEnum ? "enum" : "string")}
                    </span>
                  </div>
                  {prop.description && (
                    <p className="text-[11px] text-zinc-500">{prop.description}</p>
                  )}

                  {hasEnum ? (
                    <CustomSelect
                      options={prop.enum.map((opt: string) => ({ value: opt, label: opt }))}
                      value={inputs[key] ?? prop.default ?? prop.enum[0]}
                      onChange={(val) => handleInputChange(key, val, "string")}
                    />
                  ) : isMultiline ? (
                    <textarea
                      rows={3}
                      value={inputs[key] ?? ""}
                      onChange={(e) => handleInputChange(key, e.target.value, "string")}
                      placeholder={prop.default ? `Default: ${prop.default}` : ""}
                      required={isRequired}
                      className="p-2.5 text-xs bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 font-mono"
                    />
                  ) : (
                    <input
                      type={prop.type === "integer" || prop.type === "number" ? "number" : "text"}
                      value={inputs[key] ?? ""}
                      onChange={(e) => handleInputChange(key, e.target.value, prop.type)}
                      placeholder={prop.default !== undefined ? `Default: ${prop.default}` : ""}
                      required={isRequired}
                      className="h-8 px-2.5 text-xs bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 font-mono"
                    />
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-md text-xs text-zinc-500">
            This action requires no input arguments.
          </div>
        )}

        {/* Submit Bar */}
        <div className="flex items-center justify-between pt-1 border-t border-zinc-100">
          <div className="text-[11px] text-zinc-400">
            Action: <code className="text-zinc-600">{action.id}</code>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
              Close
            </Button>
            <Button type="submit" variant="primary" loading={loading}>
              {loading ? "Executing..." : "Execute Action"}
            </Button>
          </div>
        </div>

        {/* Error Output */}
        {error && (
          <div className="p-3 text-xs bg-rose-50 border border-rose-200 rounded-md text-rose-800 flex items-start gap-2">
            <AlertCircle size={14} className="text-rose-500 mt-0.5 shrink-0" />
            <div className="flex-1">
              <div className="font-semibold">Execution Failed</div>
              <div className="mt-0.5 font-mono text-[11px] break-all">{error}</div>
            </div>
          </div>
        )}

        {/* Result Output */}
        {result && (
          <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-md flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 font-medium text-emerald-700">
                <CheckCircle2 size={13} className="text-emerald-500" />
                Execution Success
              </span>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-[11px] text-zinc-500">
                  <Clock size={11} />
                  {result.meta?.durationMs ?? 0}ms
                  {result.meta?.replayed && " (cached replay)"}
                </span>
                <button
                  type="button"
                  onClick={copyResultJson}
                  className="flex items-center gap-1 text-[11px] text-zinc-600 hover:text-black"
                >
                  {copied ? <Check size={11} className="text-emerald-600" /> : <Copy size={11} />}
                  <span>{copied ? "Copied" : "Copy JSON"}</span>
                </button>
                <Link
                  href="/logs"
                  className="flex items-center gap-1 text-[11px] text-zinc-600 hover:text-black underline"
                  onClick={onClose}
                >
                  <span>Audit Logs</span>
                  <ArrowRight size={10} />
                </Link>
              </div>
            </div>
            <pre className="p-2.5 bg-white border border-zinc-200 rounded text-[11px] font-mono text-zinc-800 overflow-x-auto max-h-56">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          </div>
        )}
      </form>
    </Modal>
  );
}

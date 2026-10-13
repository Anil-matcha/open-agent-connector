"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { CustomSelect } from "@/components/ui/CustomSelect";
import { fetchApi } from "@/lib/api";
import Link from "next/link";
import {
  ExternalLink,
  ShieldCheck,
  KeyRound,
  AlertCircle,
  Play,
  ArrowRight,
  Sparkles,
  Copy,
  Check,
  Globe,
} from "lucide-react";

interface SetupGuide {
  title?: string;
  docs_url?: string;
  docs_label?: string;
  instructions?: string | string[];
  scopes?: string[];
}

interface AuthConfigField {
  key: string;
  label: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
  description?: string;
}

interface AuthConfigItem {
  type: string;
  label?: string;
  placeholder?: string;
  description?: string;
  docs_url?: string;
  docs_label?: string;
  setup_guide?: SetupGuide;
  fields?: AuthConfigField[];
}

interface ConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  service: string;
  displayName: string;
  authTypes: string[];
  authConfigs?: AuthConfigItem[];
  onSuccess: () => void;
}

interface OAuthMeta {
  configured: boolean;
  hostedAvailable: boolean;
  customConfigured: boolean;
  activeMode: "hosted" | "custom" | null;
  callbackUrl?: string;
  hostedDomain?: string;
}

export function ConnectModal({
  isOpen,
  onClose,
  service,
  displayName,
  authTypes,
  authConfigs = [],
  onSuccess,
}: ConnectModalProps) {
  const hasOAuth2 = authTypes.includes("oauth2");
  const hasManualAuth = authTypes.some((t) => t !== "oauth2");

  const [authMode, setAuthMode] = useState<"oauth" | "manual">(
    hasOAuth2 ? "oauth" : "manual"
  );
  const [authType, setAuthType] = useState<string>(
    hasOAuth2 ? "oauth2" : authTypes[0] || "api_key"
  );
  const [connectionName, setConnectionName] = useState("default");
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthStatus, setOauthStatus] = useState<OAuthMeta | null>(null);
  const [oauthTab, setOauthTab] = useState<"hosted" | "custom">("hosted");
  const [customClientId, setCustomClientId] = useState("");
  const [customClientSecret, setCustomClientSecret] = useState("");
  const [customSaving, setCustomSaving] = useState(false);
  const [copiedCallback, setCopiedCallback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (authTypes.includes("oauth2")) {
      setAuthMode("oauth");
      setAuthType("oauth2");
    } else {
      setAuthMode("manual");
      setAuthType(authTypes[0] || "api_key");
    }
    setOauthTab("hosted");
    setConnectionName("default");
    setFormValues({});
    setError(null);
  }, [service, isOpen, authTypes]);

  React.useEffect(() => {
    if (authTypes.includes("oauth2")) {
      fetchApi<OAuthMeta>(`/api/oauth/${service}/config`)
        .then((res) => {
          setOauthStatus(res);
          if (res.customConfigured && !res.hostedAvailable) {
            setOauthTab("custom");
          }
        })
        .catch(() => {});
    }
  }, [service, authTypes]);

  async function handleOAuthLaunch(mode: "hosted" | "custom" = "hosted") {
    setOauthLoading(true);
    setError(null);
    try {
      const returnUri =
        typeof window !== "undefined"
          ? `${window.location.origin}/connections`
          : "";
      const res = await fetchApi<{ data: { authorization_url: string } }>(
        `/api/oauth/${service}/authorize?connectionName=${encodeURIComponent(
          connectionName.trim() || "default"
        )}&redirectUri=${encodeURIComponent(returnUri)}&mode=${mode}`
      );
      if (res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
      } else {
        throw new Error("Authorization URL could not be generated.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to start OAuth flow.");
      setOauthLoading(false);
    }
  }

  async function handleSaveCustomOAuth(e: React.FormEvent) {
    e.preventDefault();
    if (!customClientId.trim() || !customClientSecret.trim()) {
      setError("Please enter both Client ID and Client Secret.");
      return;
    }
    setCustomSaving(true);
    setError(null);
    try {
      await fetchApi(`/api/oauth/${service}/config?mode=custom`, {
        method: "POST",
        body: JSON.stringify({
          clientId: customClientId.trim(),
          clientSecret: customClientSecret.trim(),
          mode: "custom",
        }),
      });
      await handleOAuthLaunch("custom");
    } catch (err: any) {
      setError(err.message || "Failed to save custom OAuth credentials.");
      setCustomSaving(false);
    }
  }

  function handleCopyCallback() {
    const url =
      oauthStatus?.callbackUrl ||
      `https://connector.suparagent.ai/api/oauth/${service}/callback`;
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(url);
      setCopiedCallback(true);
      setTimeout(() => setCopiedCallback(false), 2000);
    }
  }

  // Active config for manual mode
  const activeConfig = authConfigs.find((c) => c.type === authType);

  const manualAuthOptions = authTypes
    .filter((type) => type !== "oauth2")
    .map((type) => {
      const config = authConfigs.find((c) => c.type === type);
      return {
        value: type,
        label:
          config?.label ||
          (type === "api_key"
            ? "API Key / Personal Access Token"
            : type === "no_auth"
            ? "No Authentication Required"
            : type),
      };
    });

  async function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const activeFields = activeConfig?.fields;
      const values: Record<string, string> = { ...formValues };

      if (authType !== "no_auth") {
        if (activeFields && activeFields.length > 0) {
          for (const f of activeFields) {
            if (
              f.required !== false &&
              (!values[f.key] || !values[f.key].trim())
            ) {
              throw new Error(`Please enter ${f.label}.`);
            }
          }
        } else {
          const singleVal = values["apiKey"] || values["accessToken"] || "";
          if (!singleVal.trim()) {
            throw new Error("Please enter your token or API key.");
          }
        }
      }

      // Ensure backward-compatible aliases for single-field consumers
      if (values.apiKey && !values.accessToken) {
        values.accessToken = values.apiKey;
      }
      if (values.accessToken && !values.apiKey) {
        values.apiKey = values.accessToken;
      }

      await fetchApi(`/api/connections/${service}`, {
        method: "PUT",
        body: JSON.stringify({
          authType,
          connectionName: connectionName.trim() || "default",
          values,
        }),
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to connect provider.");
    } finally {
      setLoading(false);
    }
  }

  const guide = activeConfig?.setup_guide;
  const docsUrl = guide?.docs_url || activeConfig?.docs_url;
  const docsLabel =
    guide?.docs_label ||
    activeConfig?.docs_label ||
    `${displayName} Documentation`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Connect ${displayName}`}
      description="Credentials are validated with the provider in real-time, encrypted with AES-256, and stored locally."
      maxWidth="md"
    >
      <div className="flex flex-col gap-4">
        {error && (
          <div className="p-3 text-xs text-rose-800 bg-rose-50 border border-rose-200 rounded-md flex items-start gap-2">
            <AlertCircle size={14} className="text-rose-600 mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold">Validation Failed</div>
              <div className="mt-0.5">{error}</div>
            </div>
          </div>
        )}

        {/* Top-Level Mode Selector (if provider supports BOTH OAuth AND Manual Credentials) */}
        {hasOAuth2 && hasManualAuth && (
          <div className="grid grid-cols-2 gap-1 p-1 bg-zinc-100/90 border border-zinc-200/70 rounded-lg">
            <button
              type="button"
              onClick={() => {
                setAuthMode("oauth");
                setAuthType("oauth2");
                setError(null);
              }}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                authMode === "oauth"
                  ? "bg-white text-zinc-900 shadow-xs"
                  : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/50"
              }`}
            >
              <Sparkles
                size={13}
                className={authMode === "oauth" ? "text-amber-500" : "text-zinc-400"}
              />
              <span>1-Click OAuth (Recommended)</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthMode("manual");
                const fallback =
                  authTypes.find((t) => t !== "oauth2") || "api_key";
                setAuthType(fallback);
                setError(null);
              }}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                authMode === "manual"
                  ? "bg-white text-zinc-900 shadow-xs"
                  : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/50"
              }`}
            >
              <KeyRound
                size={13}
                className={authMode === "manual" ? "text-zinc-900" : "text-zinc-400"}
              />
              <span>Personal Token / API Key</span>
            </button>
          </div>
        )}

        {/* -------------------- OAUTH 2.0 FLOW -------------------- */}
        {authMode === "oauth" && hasOAuth2 && (
          <div className="flex flex-col gap-3.5">
            {/* Sub-selector: Hosted 1-Click vs Custom App (BYOC) */}
            <div className="flex items-center justify-between pb-1 border-b border-zinc-100">
              <div className="flex items-center gap-1 bg-zinc-100/80 p-0.5 rounded-md">
                <button
                  type="button"
                  onClick={() => setOauthTab("hosted")}
                  className={`px-2.5 py-1 rounded text-xs transition-all cursor-pointer ${
                    oauthTab === "hosted"
                      ? "bg-white text-zinc-900 font-semibold shadow-2xs"
                      : "text-zinc-600 hover:text-zinc-900"
                  }`}
                >
                  Hosted 1-Click
                </button>
                <button
                  type="button"
                  onClick={() => setOauthTab("custom")}
                  className={`px-2.5 py-1 rounded text-xs transition-all cursor-pointer ${
                    oauthTab === "custom"
                      ? "bg-white text-zinc-900 font-semibold shadow-2xs"
                      : "text-zinc-600 hover:text-zinc-900"
                  }`}
                >
                  Custom App (BYOC)
                </button>
              </div>

              <span className="text-[11px] text-zinc-400 font-mono hidden sm:inline-flex items-center gap-1">
                <Globe size={11} className="text-zinc-400" />
                connector.suparagent.ai
              </span>
            </div>

            {/* Connection Alias */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-zinc-700">Connection Alias</label>
              <input
                type="text"
                value={connectionName}
                onChange={(e) => setConnectionName(e.target.value)}
                placeholder="e.g. default, work, personal"
                required
                className="h-9 px-3 text-xs bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
              />
              <p className="text-[11px] text-zinc-400">
                A unique alias for this connection (defaults to <code>default</code>).
              </p>
            </div>

            {/* Tab 1: Hosted 1-Click */}
            {oauthTab === "hosted" && (
              <div className="p-4 bg-gradient-to-b from-zinc-50 to-white border border-zinc-200 rounded-lg flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-semibold text-zinc-900 flex items-center gap-1.5">
                    <Sparkles size={13} className="text-amber-500" />
                    Connect via SuparAgent Managed App
                  </span>
                  <p className="text-[11px] text-zinc-500 leading-relaxed">
                    Zero developer setup required. Connect your account securely via our verified multi-tenant app on <span className="font-mono text-zinc-700">connector.suparagent.ai</span>.
                  </p>
                </div>

                <Button
                  type="button"
                  variant="primary"
                  size="md"
                  loading={oauthLoading}
                  onClick={() => handleOAuthLaunch("hosted")}
                  className="w-full bg-zinc-900 hover:bg-black text-white text-xs font-semibold py-2.5 flex items-center justify-center gap-2 shadow-xs cursor-pointer mt-1"
                >
                  <Sparkles size={13} className="text-amber-300" />
                  <span>Connect with {displayName} (1-Click)</span>
                </Button>
              </div>
            )}

            {/* Tab 2: Custom App (BYOC) */}
            {oauthTab === "custom" && (
              <div className="p-3.5 bg-zinc-50/70 border border-zinc-200 rounded-lg flex flex-col gap-3">
                <p className="text-[11px] text-zinc-500 leading-relaxed">
                  Use your own developer credentials from {displayName} Developer Console for organizational isolation.
                </p>

                {/* Redirect URI with Copy */}
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
                    Authorized Redirect URI
                  </label>
                  <div className="flex items-center gap-1 bg-white border border-zinc-200 rounded-md p-1.5">
                    <input
                      type="text"
                      readOnly
                      value={
                        oauthStatus?.callbackUrl ||
                        `https://connector.suparagent.ai/api/oauth/${service}/callback`
                      }
                      className="bg-transparent text-[11px] font-mono text-zinc-700 flex-1 px-1 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleCopyCallback}
                      className="px-2 py-1 text-[10px] font-medium text-zinc-600 hover:text-zinc-900 bg-zinc-100 hover:bg-zinc-200 rounded flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      {copiedCallback ? (
                        <>
                          <Check size={11} className="text-emerald-600" />
                          <span className="text-emerald-700 font-semibold">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={11} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Client ID & Secret Inputs */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium text-zinc-700">Client ID</label>
                    <input
                      type="text"
                      value={customClientId}
                      onChange={(e) => setCustomClientId(e.target.value)}
                      placeholder="Enter Client ID..."
                      className="h-8 px-2.5 text-xs font-mono bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-medium text-zinc-700">Client Secret</label>
                    <input
                      type="password"
                      value={customClientSecret}
                      onChange={(e) => setCustomClientSecret(e.target.value)}
                      placeholder="Enter Client Secret..."
                      className="h-8 px-2.5 text-xs font-mono bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    loading={customSaving || oauthLoading}
                    onClick={handleSaveCustomOAuth}
                    className="text-xs font-medium cursor-pointer"
                  >
                    Save & Connect Custom OAuth
                  </Button>
                </div>
              </div>
            )}

            {/* Footer for OAuth */}
            <div className="flex items-center justify-between gap-2 pt-3 border-t border-zinc-100">
              <Link
                href={`/actions?service=${service}`}
                onClick={onClose}
                className="text-xs text-zinc-500 hover:text-zinc-900 flex items-center gap-1.5 font-medium transition-colors"
              >
                <Play size={11} className="text-zinc-400" />
                <span>Browse {displayName} Actions</span>
                <ArrowRight size={11} className="text-zinc-400" />
              </Link>
              <Button type="button" variant="ghost" onClick={onClose}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* -------------------- MANUAL TOKEN / API KEY FLOW -------------------- */}
        {(authMode === "manual" || !hasOAuth2) && (
          <form onSubmit={handleManualSubmit} className="flex flex-col gap-4">
            {/* Manual Auth Type Selector (if multiple manual types exist, e.g. PAT vs Basic) */}
            {manualAuthOptions.length > 1 && (
              <CustomSelect
                label="Authentication Method"
                options={manualAuthOptions}
                value={authType}
                onChange={setAuthType}
              />
            )}

            {/* Connection Alias */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-zinc-700">Connection Alias</label>
              <input
                type="text"
                value={connectionName}
                onChange={(e) => setConnectionName(e.target.value)}
                placeholder="e.g. default, work, personal"
                required
                className="h-9 px-3 text-xs bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
              />
              <p className="text-[11px] text-zinc-400">
                A unique alias for this connection (defaults to <code>default</code>).
              </p>
            </div>

            {/* Setup Guidance */}
            {(guide || docsUrl) && (
              <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-md text-xs text-zinc-600 flex flex-col gap-2">
                <div className="flex items-center justify-between font-semibold text-zinc-800">
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck size={13} className="text-emerald-600" />
                    {guide?.title || `${displayName} Token Setup Guide`}
                  </span>
                  {docsUrl && (
                    <a
                      href={docsUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[11px] text-zinc-900 hover:text-black font-medium flex items-center gap-1 underline"
                    >
                      {docsLabel}
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>

                {guide?.instructions && (
                  <div className="text-[11px] text-zinc-600 flex flex-col gap-1">
                    {Array.isArray(guide.instructions) ? (
                      guide.instructions.map((step, idx) => (
                        <p key={idx}>{step}</p>
                      ))
                    ) : (
                      <p>{guide.instructions}</p>
                    )}
                  </div>
                )}

                {guide?.scopes && guide.scopes.length > 0 && (
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
                      Recommended Scopes / Permissions:
                    </span>
                    <div className="bg-white px-2 py-1.5 rounded border border-zinc-200 font-mono text-[10px] text-zinc-700 flex flex-wrap gap-1">
                      {guide.scopes.map((scope) => (
                        <span key={scope} className="bg-zinc-100 px-1 py-0.5 rounded">
                          {scope}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Credential Input(s) */}
            {authType !== "no_auth" && (
              <>
                {activeConfig?.fields && activeConfig.fields.length > 0 ? (
                  activeConfig.fields.map((field) => (
                    <div key={field.key} className="flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-medium text-zinc-700">
                          {field.label}
                          {field.required !== false && (
                            <span className="text-rose-500 ml-0.5">*</span>
                          )}
                        </label>
                      </div>
                      <input
                        type={field.type === "password" ? "password" : "text"}
                        value={formValues[field.key] || ""}
                        onChange={(e) =>
                          setFormValues((prev) => ({
                            ...prev,
                            [field.key]: e.target.value,
                          }))
                        }
                        placeholder={field.placeholder || `Enter ${field.label}...`}
                        required={field.required !== false}
                        className="h-9 px-3 text-xs font-mono bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
                      />
                      {field.description && (
                        <p className="text-[11px] text-zinc-400">{field.description}</p>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-medium text-zinc-700">
                      {activeConfig?.label || "API Key or Access Token"}
                    </label>
                    <input
                      type="password"
                      value={formValues["apiKey"] || ""}
                      onChange={(e) =>
                        setFormValues((prev) => ({
                          ...prev,
                          apiKey: e.target.value,
                          accessToken: e.target.value,
                        }))
                      }
                      placeholder={
                        activeConfig?.placeholder || "Enter secret key or token..."
                      }
                      required
                      className="h-9 px-3 text-xs font-mono bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
                    />
                    {activeConfig?.description && (
                      <p className="text-[11px] text-zinc-400">{activeConfig.description}</p>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Footer for Manual Form */}
            <div className="flex items-center justify-between gap-2 pt-3 border-t border-zinc-100">
              <Link
                href={`/actions?service=${service}`}
                onClick={onClose}
                className="text-xs text-zinc-500 hover:text-zinc-900 flex items-center gap-1.5 font-medium transition-colors"
              >
                <Play size={11} className="text-zinc-400" />
                <span>Browse {displayName} Actions</span>
                <ArrowRight size={11} className="text-zinc-400" />
              </Link>

              <div className="flex items-center gap-2">
                <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" loading={loading}>
                  {loading ? "Validating & Saving..." : "Validate & Connect"}
                </Button>
              </div>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
}

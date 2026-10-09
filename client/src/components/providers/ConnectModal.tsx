"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { CustomSelect } from "@/components/ui/CustomSelect";
import { fetchApi } from "@/lib/api";
import { ExternalLink, ShieldCheck, KeyRound, AlertCircle } from "lucide-react";

interface SetupGuide {
  title?: string;
  docs_url?: string;
  docs_label?: string;
  instructions?: string | string[];
  scopes?: string[];
}

interface AuthConfigItem {
  type: string;
  label?: string;
  placeholder?: string;
  description?: string;
  docs_url?: string;
  docs_label?: string;
  setup_guide?: SetupGuide;
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

export function ConnectModal({
  isOpen,
  onClose,
  service,
  displayName,
  authTypes,
  authConfigs = [],
  onSuccess,
}: ConnectModalProps) {
  const [authType, setAuthType] = useState(authTypes[0] || "api_key");
  const [connectionName, setConnectionName] = useState("default");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthConfigured, setOauthConfigured] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (authTypes.includes("oauth2")) {
      fetchApi<{ configured: boolean }>(`/api/oauth/${service}/config`)
        .then((res) => {
          if (res.configured) setOauthConfigured(true);
        })
        .catch(() => {});
    }
  }, [service, authTypes]);

  async function handleOAuthLaunch() {
    setOauthLoading(true);
    setError(null);
    try {
      const returnUri = typeof window !== "undefined" ? `${window.location.origin}/connections` : "";
      const res = await fetchApi<{ data: { authorization_url: string } }>(
        `/api/oauth/${service}/authorize?connectionName=${encodeURIComponent(connectionName.trim() || "default")}&redirectUri=${encodeURIComponent(returnUri)}`
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

  // Match auth config if provided
  const activeConfig = authConfigs.find((c) => c.type === authType);

  const authOptions = authTypes.map((type) => {
    const config = authConfigs.find((c) => c.type === type);
    return {
      value: type,
      label:
        config?.label ||
        (type === "api_key"
          ? "API Key / Personal Access Token"
          : type === "oauth2"
          ? "OAuth 2.0 Access Token"
          : type === "no_auth"
          ? "No Authentication Required"
          : type),
    };
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (authType !== "no_auth" && !apiKey.trim()) {
        throw new Error("Please enter your token or API key.");
      }

      await fetchApi(`/api/connections/${service}`, {
        method: "PUT",
        body: JSON.stringify({
          authType,
          connectionName: connectionName.trim() || "default",
          values: {
            apiKey: apiKey.trim(),
            accessToken: apiKey.trim(),
          },
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

  // Dynamic guide & documentation resolution from provider configuration
  const guide = activeConfig?.setup_guide;
  const docsUrl = guide?.docs_url || activeConfig?.docs_url;
  const docsLabel = guide?.docs_label || activeConfig?.docs_label || `${displayName} Documentation`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Connect ${displayName}`}
      description="Credentials are validated with the provider in real-time, encrypted with AES-256, and stored locally."
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && (
          <div className="p-3 text-xs text-rose-800 bg-rose-50 border border-rose-200 rounded-md flex items-start gap-2">
            <AlertCircle size={14} className="text-rose-600 mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold">Validation Failed</div>
              <div className="mt-0.5">{error}</div>
            </div>
          </div>
        )}

        {/* Auth Type Selector */}
        {authOptions.length > 1 && (
          <CustomSelect
            label="Authentication Method"
            options={authOptions}
            value={authType}
            onChange={setAuthType}
          />
        )}

        {/* OAuth 2.0 PKCE Fast Path */}
        {oauthConfigured && (
          <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-md flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-zinc-900">OAuth 2.0 PKCE Available</span>
              <span className="text-[11px] text-zinc-500">Authorize directly with {displayName} consent flow</span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              loading={oauthLoading}
              onClick={handleOAuthLaunch}
              className="bg-white text-zinc-800 hover:bg-zinc-100 text-xs shrink-0"
            >
              Sign In via OAuth
            </Button>
          </div>
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
            A unique alias for this account instance (defaults to <code>default</code>).
          </p>
        </div>

        {/* Dynamic Provider Setup Guidance */}
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

            {/* Instructions */}
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

            {/* Scopes */}
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

        {/* Credential Input */}
        {authType !== "no_auth" && (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-zinc-700">
              {activeConfig?.label || (authType === "oauth2" ? "OAuth Access Token" : "API Key or Access Token")}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={activeConfig?.placeholder || "Enter secret key or token..."}
              required
              className="h-9 px-3 text-xs font-mono bg-white border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 text-zinc-900 placeholder:text-zinc-400"
            />
            {activeConfig?.description && (
              <p className="text-[11px] text-zinc-400">{activeConfig.description}</p>
            )}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-100">
          <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={loading}>
            {loading ? "Validating & Saving..." : "Validate & Connect"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

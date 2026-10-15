"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

function CallbackContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");
  const service = searchParams.get("service") || "";
  const connectionName = searchParams.get("connectionName") || "";
  const errorMsg = searchParams.get("error") || "";

  const [closing, setClosing] = useState(false);
  const isSuccess = status === "connected";
  const isError = status === "error" || Boolean(errorMsg);

  useEffect(() => {
    // Post result to parent opener window if opened as popup
    if (typeof window !== "undefined") {
      const payload = {
        type: "CONNECTOR_HUB_OAUTH_RESULT",
        status: isSuccess ? "success" : "error",
        service,
        connectionName,
        error: errorMsg,
      };

      if (window.opener) {
        try {
          window.opener.postMessage(payload, window.location.origin);
        } catch (e) {
          console.error("Failed to notify parent window", e);
        }

        setClosing(true);
        const timer = setTimeout(() => {
          window.close();
        }, 1200);
        return () => clearTimeout(timer);
      } else {
        // Fallback for regular tab / standalone navigation
        const timer = setTimeout(() => {
          const query = isSuccess
            ? `?status=connected&service=${encodeURIComponent(service)}&connectionName=${encodeURIComponent(connectionName)}`
            : `?status=error&error=${encodeURIComponent(errorMsg)}`;
          window.location.href = `/connections${query}`;
        }, 1500);
        return () => clearTimeout(timer);
      }
    }
  }, [status, service, connectionName, errorMsg, isSuccess]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center p-6 select-none">
      <div className="w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-2xl text-center flex flex-col items-center">
        {isSuccess ? (
          <>
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4">
              <CheckCircle2 size={26} />
            </div>
            <h1 className="text-base font-semibold text-zinc-100 mb-1">
              Connected Successfully!
            </h1>
            <p className="text-xs text-zinc-400 mb-4">
              {service ? `Your connection to ${service} is now active.` : "Authentication completed successfully."}
            </p>
            <div className="flex items-center gap-2 text-[11px] text-zinc-500 bg-zinc-950/50 px-3 py-1.5 rounded-md border border-zinc-800">
              <Loader2 size={12} className="animate-spin text-emerald-400" />
              <span>{closing ? "Closing window automatically..." : "Finalizing..."}</span>
            </div>
          </>
        ) : isError ? (
          <>
            <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mb-4">
              <AlertCircle size={26} />
            </div>
            <h1 className="text-base font-semibold text-zinc-100 mb-1">
              Connection Failed
            </h1>
            <p className="text-xs text-rose-400 mb-5 break-words max-w-xs">
              {errorMsg || "Provider authentication could not be completed."}
            </p>
            <button
              onClick={() => window.close()}
              className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Close Window
            </button>
          </>
        ) : (
          <>
            <Loader2 size={28} className="animate-spin text-blue-500 mb-4" />
            <h1 className="text-sm font-semibold text-zinc-200 mb-1">
              Finalizing Connection...
            </h1>
            <p className="text-xs text-zinc-500">
              Exchanging authorization token with provider.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
          <Loader2 size={24} className="animate-spin text-zinc-600" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}

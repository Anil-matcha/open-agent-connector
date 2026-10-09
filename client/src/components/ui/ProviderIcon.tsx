"use client";

import React, { useState } from "react";
import providerIconsMap from "@/lib/provider-icons.json";

interface ProviderIconProps {
  service?: string;
  displayName?: string;
  iconUrl?: string;
  className?: string;
  size?: "xs" | "sm" | "md" | "lg";
}

const sizeClasses = {
  xs: "w-4 h-4 text-[9px]",
  sm: "w-5 h-5 text-[10px]",
  md: "w-7 h-7 text-xs",
  lg: "w-10 h-10 text-sm",
};

const iconSizeClasses = {
  xs: "w-3.5 h-3.5",
  sm: "w-4 h-4",
  md: "w-5 h-5",
  lg: "w-7 h-7",
};

export function ProviderIcon({
  service = "",
  displayName = "",
  iconUrl,
  className = "",
  size = "md",
}: ProviderIconProps) {
  const [hasError, setHasError] = useState(false);

  const cleanService = (service || "").toLowerCase().trim();
  const name = displayName || service || "App";

  // 1. First priority: direct iconUrl if supplied
  // 2. Second priority: catalog icon mapping from the provider catalog
  // 3. Built-in reliable SVG fallbacks for core providers
  let resolvedUrl = iconUrl;
  if (!resolvedUrl && cleanService) {
    const catalogUrl = (providerIconsMap as Record<string, string>)[cleanService];
    if (catalogUrl) {
      resolvedUrl = catalogUrl;
    }
  }

  // Fallback initials
  const initials = name
    .split(/[\s_-]+/)
    .map((part) => part[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase() || "?";

  // Dedicated built-in SVGs if image fails or not in catalog
  if (hasError || !resolvedUrl) {
    if (cleanService === "github") {
      return (
        <span
          className={`inline-flex items-center justify-center rounded-md bg-zinc-900 text-white shrink-0 overflow-hidden shadow-xs ${sizeClasses[size]} ${className}`}
          title="GitHub"
        >
          <svg
            className={`${iconSizeClasses[size]} fill-current`}
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            />
          </svg>
        </span>
      );
    }

    if (cleanService === "hackernews") {
      return (
        <span
          className={`inline-flex items-center justify-center rounded-md bg-[#ff6600] text-white font-bold shrink-0 overflow-hidden shadow-xs ${sizeClasses[size]} ${className}`}
          title="Hacker News"
        >
          <span className="leading-none">Y</span>
        </span>
      );
    }

    if (cleanService === "slack") {
      return (
        <span
          className={`inline-flex items-center justify-center rounded-md bg-[#4A154B] p-1 text-white shrink-0 overflow-hidden shadow-xs ${sizeClasses[size]} ${className}`}
          title="Slack"
        >
          <svg className={`${iconSizeClasses[size]}`} viewBox="0 0 24 24" fill="none">
            <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" fill="#E01E5A"/>
            <path d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" fill="#36C5F0"/>
            <path d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" fill="#2EB67D"/>
            <path d="M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#ECB22E"/>
          </svg>
        </span>
      );
    }

    if (cleanService === "custom") {
      return (
        <span
          className={`inline-flex items-center justify-center rounded-md bg-zinc-800 text-amber-400 shrink-0 overflow-hidden shadow-xs ${sizeClasses[size]} ${className}`}
          title="Custom Webhook / HTTP"
        >
          <svg className={`${iconSizeClasses[size]} stroke-current`} viewBox="0 0 24 24" fill="none" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m18 16 4-4-4-4"/>
            <path d="m6 8-4 4 4 4"/>
            <path d="m14.5 4-5 16"/>
          </svg>
        </span>
      );
    }

    return (
      <span
        className={`inline-flex items-center justify-center rounded-md bg-zinc-100 text-zinc-600 font-semibold border border-zinc-200 shrink-0 select-none ${sizeClasses[size]} ${className}`}
        title={name}
      >
        {initials}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center justify-center rounded-md bg-white border border-zinc-200 p-0.5 shrink-0 overflow-hidden shadow-2xs ${sizeClasses[size]} ${className}`}
      title={name}
    >
      <img
        src={resolvedUrl}
        alt={name}
        className={`${iconSizeClasses[size]} object-contain`}
        loading="lazy"
        onError={() => setHasError(true)}
      />
    </span>
  );
}

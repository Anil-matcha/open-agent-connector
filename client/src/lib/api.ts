const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let cachedToken: string | null = null;
let syncingTokenPromise: Promise<string | null> | null = null;

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("connector_admin_token") || cachedToken;
}

export function setAdminToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("connector_admin_token", token);
  }
  cachedToken = token;
}

async function ensureLocalToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const existing = localStorage.getItem("connector_admin_token");
  if (existing) return existing;

  if (syncingTokenPromise) return syncingTokenPromise;

  syncingTokenPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/status`);
      if (res.ok) {
        const data = await res.json();
        if (data.localToken) {
          localStorage.setItem("connector_admin_token", data.localToken);
          cachedToken = data.localToken;
          return data.localToken;
        }
      }
    } catch {
      // Local sync failed; operator will enter manually if required
    }
    return null;
  })();

  return syncingTokenPromise;
}

export async function fetchApi<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  // Automatically attach admin token header if available
  let token = getAdminToken();
  if (!token && typeof window !== "undefined") {
    token = await ensureLocalToken();
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg =
      data?.detail?.message ||
      data?.detail ||
      data?.error?.message ||
      `Request failed with status ${response.status}`;
    throw new Error(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
  }

  return data;
}

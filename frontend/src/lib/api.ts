import axios from "axios";

/**
 * Central API client for PulseTrack AI.
 *
 * Auth design (v1, per roadmap):
 * - access token kept in localStorage, attached to every request
 * - on a 401 the client transparently calls /auth/refresh once and retries
 * - if refresh itself is rejected (expired or reuse detected) -> wipe tokens -> /login
 */

export const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

const TOKEN_KEY = "pt_access";
const REFRESH_KEY = "pt_refresh";

export const tokens = {
  get access() {
    return localStorage.getItem(TOKEN_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  save(access: string, refresh: string) {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const access = tokens.access;
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokens.refresh;
  if (!refresh) return null;
  try {
    const { data } = await axios.post(
      `${API_BASE}/auth/refresh`,
      { refresh_token: refresh },
      { headers: { Authorization: "" } }
    );
    const pair = data.data;
    tokens.save(pair.access_token, pair.refresh_token);
    return pair.access_token as string;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const code = error.response?.data?.error?.code;

    if (
      error.response?.status === 401 &&
      !original._retried &&
      code !== "REFRESH_REUSE_DETECTED"
    ) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken();
      const newAccess = await refreshing.finally(() => {
        refreshing = null;
      });
      if (newAccess) {
        original.headers.Authorization = `Bearer ${newAccess}`;
        return api(original);
      }
      tokens.clear();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

/** Uniform envelope helper: unwrap {data, error} -> data | throw readable Error. */
export async function unwrap<T>(promise: Promise<{ data: { data: T; error: { message: string } | null } }>): Promise<T> {
  const { data } = await promise;
  if (data.error) throw new Error(data.error.message);
  return data.data;
}

export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.error?.message ?? err.message;
  }
  return err instanceof Error ? err.message : String(err);
}

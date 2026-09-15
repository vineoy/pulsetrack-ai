import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, errorMessage, tokens, unwrap } from "../lib/api";
import type { AuthOut } from "../types";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    team_name: "",
    email: "",
    password: "",
  });

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const promise =
        mode === "login"
          ? api.post("/auth/login", { email: form.email, password: form.password })
          : api.post("/auth/register", {
              name: form.name,
              team_name: form.team_name,
              email: form.email,
              password: form.password,
            });
      const auth = await unwrap<AuthOut>(promise);
      tokens.save(auth.access_token, auth.refresh_token);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">
            PulseTrack <span className="text-indigo-400">AI</span>
          </h1>
          <p className="mt-1 text-sm text-slate-400">Uptime monitoring with an AI incident analyst</p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-xl">
          <div className="mb-5 grid grid-cols-2 rounded-lg bg-slate-100 p-1 text-sm font-medium">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`rounded-md py-1.5 ${mode === "login" ? "bg-white shadow" : "text-slate-500"}`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={`rounded-md py-1.5 ${mode === "register" ? "bg-white shadow" : "text-slate-500"}`}
            >
              Register
            </button>
          </div>

          <form onSubmit={submit} className="space-y-3">
            {mode === "register" && (
              <>
                <Field label="Your name" value={form.name} onChange={set("name")} placeholder="Ada Lovelace" required />
                <Field
                  label="Team / company name"
                  value={form.team_name}
                  onChange={set("team_name")}
                  placeholder="Acme Inc"
                  required
                />
              </>
            )}
            <Field
              label="Email"
              type="email"
              value={form.email}
              onChange={set("email")}
              placeholder="you@company.com"
              required
            />
            <Field
              label="Password"
              type="password"
              value={form.password}
              onChange={set("password")}
              placeholder={mode === "register" ? "min. 8 characters" : "••••••••"}
              required
            />

            {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {busy ? "Working…" : mode === "login" ? "Log in" : "Create team account"}
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-slate-400">
            Demo: <code className="text-slate-600">demo@pulsetrack.dev</code> / Demo1234!
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-600">{label}</span>
      <input
        {...props}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
      />
    </label>
  );
}

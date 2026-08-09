/**
 * Login Page — /login
 *
 * Premium authentication entry point for MultiAgent OS.
 * Integrates with existing POST /api/auth/login (OAuth2PasswordRequestForm).
 *
 * On success → redirects to /app.
 */

"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, AlertCircle, Zap } from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { Sun, Moon } from "lucide-react";
import api from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cycleTheme = () => {
    const order: Array<"light" | "dark" | "system"> = [
      "light",
      "dark",
      "system",
    ];
    const idx = order.indexOf(theme);
    setTheme(order[(idx + 1) % order.length]);
  };

  const validateForm = (): boolean => {
    if (!email.trim()) {
      setError("Email is required.");
      return false;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError("Please enter a valid email address.");
      return false;
    }
    if (!password) {
      setError("Password is required.");
      return false;
    }
    if (password.length < 4) {
      setError("Password must be at least 4 characters.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) return;

    setLoading(true);
    try {
      // Backend expects OAuth2PasswordRequestForm (form-encoded, username field)
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      await api.post("/api/auth/login", formData, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      // Success — navigate to authenticated app
      router.push("/app");
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError("Incorrect email or password.");
      } else if (err?.response?.data?.detail) {
        setError(
          typeof err.response.data.detail === "string"
            ? err.response.data.detail
            : "Authentication failed."
        );
      } else if (err?.request) {
        setError(
          "Unable to reach the backend. Ensure the server is running."
        );
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex"
      style={{ background: "var(--bg-primary)", color: "var(--fg-primary)" }}
    >
      {/* Left Panel — Branding (desktop only) */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 border-r-2 border-[var(--border-primary)]"
        style={{ background: "var(--bg-surface)" }}
      >
        <div>
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 mb-16">
            <div
              className="w-8 h-8 border-2 border-[var(--border-primary)] flex items-center justify-center"
              style={{ background: "var(--accent-primary)" }}
            >
              <span className="text-[11px] font-black text-[var(--fg-on-accent)] leading-none">
                M
              </span>
            </div>
            <span
              className="text-sm font-extrabold tracking-tight uppercase"
              style={{ color: "var(--fg-primary)" }}
            >
              MultiAgent OS
            </span>
          </Link>

          {/* Branding text */}
          <h1
            className="text-display mb-6"
            style={{ color: "var(--fg-primary)" }}
          >
            Multi-Agent
            <br />
            <span style={{ color: "var(--accent-primary)" }}>
              Intelligence.
            </span>
          </h1>
          <p className="text-body" style={{ color: "var(--fg-secondary)" }}>
            Seven specialized AI agents collaborating through orchestrated
            workflows to deliver comprehensive results.
          </p>
        </div>

        {/* Bottom decorative info */}
        <div className="flex items-center gap-6">
          {["Planner", "Researcher", "Coder", "Tester", "Reviewer"].map(
            (agent) => (
              <span
                key={agent}
                className="text-caption"
                style={{ color: "var(--fg-tertiary)" }}
              >
                {agent}
              </span>
            )
          )}
        </div>
      </div>

      {/* Right Panel — Form */}
      <div className="flex-1 flex flex-col">
        {/* Top bar with theme toggle */}
        <div className="flex items-center justify-between p-4 sm:p-6">
          {/* Mobile logo */}
          <Link href="/" className="flex items-center gap-2 lg:hidden">
            <div
              className="w-7 h-7 border-2 border-[var(--border-primary)] flex items-center justify-center"
              style={{ background: "var(--accent-primary)" }}
            >
              <span className="text-[10px] font-black text-[var(--fg-on-accent)] leading-none">
                M
              </span>
            </div>
            <span
              className="text-xs font-extrabold tracking-tight uppercase"
              style={{ color: "var(--fg-primary)" }}
            >
              MultiAgent OS
            </span>
          </Link>
          <div className="lg:ml-auto" />

          <button
            onClick={cycleTheme}
            type="button"
            className="w-8 h-8 flex items-center justify-center border-2 border-[var(--border-primary)]"
            style={{
              background: "var(--bg-surface)",
              boxShadow: "var(--shadow-brutalist-sm)",
              color: "var(--fg-primary)",
            }}
            aria-label="Toggle theme"
          >
            <Sun
              className="w-3.5 h-3.5 dark:hidden"
              aria-hidden="true"
            />
            <Moon
              className="w-3.5 h-3.5 hidden dark:inline"
              aria-hidden="true"
            />
          </button>
        </div>

        {/* Form container */}
        <div className="flex-1 flex items-center justify-center px-4 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-8">
              <h2 className="text-h1 mb-2">Welcome Back</h2>
              <p
                className="text-body"
                style={{ color: "var(--fg-secondary)" }}
              >
                Access your AI orchestration workspace.
              </p>
            </div>

            {/* Error */}
            {error && (
              <div
                className="mb-6 p-3 border-2 flex items-start gap-3"
                style={{
                  borderColor: "var(--accent-error)",
                  background: "rgba(239,68,68,0.05)",
                }}
                role="alert"
              >
                <AlertCircle
                  className="w-4 h-4 mt-0.5 shrink-0"
                  style={{ color: "var(--accent-error)" }}
                  aria-hidden="true"
                />
                <span
                  className="text-body-sm"
                  style={{ color: "var(--accent-error)" }}
                >
                  {error}
                </span>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              {/* Email */}
              <div className="mb-5">
                <label htmlFor="login-email" className="form-label">
                  Email
                </label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError(null);
                  }}
                  placeholder="admin@enterprise.com"
                  disabled={loading}
                  className={`form-input ${error && !email ? "form-input-error" : ""}`}
                />
              </div>

              {/* Password */}
              <div className="mb-6">
                <label htmlFor="login-password" className="form-label">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setError(null);
                    }}
                    placeholder="Enter your password"
                    disabled={loading}
                    className={`form-input pr-10 ${error && !password ? "form-input-error" : ""}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    style={{ color: "var(--fg-tertiary)" }}
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" aria-hidden="true" />
                    ) : (
                      <Eye className="w-4 h-4" aria-hidden="true" />
                    )}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="brutalist-btn brutalist-btn-primary w-full justify-center"
              >
                {loading ? (
                  <>
                    <Loader2
                      className="w-4 h-4 animate-spin"
                      aria-hidden="true"
                    />
                    Signing in...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" aria-hidden="true" />
                    Sign In
                  </>
                )}
              </button>
            </form>

            {/* Forgot password */}
            <div className="mt-4 text-center">
              <span
                className="text-body-sm"
                style={{ color: "var(--fg-tertiary)" }}
              >
                Forgot password?
              </span>
            </div>

            {/* Divider */}
            <div
              className="my-8 h-px"
              style={{ background: "var(--border-secondary)" }}
            />

            {/* Signup link */}
            <div className="text-center">
              <p
                className="text-body-sm mb-2"
                style={{ color: "var(--fg-secondary)" }}
              >
                Don&apos;t have an account?
              </p>
              <Link
                href="/signup"
                className="text-body-sm font-bold uppercase tracking-wide"
                style={{ color: "var(--accent-primary)" }}
              >
                Create account →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

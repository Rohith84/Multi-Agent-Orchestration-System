/**
 * Signup Page — /signup
 *
 * Registration experience matching /login style.
 * As no backend registration endpoint exists yet, this UI validates fields
 * and displays a clear message that backend registration is pending,
 * without faking successful registration.
 */

"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Loader2, AlertCircle, Info, Sun, Moon } from "lucide-react";
import { useTheme } from "@/components/theme-provider";

export default function SignupPage() {
  const { theme, setTheme } = useTheme();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organization, setOrganization] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const cycleTheme = () => {
    const order: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];
    const idx = order.indexOf(theme);
    setTheme(order[(idx + 1) % order.length]);
  };

  const validateForm = (): boolean => {
    if (!name.trim()) {
      setError("Full name is required.");
      return false;
    }
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
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return false;
    }
    if (!organization.trim()) {
      setError("Organization name is required.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);

    if (!validateForm()) return;

    setLoading(true);
    // Simulate short submission delay
    await new Promise((resolve) => setTimeout(resolve, 600));
    setLoading(false);

    // Backend registration is not yet implemented — display explicit notice
    setInfoMessage(
      "Self-service account registration is currently pending backend API support. Please contact your platform administrator or sign in with existing enterprise credentials."
    );
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
            Create Your
            <br />
            <span style={{ color: "var(--accent-secondary)" }}>
              Workspace.
            </span>
          </h1>
          <p className="text-body" style={{ color: "var(--fg-secondary)" }}>
            Build your enterprise AI execution environment with specialized agent teams and full governance control.
          </p>
        </div>

        {/* Bottom decorative info */}
        <div className="flex items-center gap-6">
          {["Identity", "Access", "Auditability", "Control"].map(
            (item) => (
              <span
                key={item}
                className="text-caption"
                style={{ color: "var(--fg-tertiary)" }}
              >
                {item}
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
            <Sun className="w-3.5 h-3.5 dark:hidden" aria-hidden="true" />
            <Moon className="w-3.5 h-3.5 hidden dark:inline" aria-hidden="true" />
          </button>
        </div>

        {/* Form container */}
        <div className="flex-1 flex items-center justify-center px-4 sm:px-8 py-6">
          <div className="w-full max-w-md">
            <div className="mb-6">
              <h2 className="text-h1 mb-2">Create Account</h2>
              <p className="text-body" style={{ color: "var(--fg-secondary)" }}>
                Register your organization workspace.
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div
                className="mb-5 p-3 border-2 flex items-start gap-3"
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

            {/* Info Message */}
            {infoMessage && (
              <div
                className="mb-5 p-3 border-2 flex items-start gap-3"
                style={{
                  borderColor: "var(--accent-tertiary)",
                  background: "rgba(6,182,212,0.05)",
                }}
                role="status"
              >
                <Info
                  className="w-4 h-4 mt-0.5 shrink-0"
                  style={{ color: "var(--accent-tertiary)" }}
                  aria-hidden="true"
                />
                <span
                  className="text-body-sm"
                  style={{ color: "var(--fg-primary)" }}
                >
                  {infoMessage}
                </span>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              {/* Full Name */}
              <div className="mb-4">
                <label htmlFor="signup-name" className="form-label">
                  Full Name
                </label>
                <input
                  id="signup-name"
                  type="text"
                  autoComplete="name"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setError(null);
                  }}
                  placeholder="Jane Doe"
                  disabled={loading}
                  className={`form-input ${error && !name.trim() ? "form-input-error" : ""}`}
                />
              </div>

              {/* Email */}
              <div className="mb-4">
                <label htmlFor="signup-email" className="form-label">
                  Work Email
                </label>
                <input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError(null);
                  }}
                  placeholder="jane@company.com"
                  disabled={loading}
                  className={`form-input ${error && !email.trim() ? "form-input-error" : ""}`}
                />
              </div>

              {/* Password */}
              <div className="mb-4">
                <label htmlFor="signup-password" className="form-label">
                  Password
                </label>
                <input
                  id="signup-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError(null);
                  }}
                  placeholder="At least 6 characters"
                  disabled={loading}
                  className={`form-input ${error && !password ? "form-input-error" : ""}`}
                />
              </div>

              {/* Organization */}
              <div className="mb-6">
                <label htmlFor="signup-org" className="form-label">
                  Organization Name
                </label>
                <input
                  id="signup-org"
                  type="text"
                  autoComplete="organization"
                  value={organization}
                  onChange={(e) => {
                    setOrganization(e.target.value);
                    setError(null);
                  }}
                  placeholder="Acme Corp"
                  disabled={loading}
                  className={`form-input ${error && !organization.trim() ? "form-input-error" : ""}`}
                />
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="brutalist-btn brutalist-btn-primary w-full justify-center"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    Creating Account...
                  </>
                ) : (
                  "Create Account"
                )}
              </button>
            </form>

            {/* Divider */}
            <div
              className="my-6 h-px"
              style={{ background: "var(--border-secondary)" }}
            />

            {/* Login link */}
            <div className="text-center">
              <p className="text-body-sm mb-2" style={{ color: "var(--fg-secondary)" }}>
                Already have an account?
              </p>
              <Link
                href="/login"
                className="text-body-sm font-bold uppercase tracking-wide"
                style={{ color: "var(--accent-text)" }}
              >
                Sign in →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

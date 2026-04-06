"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiLogin, apiSignup } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLogin && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (isLogin) {
        await apiLogin(email, password);
      } else {
        await apiSignup(email, password);
      }
      router.replace("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg-primary)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px",
    }} className="bg-grid">

      {/* Card */}
      <div style={{
        width: "100%",
        maxWidth: "420px",
        background: "rgba(255,255,255,0.02)",
        border: "1px solid var(--border)",
        borderRadius: "20px",
        padding: "40px",
        backdropFilter: "blur(12px)",
      }} className="animate-in">

        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "32px" }}>
          <div style={{
            width: "36px", height: "36px",
            borderRadius: "10px",
            background: "linear-gradient(135deg, #3b82f6, #6366f1)",
            boxShadow: "0 4px 12px rgba(59,130,246,0.3)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="18" height="18" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span style={{ fontWeight: 800, fontSize: "18px", letterSpacing: "-0.03em" }}>AdNova</span>
        </div>

        <h1 style={{ fontSize: "24px", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "6px" }}>
          {isLogin ? "Welcome back" : "Create your account"}
        </h1>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "28px" }}>
          {isLogin ? "Sign in to your AdNova account" : "Start optimizing your ad spend with AI"}
        </p>

        {/* Error */}
        {error && (
          <div style={{
            padding: "12px 16px",
            background: "var(--red-muted)",
            border: "1px solid rgba(244,63,94,0.3)",
            borderRadius: "10px",
            fontSize: "14px",
            color: "var(--red)",
            marginBottom: "16px",
          }}>
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label className="form-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className="form-input"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              placeholder={isLogin ? "••••••••" : "Min. 8 characters"}
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete={isLogin ? "current-password" : "new-password"}
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ width: "100%", justifyContent: "center", marginTop: "4px" }}
          >
            {loading ? (
              <>
                <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
                {isLogin ? "Signing in..." : "Creating account..."}
              </>
            ) : (isLogin ? "Sign in" : "Create account")}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: "13px", color: "var(--text-muted)", marginTop: "24px" }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button 
            type="button" 
            onClick={() => { setIsLogin(!isLogin); setError(""); }}
            style={{ color: "var(--gold)", fontWeight: 600, background: "none", border: "none", cursor: "pointer", padding: 0, font: "inherit" }}
          >
            {isLogin ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}

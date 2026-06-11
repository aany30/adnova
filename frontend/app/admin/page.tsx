"use client";

import { useEffect, useState } from "react";
import { Activity, AlertTriangle, BarChart3, CheckCircle, Gauge, RefreshCw, Settings, Shield, Zap } from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";

interface AdminEvent {
  actor_id?: string;
  status?: string;
  reason?: string;
  created_at?: string;
  metadata?: Record<string, unknown>;
}

interface AdminStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  fallback_count: number;
  fallback_rate: number;
  model_profile: string;
  daily_limit: number;
  monthly_limit: number;
  recent_events: AdminEvent[];
  recent_failures: AdminEvent[];
  generated_at: string;
}

interface AdminPayload {
  status: string;
  stats: AdminStats;
  config: {
    model_profile: string;
    available_profiles: string[];
    daily_limit: number;
    monthly_limit: number;
  };
}

function AdminMetric({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="admin-metric glass-card">
      <div className="admin-metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <p>{hint}</p>}
    </div>
  );
}

export default function AdminPage() {
  const [data, setData] = useState<AdminPayload | null>(null);
  const [modelProfile, setModelProfile] = useState("balanced");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  async function loadStats() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth("/admin/stats");
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.detail || "Could not load admin stats");
      setData(payload);
      setModelProfile(payload.config.model_profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load admin stats");
    } finally {
      setLoading(false);
    }
  }

  async function saveConfig() {
    setSaving(true);
    setSaved(null);
    setError(null);
    try {
      const res = await fetchWithAuth("/admin/config", {
        method: "PATCH",
        body: JSON.stringify({
          model_profile: modelProfile,
        }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.detail || "Could not save admin config");
      setSaved("Config saved for this server session.");
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save admin config");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    loadStats();
  }, []);

  const stats = data?.stats;

  return (
    <main className="admin-page">
      <section className="admin-hero">
        <div>
          <div className="badge">
            <Shield size={12} />
            Operator Console
          </div>
          <h1>AdNova Admin</h1>
          <p>Monitor campaign optimizer usage, fallback health, model profile, limits, and recent failures.</p>
        </div>
        <button className="btn-secondary admin-refresh" onClick={loadStats} disabled={loading}>
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </section>

      {error && (
        <div className="co-error admin-banner">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {saved && (
        <div className="admin-success admin-banner">
          <CheckCircle size={16} />
          <span>{saved}</span>
        </div>
      )}

      {loading && !stats ? (
        <section className="admin-loading-grid">
          <div className="glass-card skeleton" />
          <div className="glass-card skeleton" />
          <div className="glass-card skeleton" />
          <div className="glass-card skeleton" />
        </section>
      ) : stats ? (
        <>
          <section className="admin-metric-grid">
            <AdminMetric icon={<BarChart3 size={18} />} label="Total requests" value={stats.total_requests} hint="Campaign optimizer attempts" />
            <AdminMetric icon={<CheckCircle size={18} />} label="Successful" value={stats.successful_requests} hint="Completed analyses" />
            <AdminMetric icon={<AlertTriangle size={18} />} label="Failed" value={stats.failed_requests} hint="Backend or AI failures" />
            <AdminMetric icon={<Zap size={18} />} label="Fallback rate" value={`${stats.fallback_rate}%`} hint={`${stats.fallback_count} fallback responses`} />
          </section>

          <section className="admin-grid admin-grid-single">
            <div className="glass-card admin-card">
              <div className="admin-card-heading">
                <Gauge size={18} />
                <div>
                  <h2>Model Selection</h2>
                  <p>Balanced is the default. Economy lowers cost; quality prioritizes output depth.</p>
                </div>
              </div>
              <label className="admin-field">
                Model profile
                <select className="form-input" value={modelProfile} onChange={(e) => setModelProfile(e.target.value)}>
                  {(data.config.available_profiles || ["quality", "balanced", "economy"]).map((profile) => (
                    <option key={profile} value={profile}>{profile}</option>
                  ))}
                </select>
              </label>
              <button className="btn-primary admin-save" onClick={saveConfig} disabled={saving}>
                <Settings size={16} />
                {saving ? "Saving" : "Save model profile"}
              </button>
            </div>
          </section>

          <section className="admin-grid">
            <div className="glass-card admin-card">
              <div className="admin-card-heading">
                <Activity size={18} />
                <div>
                  <h2>Recent Analyses</h2>
                  <p>Latest usage events from this server session.</p>
                </div>
              </div>
              <div className="admin-event-list">
                {stats.recent_events.length ? stats.recent_events.map((event, index) => (
                  <div key={`${event.created_at}-${index}`} className="admin-event">
                    <strong>{event.status || "unknown"}</strong>
                    <span>{event.actor_id || "unknown actor"}</span>
                    <p>{event.reason || String(event.metadata?.file_name || "Campaign optimizer request")}</p>
                  </div>
                )) : <p className="co-muted">No analyses recorded yet.</p>}
              </div>
            </div>

            <div className="glass-card admin-card">
              <div className="admin-card-heading">
                <AlertTriangle size={18} />
                <div>
                  <h2>Failed Requests</h2>
                  <p>Clear reason labels help separate extraction, quota, and OpenAI issues.</p>
                </div>
              </div>
              <div className="admin-event-list">
                {stats.recent_failures.length ? stats.recent_failures.map((event, index) => (
                  <div key={`${event.created_at}-${index}`} className="admin-event admin-event-failure">
                    <strong>{event.reason || "failure"}</strong>
                    <span>{event.actor_id || "unknown actor"}</span>
                    <p>{String(event.metadata?.error || event.metadata?.file_name || "No extra detail")}</p>
                  </div>
                )) : <p className="co-muted">No failures recorded yet.</p>}
              </div>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}

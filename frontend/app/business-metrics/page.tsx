"use client";
import { useState, useRef } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";
import { 
  Calculator, DollarSign, Package, Image as ImageIcon,
  AlertTriangle, Activity, Target, CheckCircle, Lightbulb, 
  TrendingUp, BarChart as BarChartIcon, BrainCircuit, Play, ArrowRight
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface MetricsResult {
  metrics: {
    spend_total: number;
    spend_per_day: number;
    days: number;
    orders: number;
    revenue: number;
    cogs_total: number;
    net_profit: number;
    cpa: number;
    roas: number;
    roi: number;
    profit_margin_pct: number;
    break_even_roas: number;
    margin_pct: number;
    verdict: string;
    verdict_color: string;
    cost_price: number;
    selling_price: number;
  };
  ai_analysis: {
    creative_quality_score?: number;
    hook_analysis?: string;
    why_it_worked?: string[];
    weaknesses?: string[];
    improvement_suggestions?: string[];
    india_market_fit?: string;
    verdict?: string;
    performance_verdict?: string;
    performance_summary?: string;
    key_insights?: string[];
    improvement_actions?: string[];
    next_steps?: string;
    benchmark_comparison?: string;
  };
  creative_analyzed: boolean;
}

function MetricCard({ label, value, sub, color, icon: Icon }: { label: string; value: string; sub?: string; color?: string; icon?: any }) {
  return (
    <div className="glass-card" style={{ padding: "24px 28px", position: "relative", overflow: "hidden" }}>
      {Icon && <Icon size={40} style={{ position: "absolute", right: "-10px", bottom: "-10px", opacity: 0.05, color: color || "var(--text-primary)" }} />}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
        {Icon && <Icon size={14} color={color || "var(--text-muted)"} />}
        <div className="metric-label" style={{ margin: 0 }}>{label}</div>
      </div>
      <div className="metric-value" style={{ color: color || "var(--text-primary)" }}>{value}</div>
      {sub && <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "8px", fontWeight: 500 }}>{sub}</div>}
    </div>
  );
}

// Custom tooltip for Recharts
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div style={{ background: "rgba(9, 9, 11, 0.9)", border: "1px solid var(--border)", padding: "10px 14px", borderRadius: "8px", backdropFilter: "blur(8px)" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: "12px", marginBottom: "4px" }}>{payload[0].payload.name}</p>
        <p style={{ color: payload[0].payload.fill, fontSize: "16px", fontWeight: 700 }}>₹{payload[0].value.toLocaleString("en-IN")}</p>
      </div>
    );
  }
  return null;
};

export default function BusinessMetrics() {
  const [form, setForm] = useState({
    spendTotal: "",
    spendPerDay: "",
    usePerDay: false,
    days: "",
    orders: "",
    costPrice: "",
    sellingPrice: "",
  });
  const [creativeFile, setCreativeFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MetricsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (file: File) => {
    setCreativeFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileChange(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const totalSpend = form.usePerDay
      ? parseFloat(form.spendPerDay) * parseInt(form.days)
      : parseFloat(form.spendTotal);

    const body = new FormData();
    body.append("spend_total", String(totalSpend));
    body.append("days", form.days || "1");
    body.append("orders", form.orders);
    body.append("cost_price", form.costPrice);
    body.append("selling_price", form.sellingPrice);
    if (creativeFile) body.append("creative", creativeFile);

    try {
      const res = await fetch(`${API}/metrics`, { method: "POST", body });
      if (!res.ok) {
        let errorMsg = "Analysis failed";
        try {
          const err = await res.json();
          errorMsg = err.detail || errorMsg;
        } catch (e) {
          errorMsg = `Server error (${res.status}): ${res.statusText}`;
        }
        throw new Error(errorMsg);
      }
      const data = await res.json();
      setResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend. Is it running?";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fmtCurrency = (n: number) => `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
  const fmtNum = (n: number, d = 2) => n.toFixed(d);

  // Prepare chart data for Unit Economics if result exists
  let unitData: { name: string; value: number; fill: string }[] = [];
  if (result) {
    const profitPerUnit = result.metrics.selling_price - result.metrics.cost_price - result.metrics.cpa;
    unitData = [
      { name: "Cost Price (COGS)", value: result.metrics.cost_price, fill: "#94a3b8" }, // neutral slate
      { name: "CPA (Ad Cost/Order)", value: Math.round(result.metrics.cpa), fill: "#3b82f6" }, // pro blue
      { name: "Net Profit / Order", value: Math.round(profitPerUnit), fill: profitPerUnit >= 0 ? "#10b981" : "#f43f5e" }, // emerald or rose
    ];
  }

  return (
    <div style={{ padding: "40px", maxWidth: "1140px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "40px" }} className="animate-in">
        <div className="badge" style={{ marginBottom: "16px", background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
          <Activity size={12} style={{ marginRight: "4px" }} />
          Performance Intelligence
        </div>
        <h1 style={{ fontSize: "36px", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "12px" }}>
          Unit Economics <span className="gradient-text">& Profitability</span>
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "16px", maxWidth: "600px", lineHeight: 1.6 }}>
          Input your raw campaign data to visualize your break-even metrics and true net profit. Add your creative for deep AI diagnostic analysis.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: "32px", alignItems: "start" }}>
        {/* Form */}
        <div className="glass-card" style={{ padding: "32px" }}>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: "24px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                <DollarSign size={16} color="var(--gold)" />
                <h3 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>Total Investment</h3>
              </div>
              
              <div style={{ display: "flex", gap: "8px", marginBottom: "16px", background: "rgba(0,0,0,0.2)", padding: "4px", borderRadius: "10px" }}>
                <button type="button" onClick={() => setForm(f => ({ ...f, usePerDay: false }))}
                  className={form.usePerDay ? "" : "btn-primary"}
                  style={{ flex: 1, fontSize: "12px", padding: "8px 12px", borderRadius: "8px", border: "none", background: form.usePerDay ? "transparent" : "#fff", color: form.usePerDay ? "var(--text-secondary)" : "#000", fontWeight: 600, cursor: "pointer", transition: "all 0.2s" }}>
                  Total Spend
                </button>
                <button type="button" onClick={() => setForm(f => ({ ...f, usePerDay: true }))}
                  style={{ flex: 1, fontSize: "12px", padding: "8px 12px", borderRadius: "8px", border: "none", background: form.usePerDay ? "#fff" : "transparent", color: form.usePerDay ? "#000" : "var(--text-secondary)", fontWeight: 600, cursor: "pointer", transition: "all 0.2s" }}>
                  Per Day
                </button>
              </div>

              {form.usePerDay ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label className="form-label">Spend/Day (₹)</label>
                    <input className="form-input" type="number" placeholder="1500" value={form.spendPerDay} onChange={e => setForm(f => ({ ...f, spendPerDay: e.target.value }))} required />
                  </div>
                  <div>
                    <label className="form-label">Days</label>
                    <input className="form-input" type="number" placeholder="7" value={form.days} onChange={e => setForm(f => ({ ...f, days: e.target.value }))} required />
                  </div>
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label className="form-label">Total Spend (₹)</label>
                    <input className="form-input" type="number" placeholder="10000" value={form.spendTotal} onChange={e => setForm(f => ({ ...f, spendTotal: e.target.value }))} required />
                  </div>
                  <div>
                    <label className="form-label">Days Ran</label>
                    <input className="form-input" type="number" placeholder="7" value={form.days} onChange={e => setForm(f => ({ ...f, days: e.target.value }))} required />
                  </div>
                </div>
              )}
            </div>

            <hr className="divider" />

            <div style={{ marginBottom: "24px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                <Package size={16} color="var(--purple)" />
                <h3 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>Returns & Margins</h3>
              </div>
              <div style={{ marginBottom: "16px" }}>
                <label className="form-label">Total Orders Generated</label>
                <input className="form-input" type="number" placeholder="45" value={form.orders} onChange={e => setForm(f => ({ ...f, orders: e.target.value }))} required />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label className="form-label">Cost Price (₹)</label>
                  <input className="form-input" type="number" placeholder="350" value={form.costPrice} onChange={e => setForm(f => ({ ...f, costPrice: e.target.value }))} required />
                </div>
                <div>
                  <label className="form-label">Selling Price (₹)</label>
                  <input className="form-input" type="number" placeholder="799" value={form.sellingPrice} onChange={e => setForm(f => ({ ...f, sellingPrice: e.target.value }))} required />
                </div>
              </div>
            </div>

            <hr className="divider" />

            {/* Creative Upload */}
            <div style={{ marginBottom: "32px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                <ImageIcon size={16} color="var(--blue)" />
                <h3 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>Creative Context (Optional)</h3>
              </div>
              <div
                className="upload-zone"
                style={{ padding: "24px", position: "relative" }}
                onDrop={handleDrop}
                onDragOver={e => e.preventDefault()}
                onClick={() => fileRef.current?.click()}
              >
                <input ref={fileRef} type="file" accept="image/*,video/*" style={{ display: "none" }} onChange={e => { const f = e.target.files?.[0]; if (f) handleFileChange(f); }} />
                {previewUrl ? (
                  <div>
                    {creativeFile?.type.startsWith("video") ? (
                      <video src={previewUrl} style={{ width: "100%", maxHeight: "140px", objectFit: "cover", borderRadius: "8px", border: "1px solid var(--border)" }} muted />
                    ) : (
                      <img src={previewUrl} alt="Creative preview" style={{ width: "100%", maxHeight: "140px", objectFit: "cover", borderRadius: "8px", border: "1px solid var(--border)" }} />
                    )}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", marginTop: "12px", color: "var(--green)" }}>
                      <CheckCircle size={14} />
                      <span style={{ fontSize: "12px", fontWeight: 500 }}>{creativeFile?.name}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ display: "flex", justifyContent: "center", marginBottom: "12px", color: "var(--text-muted)" }}>
                      <Play size={28} />
                    </div>
                    <p style={{ fontSize: "13px", color: "var(--text-primary)", fontWeight: 500 }}>Select Video or Image</p>
                    <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>Powers the AI diagnostic engine</p>
                  </>
                )}
              </div>
            </div>

            {error && (
              <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", padding: "14px 16px", background: "var(--red-muted)", border: "1px solid rgba(244,63,94,0.2)", borderRadius: "10px", color: "var(--red)", fontSize: "13px", marginBottom: "20px" }}>
                <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
                <span>{error}</span>
              </div>
            )}

            <button type="submit" className="btn-primary" style={{ width: "100%", justifyContent: "center", padding: "16px", fontSize: "15px" }} disabled={loading}>
              {loading ? (
                <>
                  <svg className="animate-spin" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                  Processing Data...
                </>
              ) : (
                <>
                  <BarChartIcon size={18} />
                  Calculate Unit Economics
                </>
              )}
            </button>
          </form>
        </div>

        {/* Results */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {!result && !loading && (
             <div className="glass-card" style={{ padding: "120px 40px", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <BarChartIcon size={48} style={{ color: "var(--text-muted)", opacity: 0.5, marginBottom: "24px" }} strokeWidth={1} />
              <h3 style={{ fontSize: "20px", fontWeight: 600, marginBottom: "8px", color: "var(--text-secondary)" }}>Awaiting Data</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "15px", maxWidth: "340px", lineHeight: 1.6 }}>Feed the engine your ad spend and product margins to unlock deep financial insights.</p>
            </div>
          )}

          {loading && (
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <div className="glass-card skeleton" style={{ height: "140px" }} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                <div className="glass-card skeleton" style={{ height: "180px" }} />
                <div className="glass-card skeleton" style={{ height: "180px" }} />
              </div>
              <div className="glass-card skeleton" style={{ height: "300px" }} />
            </div>
          )}

          {result && (
            <div className="animate-in" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              
              {/* Verdict Header Line */}
              <div className="glass-card" style={{ padding: "24px 30px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "linear-gradient(to right, rgba(255,255,255,0.01), rgba(255,255,255,0.03))" }}>
                <div>
                  <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>Campaign Verdict</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: result.metrics.verdict_color === "green" ? "var(--green)" : result.metrics.verdict_color === "red" ? "var(--red)" : "var(--gold)" }} />
                    <span style={{ fontSize: "18px", fontWeight: 700 }}>{result.metrics.verdict}</span>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>Financial Flow</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "16px", color: "var(--text-secondary)" }}>{fmtCurrency(result.metrics.spend_total)}</span>
                    <ArrowRight size={14} color="var(--text-muted)" />
                    <span style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)" }}>{fmtCurrency(result.metrics.revenue)}</span>
                  </div>
                </div>
              </div>

              {/* Core 4 MetricsGrid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                <MetricCard icon={Target} label="ROAS" value={`${fmtNum(result.metrics.roas)}x`} sub={`Break-even threshold: ${fmtNum(result.metrics.break_even_roas)}x`} color={result.metrics.roas >= result.metrics.break_even_roas ? "var(--green)" : "var(--red)"} />
                <MetricCard icon={DollarSign} label="Net Profit" value={fmtCurrency(result.metrics.net_profit)} sub={`Margin: ${fmtNum(result.metrics.profit_margin_pct)}%`} color={result.metrics.net_profit >= 0 ? "var(--green)" : "var(--red)"} />
                <MetricCard icon={TrendingUp} label="ROI" value={`${fmtNum(result.metrics.roi)}%`} sub="Return on Investment" color={result.metrics.roi >= 0 ? "var(--text-primary)" : "var(--red)"} />
                <MetricCard icon={Package} label="CPA (Cost per Acquisition)" value={fmtCurrency(result.metrics.cpa)} sub={`Acquired ${result.metrics.orders} customers`} color="var(--gold-light)" />
              </div>

              {/* Aesthetic Explained Graph - Unit Economics */}
              <div className="glass-card" style={{ padding: "30px", overflow: "hidden" }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "30px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                      <BarChartIcon size={16} color="var(--gold)" />
                      <h4 style={{ fontSize: "14px", fontWeight: 700 }}>Unit Economics Breakdown</h4>
                    </div>
                    <p style={{ fontSize: "13px", color: "var(--text-muted)", maxWidth: "400px", lineHeight: 1.5 }}>
                      This chart illustrates where the money from a single order (₹{fmtNum(result.metrics.selling_price, 0)}) goes. 
                      If Cost Price + CPA exceeds the Selling Price, your net profit is negative.
                    </p>
                  </div>
                  <div style={{ textAlign: "right", background: "rgba(255,255,255,0.03)", padding: "12px 16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px" }}>Selling Price</div>
                    <div style={{ fontSize: "20px", fontWeight: 800 }}>{fmtCurrency(result.metrics.selling_price)}</div>
                  </div>
                </div>

                <div style={{ width: "100%", height: "240px", marginLeft: "-15px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={unitData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                      <XAxis type="number" hide />
                      <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-secondary)', fontSize: 12, fontWeight: 500 }} width={140} />
                      <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={28}>
                        {unitData.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Bar>
                      <ReferenceLine x={0} stroke="var(--border)" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* AI Analysis Details */}
              {result.ai_analysis && (
                <div className="glass-card" style={{ padding: "32px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "30px", paddingBottom: "20px", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "var(--blue-muted)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <BrainCircuit size={18} color="var(--blue)" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "16px" }}>Diagnostic Intelligence</div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                        {result.creative_analyzed ? "Deep scan: Financials + Creative Video/Image" : "Financials-only Analysis"}
                      </div>
                    </div>
                  </div>

                  {result.creative_analyzed ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                      {result.ai_analysis.hook_analysis && (
                        <div style={{ padding: "16px", background: "rgba(59,130,246,0.04)", borderRadius: "10px", borderLeft: "2px solid var(--blue)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                            <Lightbulb size={14} color="var(--blue)" />
                            <h5 style={{ fontSize: "12px", fontWeight: 700, color: "var(--blue)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>Strategic Narrative</h5>
                          </div>
                          <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>{result.ai_analysis.hook_analysis}</p>
                        </div>
                      )}
                      
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                        {result.ai_analysis.why_it_worked && result.ai_analysis.why_it_worked.length > 0 && (
                          <div style={{ padding: "20px", background: "rgba(255,255,255,0.02)", borderRadius: "12px", border: "1px solid var(--border)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "16px" }}>
                              <CheckCircle size={14} color="var(--green)" />
                              <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Positive Indicators</div>
                            </div>
                            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "10px", padding: 0, margin: 0 }}>
                              {result.ai_analysis.why_it_worked.map((item, i) => (
                                <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)", paddingLeft: "22px", position: "relative", lineHeight: 1.5 }}>
                                  <span style={{ position: "absolute", left: 0, top: "2px", color: "var(--green)" }}>+</span>{item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {result.ai_analysis.improvement_suggestions && result.ai_analysis.improvement_suggestions.length > 0 && (
                          <div style={{ padding: "20px", background: "rgba(244,63,94,0.03)", borderRadius: "12px", border: "1px solid rgba(244,63,94,0.15)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "16px" }}>
                              <AlertTriangle size={14} color="var(--red)" />
                              <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--red)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Required Fixes</div>
                            </div>
                            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "10px", padding: 0, margin: 0 }}>
                              {result.ai_analysis.improvement_suggestions.map((item, i) => (
                                <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)", paddingLeft: "22px", position: "relative", lineHeight: 1.5 }}>
                                  <span style={{ position: "absolute", left: 0, top: "2px", color: "var(--red)" }}>→</span>{item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                      {result.ai_analysis.performance_summary && (
                        <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.7, margin: 0 }}>{result.ai_analysis.performance_summary}</p>
                      )}
                      {result.ai_analysis.benchmark_comparison && (
                        <div style={{ padding: "16px", background: "rgba(59,130,246,0.04)", borderRadius: "10px", borderLeft: "2px solid var(--blue)" }}>
                          <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--blue)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Benchmark Analysis</div>
                          <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>{result.ai_analysis.benchmark_comparison}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

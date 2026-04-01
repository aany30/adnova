"use client";
import { useState, useRef } from "react";
import { 
  Sparkles, Target, Film, Mic, CheckCircle, AlertTriangle, 
  BrainCircuit, Users, MapPin, Tv, Tag, Activity, Lightbulb, UserCheck, Languages,
  PenTool, MessageSquareText, Video
} from "lucide-react";

let API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
if (API.endsWith('/')) API = API.slice(0, -1);
if (!API.endsWith('/api')) API = `${API}/api`;

interface ScoreWithReason {
  score: number;
  reasoning: string;
}

interface GeneratedHook {
  hook_script: string;
  psychological_angle: string;
}

interface GeneratedAdCopy {
  copy_text: string;
  copy_angle: string;
}

interface CampaignResult {
  detected_product: string;
  creative_type: string;
  detected_brand_stage: string;
  overall_ad_readiness: string;
  overall_ad_readiness_reasoning: string;
  creative_meaning_analysis: string;
  hook_score: number;
  hook_type: string;
  hook_score_reasoning: string;
  hook_timing: string;
  strengths: string[];
  weaknesses: string[];
  improvement_suggestions: string[];
  creative_format_score: {
    visual_clarity: ScoreWithReason;
    brand_visibility: ScoreWithReason;
    emotion_factor: ScoreWithReason;
    india_relevance: ScoreWithReason;
  };
  targeting: {
    recommended_age_range: string;
    gender: string;
    psychographic_profile: string;
    top_interests: string[];
    interest_reasoning: string;
    behaviors: string[];
    behavior_reasoning: string;
    city_tiers: string[];
    recommended_cities: string[];
    city_reasoning: string;
    excluded_audiences: string[];
    language_recommendation: string;
  };
  placement_recommendation: string;
  generated_hooks: GeneratedHook[];
  generated_ad_copy: GeneratedAdCopy[];
}

interface OptimizerResponse {
  is_video: boolean;
  frames_analyzed: number;
  transcript: string | null;
  ai_analysis: CampaignResult;
}

export default function CampaignOptimizer() {
  const [creativeFile, setCreativeFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OptimizerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const ai = result?.ai_analysis;

  // True only when the backend returned the hardcoded fallback because OpenAI
  // was unreachable — NOT when a real creative legitimately scores zero.
  const isApiError = !!ai && ai.detected_product?.toLowerCase().startsWith("unable to detect");

  const handleFileChange = (file: File) => {
    setCreativeFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    if (result) setResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileChange(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!creativeFile) return;

    setLoading(true);
    setError(null);

    const body = new FormData();
    body.append("creative", creativeFile);

    try {
      const res = await fetch(`${API}/campaign-optimizer`, { method: "POST", body });
      if (!res.ok) {
        let errorMsg = "Analysis failed";
        try {
          const err = await res.json();
          errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail) || errorMsg;
        } catch (e) {
          errorMsg = `Server error (${res.status}): ${res.statusText}`;
        }
        throw new Error(errorMsg);
      }
      const data = await res.json();
      setResult(data);
    } catch (err: unknown) {
      console.error("Fetch error:", err);
      const msg = err instanceof Error ? err.message : "Connection failed (v2)";
      setError(`[Deployment v2] ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const readinessColor = (r: string) => {
    if (r === "Ready to Scale") return "var(--green)";
    if (r === "Needs Minor Edits") return "var(--gold)";
    return "var(--red)";
  };

  const hookColor = (score: number) => {
    if (score >= 80) return "var(--green)";
    if (score >= 60) return "var(--gold)";
    return "var(--red)";
  };

  const ScoreRow = ({ label, data, color }: { label: string; data: ScoreWithReason; color: string }) => {
    const [open, setOpen] = useState(false);
    return (
      <div style={{ marginBottom: "16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px", cursor: "pointer" }} onClick={() => setOpen(!open)}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>{label}</span>
            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{open ? "▲" : "▼"}</span>
          </div>
          <span style={{ fontSize: "15px", fontWeight: 800, color }}>{data.score}/10</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${data.score * 10}%`, background: color }} />
        </div>
        {open && (
          <div style={{ marginTop: "8px", padding: "10px", background: "rgba(255,255,255,0.02)", borderRadius: "6px", fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5, borderLeft: `2px solid ${color}` }}>
            {data.reasoning}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ padding: "40px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "40px", textAlign: "center" }} className="animate-in">
        <div className="badge" style={{ marginBottom: "16px", background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
          <Sparkles size={12} style={{ marginRight: "4px" }} />
          Proprietary Analysis
        </div>
        <h1 style={{ fontSize: "36px", fontWeight: 900, letterSpacing: "-0.04em", marginBottom: "12px" }}>
          Creative <span className="gradient-text">Intelligence</span>
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "15px", maxWidth: "600px", margin: "0 auto" }}>
          Upload your ad creative → The intelligence engine breaks down your storytelling, uncovers emotional hooks, and provides exact Meta targeting recommendations.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: "32px", alignItems: "start" }}>
        
        {/* Upload Column */}
        <div className="glass-card" style={{ padding: "32px", position: "sticky", top: "30px" }}>
          <form onSubmit={handleSubmit}>
            <div
              className="upload-zone"
              style={{ padding: "40px 24px" }}
              onDrop={handleDrop}
              onDragOver={e => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
            >
              <input ref={fileRef} type="file" accept="image/*,video/*" style={{ display: "none" }} onChange={e => { const f = e.target.files?.[0]; if (f) handleFileChange(f); }} />
              {previewUrl ? (
                <div>
                  {creativeFile?.type.startsWith("video") ? (
                    <video src={previewUrl} style={{ width: "100%", maxHeight: "200px", objectFit: "cover", borderRadius: "10px", border: "1px solid var(--border)" }} controls muted />
                  ) : (
                    <img src={previewUrl} alt="Creative preview" style={{ width: "100%", maxHeight: "200px", objectFit: "cover", borderRadius: "10px", border: "1px solid var(--border)" }} />
                  )}
                  <p style={{ fontSize: "13px", color: "var(--green)", marginTop: "16px", fontWeight: 600 }}>File attached successfully</p>
                </div>
              ) : (
                <>
                  <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px", color: "var(--text-muted)" }}>
                    <Film size={34} strokeWidth={1.5} />
                  </div>
                  <h3 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>Drag & drop creative</h3>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>Supports MP4, MOV, JPG, PNG</p>
                </>
              )}
            </div>

            {error && (
              <div style={{ marginTop: "20px", padding: "14px 16px", background: "var(--red-muted)", border: "1px solid rgba(244,63,94,0.2)", borderRadius: "10px", color: "var(--red)", fontSize: "13px", display: "flex", gap: "10px", alignItems: "flex-start" }}>
                <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
                <span>{error}</span>
              </div>
            )}

            <button type="submit" className="btn-primary" style={{ width: "100%", marginTop: "24px", padding: "16px", justifyContent: "center", fontSize: "15px" }} disabled={!creativeFile || loading}>
              {loading ? (
                <>
                  <svg className="animate-spin" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                  Processing Structure…
                </>
              ) : (
                <>
                  <BrainCircuit size={18} />
                  Run Intelligence Scan
                </>
              )}
            </button>
          </form>

          {loading && (
            <p style={{ fontSize: "12px", color: "var(--text-muted)", textAlign: "center", marginTop: "16px", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
              <Activity size={14} className="animate-pulse" />
              {creativeFile?.type.startsWith("video") ? "Processing multi-frame video structure…" : "Analyzing creative structure…"}
            </p>
          )}
        </div>

        {/* Results */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {!result && !loading && (
            <div className="glass-card" style={{ padding: "100px 40px", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <BrainCircuit size={48} style={{ color: "var(--text-muted)", opacity: 0.5, marginBottom: "24px" }} strokeWidth={1} />
              <h3 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px" }}>Awaiting Creative</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "15px", maxWidth: "340px", lineHeight: 1.5 }}>Upload a creative to get deep contextual analysis, precise Meta targeting, and actionable feedback.</p>
            </div>
          )}

          {loading && (
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <div className="glass-card skeleton" style={{ height: "160px" }} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
                <div className="glass-card skeleton" style={{ height: "240px" }} />
                <div className="glass-card skeleton" style={{ height: "240px" }} />
              </div>
            </div>
          )}

          {result && ai && isApiError && (
            <div className="glass-card animate-in" style={{ padding: "48px 40px", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "20px" }}>
              <div style={{ width: "56px", height: "56px", borderRadius: "14px", background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.25)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <AlertTriangle size={26} color="var(--red)" />
              </div>
              <div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "10px" }}>OpenAI API Not Configured</div>
                <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.7, maxWidth: "400px", margin: "0 auto" }}>
                  The backend could not reach OpenAI. Add your key to <code style={{ background: "rgba(255,255,255,0.06)", padding: "2px 6px", borderRadius: "4px", fontSize: "13px" }}>backend/.env</code> and restart the server.
                </p>
                <div style={{ marginTop: "20px", padding: "12px 16px", background: "rgba(244,63,94,0.06)", border: "1px solid rgba(244,63,94,0.15)", borderRadius: "8px", fontFamily: "monospace", fontSize: "13px", color: "var(--text-secondary)", display: "inline-block" }}>
                  OPENAI_API_KEY=sk-...
                </div>
              </div>
            </div>
          )}

          {result && ai && !isApiError && (
            <div className="animate-in" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

              {/* Header Banner - Streamlined */}
              <div className="glass-card" style={{ padding: "0", overflow: "hidden" }}>
                <div style={{ padding: "28px 32px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.01)" }}>
                  <div>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--blue)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>Core Message Detected</div>
                    <div style={{ fontSize: "22px", fontWeight: 800, color: "var(--text-primary)", marginBottom: "4px" }}>{ai.detected_product}</div>
                    <div style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>{ai.creative_type} · {ai.detected_brand_stage}</div>
                  </div>
                  <div style={{ textAlign: "right", borderLeft: "1px solid var(--border)", paddingLeft: "32px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>Verdict</div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "flex-end" }}>
                      <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: readinessColor(ai.overall_ad_readiness) }} />
                      <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)" }}>{ai.overall_ad_readiness}</div>
                    </div>
                  </div>
                </div>
                
                <div style={{ padding: "24px 32px", background: "linear-gradient(to right, rgba(59,130,246,0.02), transparent)" }}>
                  <p style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: 1.7, margin: 0, fontStyle: "italic" }}>"{ai.creative_meaning_analysis}"</p>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.6, marginTop: "16px", borderTop: "1px dashed var(--border)", paddingTop: "16px" }}>
                    <strong style={{ color: "var(--text-secondary)" }}>Reasoning:</strong> {ai.overall_ad_readiness_reasoning}
                  </p>
                </div>

                {result.is_video && (
                  <div style={{ padding: "16px 32px", background: "rgba(0,0,0,0.2)", borderTop: "1px solid var(--border)", display: "flex", alignItems: "flex-start", gap: "24px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <Film size={14} color="var(--blue)" />
                      <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500 }}>Video structure analyzed</span>
                    </div>
                    {result.transcript && (
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <Mic size={14} color="var(--gold-light)" />
                          <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500 }}>Deep narrative scan complete</span>
                        </div>
                        <div style={{ marginTop: "10px" }}>
                          <button onClick={() => setTranscriptOpen(o => !o)} style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-primary)", fontSize: "11px", cursor: "pointer", padding: "6px 12px", borderRadius: "6px", fontWeight: 600, transition: "0.2s" }} className="hover:bg-white/10">
                            {transcriptOpen ? "Hide Detected Dialogue" : "View Detected Dialogue"}
                          </button>
                          {transcriptOpen && (
                            <div style={{ marginTop: "12px", padding: "16px", background: "rgba(0,0,0,0.3)", borderRadius: "8px", fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.7, fontStyle: "italic", borderLeft: "2px solid var(--gold-light)" }}>
                              "{result.transcript}"
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Core Scores */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
                <div className="glass-card" style={{ padding: "32px", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                        <Target size={14} color="var(--text-muted)" />
                        <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>The Hook Score</div>
                      </div>
                      <span className="badge" style={{ fontSize: "11px", background: "var(--blue-muted)", color: "var(--gold-light)", border: "1px solid rgba(96,165,250,0.2)" }}>{ai.hook_type}</span>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "48px", fontWeight: 900, color: hookColor(ai.hook_score), lineHeight: 1, letterSpacing: "-0.03em" }}>{ai.hook_score}</div>
                      <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "6px" }}>/100</div>
                    </div>
                  </div>
                  <div style={{ padding: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "10px", borderLeft: `2px solid ${hookColor(ai.hook_score)}`, flex: 1 }}>
                    <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>{ai.hook_score_reasoning}</p>
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "16px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Activity size={12} />
                    {ai.hook_timing}
                  </div>
                </div>

                <div className="glass-card" style={{ padding: "32px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "24px" }}>
                    <Activity size={14} color="var(--text-muted)" />
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Creative Breakdown</div>
                  </div>
                  <ScoreRow label="Visual Clarity" data={ai.creative_format_score.visual_clarity} color="var(--gold-light)" />
                  <ScoreRow label="Brand Visibility" data={ai.creative_format_score.brand_visibility} color="var(--purple)" />
                  <ScoreRow label="Emotion Factor" data={ai.creative_format_score.emotion_factor} color="#f59e0b" />
                  <ScoreRow label="India Relevance" data={ai.creative_format_score.india_relevance} color="var(--green)" />
                </div>
              </div>

              {/* Dynamic Targeting - Redesigned to be spacious */}
              <div className="glass-card" style={{ padding: "36px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "32px", paddingBottom: "24px", borderBottom: "1px solid var(--border)" }}>
                  <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "var(--gold-muted)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Target size={20} color="var(--gold-light)" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: "20px", color: "var(--text-primary)" }}>Dynamic Meta Targeting</div>
                    <div style={{ fontSize: "14px", color: "var(--text-muted)", marginTop: "2px" }}>Custom audiences generated specifically for this creative's message</div>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px" }}>
                  {/* Left Column: Who & Where */}
                  <div>
                    {/* The Who */}
                    <div style={{ marginBottom: "36px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                        <BrainCircuit size={14} color="var(--purple)" />
                        <h4 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>The Audience (Demographics)</h4>
                      </div>
                      <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "16px", padding: "16px", background: "rgba(168,85,247,0.04)", borderRadius: "10px", borderLeft: "2px solid var(--purple)" }}>
                        {ai.targeting.psychographic_profile}
                      </p>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                        <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px", color: "var(--text-muted)" }}>
                            <Users size={12} /> <span style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase" }}>Age</span>
                          </div>
                          <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>{ai.targeting.recommended_age_range}</div>
                        </div>
                        <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px", color: "var(--text-muted)" }}>
                            <UserCheck size={12} /> <span style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase" }}>Gender</span>
                          </div>
                          <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>{ai.targeting.gender}</div>
                        </div>
                      </div>
                    </div>

                    {/* The Where */}
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                        <MapPin size={14} color="var(--red)" />
                        <h4 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>High-Value Locations</h4>
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "16px" }}>
                        {ai.targeting.recommended_cities.map((city, idx) => (
                          <span key={idx} className="badge" style={{ fontSize: "12px", padding: "6px 12px", background: "rgba(244,63,94,0.1)", color: "var(--red)", border: "1px solid rgba(244,63,94,0.2)" }}>{city}</span>
                        ))}
                      </div>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{ai.targeting.city_reasoning}</p>
                    </div>
                  </div>

                  {/* Right Column: Interests & Behaviors */}
                  <div>
                    <div style={{ marginBottom: "36px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                        <Tag size={14} color="var(--green)" />
                        <h4 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>Direct Interests & Brands</h4>
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "16px" }}>
                        {ai.targeting.top_interests.map((interest, idx) => (
                          <span key={idx} className="tag" style={{ color: "var(--text-primary)", borderColor: "var(--border)", background: "rgba(255,255,255,0.03)", padding: "6px 12px", fontSize: "13px" }}>{interest}</span>
                        ))}
                      </div>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{ai.targeting.interest_reasoning}</p>
                    </div>

                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                        <Activity size={14} color="var(--gold-light)" />
                        <h4 style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>Action Behaviors</h4>
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "16px" }}>
                        {ai.targeting.behaviors.map((b, idx) => (
                          <span key={idx} className="tag" style={{ color: "var(--gold-light)", borderColor: "rgba(96,165,250,0.2)", background: "rgba(96,165,250,0.05)", padding: "6px 12px", fontSize: "13px" }}>{b}</span>
                        ))}
                      </div>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{ai.targeting.behavior_reasoning}</p>
                    </div>

                    <div style={{ marginTop: "32px", padding: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "10px", border: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px", color: "var(--text-muted)" }}>
                        <Languages size={14} /> <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>Language Protocol</span>
                      </div>
                      <div style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>{ai.targeting.language_recommendation}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Actionable Feedback */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
                <div className="glass-card" style={{ padding: "32px", borderTop: "2px solid var(--green)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "24px" }}>
                    <CheckCircle size={16} color="var(--green)" />
                    <div style={{ fontSize: "12px", fontWeight: 800, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>What's Working Correctly</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    {ai.strengths.map((s, i) => (
                      <div key={i} style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                        <div style={{ color: "var(--green)", marginTop: "2px" }}><CheckCircle size={14} /></div>
                        <div style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{s}</div>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="glass-card" style={{ padding: "32px", border: "1px solid rgba(244,63,94,0.2)", borderTop: "2px solid var(--red)", background: "linear-gradient(135deg, rgba(244,63,94,0.02), rgba(0,0,0,0))" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "24px" }}>
                    <AlertTriangle size={16} color="var(--red)" />
                    <div style={{ fontSize: "12px", fontWeight: 800, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>High-Impact Fixes</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    {ai.improvement_suggestions.map((s, i) => (
                      <div key={i} style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                        <div style={{ color: "var(--red)", marginTop: "2px" }}><AlertTriangle size={14} /></div>
                        <div style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6 }}>{s}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Generative Expansion (Hooks & Copy) */}
              {(ai.generated_hooks?.length > 0 || ai.generated_ad_copy?.length > 0) && (
                <div className="glass-card" style={{ padding: "40px", borderTop: "2px solid var(--blue)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "32px", paddingBottom: "24px", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(59,130,246,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <PenTool size={20} color="var(--blue)" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: "20px", color: "var(--text-primary)" }}>AI Generated Variations</div>
                      <div style={{ fontSize: "14px", color: "var(--text-muted)", marginTop: "2px" }}>Ready-to-use concepts formulated to fix current weaknesses and boost conversion rates</div>
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "40px" }}>
                    {/* Left: Video Hooks */}
                    {ai.generated_hooks?.length > 0 && (
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "20px" }}>
                          <Video size={16} color="var(--gold-light)" />
                          <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>New 3-Second Hooks</h4>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                          {ai.generated_hooks.map((hook, i) => (
                            <div key={i} style={{ padding: "20px", background: "rgba(255,255,255,0.02)", borderRadius: "12px", border: "1px solid var(--border)" }}>
                              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, margin: "0 0 12px 0", fontStyle: "italic" }}>
                                "{hook.hook_script}"
                              </p>
                              <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--gold-light)", background: "rgba(245,158,11,0.1)", padding: "6px 10px", borderRadius: "6px", display: "inline-block" }}>
                                Angle: {hook.psychological_angle}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Right: Ad Copy */}
                    {ai.generated_ad_copy?.length > 0 && (
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "20px" }}>
                          <MessageSquareText size={16} color="var(--purple)" />
                          <h4 style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>Primary Text Combinations</h4>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                          {ai.generated_ad_copy.map((copy, i) => (
                            <div key={i} style={{ padding: "20px", background: "rgba(255,255,255,0.02)", borderRadius: "12px", border: "1px solid var(--border)" }}>
                              <span className="badge" style={{ fontSize: "10px", background: "rgba(168,85,247,0.1)", color: "var(--purple)", border: "1px solid rgba(168,85,247,0.2)", marginBottom: "12px", display: "inline-block" }}>
                                {copy.copy_angle} Format
                              </span>
                              <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0, whiteSpace: "pre-wrap" }}>
                                {copy.copy_text}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </div>
    </div>
  );
}

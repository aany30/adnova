"use client";

import { useRef, useState } from "react";
import { fetchWithAuth } from "@/lib/auth";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle,
  Film,
  Languages,
  Lightbulb,
  MapPin,
  MessageSquareText,
  Mic,
  PenTool,
  Sparkles,
  Tag,
  Target,
  Tv,
  UserCheck,
  Users,
  Video,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://adnova-production.up.railway.app/api";

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

interface TargetingTestAngle {
  name: string;
  audience?: string;
  age_range?: string;
  gender?: string;
  locations?: string[];
  interests?: string[];
  behaviors?: string[];
  placements?: string[];
  exclusions?: string[];
  copy_angle?: string;
  why_test?: string;
  evidence?: string;
  confidence?: number;
}

interface RecommendationItem {
  name: string;
  confidence?: number;
  evidence?: string;
  catalog_match?: boolean;
}

interface AgentTestAngle {
  name: string;
  setup: string;
  hypothesis: string;
  evidence?: string;
  copy_angle?: string;
}

interface AudienceClusterItem {
  buyer_type?: string;
  targeting_cue?: string;
  copy_angle?: string;
  evidence?: string;
}

interface UGCScript {
  script_title?: string;
  opening_visual?: string;
  voiceover?: string;
  cta?: string;
  target_audience?: string;
}

interface AgentAnalysis {
  evidence_synthesizer?: {
    observed_timeline?: { timestamp: string; observation: string; marketing_signal: string; conversion_issue_or_opportunity?: string }[];
    product_cues?: string[];
    cta_cues?: string[];
    missing_evidence?: string[];
  };
  meta_targeting_agent?: {
    primary_persona?: string;
    demographics?: string;
    interests_to_choose?: string[];
    behaviors_to_choose?: string[];
    locations_to_choose?: string[];
    exclusions?: string[];
    placements?: string[];
    testing_angles?: AgentTestAngle[];
    reasoning?: string;
  };
  hook_agent?: {
    score?: number;
    hook_type?: string;
    opening_diagnosis?: string;
    fix?: string;
  };
  virality_agent?: {
    score?: number;
    scroll_stop_factor?: string;
    shareability?: string;
    trend_fit?: string;
  };
  caption_copy_agent?: {
    primary_caption?: string;
    headline?: string;
    cta?: string;
    copy_angles?: string[];
  };
  creative_diagnosis_agent?: {
    priority_fixes?: string[];
    keep?: string[];
    risk?: string;
  };
}

interface CampaignResult {
  api_error?: boolean;
  parse_error?: boolean;
  fallback_used?: boolean;
  model_profile?: string;
  model_used?: string;
  detected_product: string;
  creative_intent?: string;
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
    audience_persona?: string;
    top_interests: string[];
    interest_reasoning: string;
    targeting_rationale?: string;
    behaviors: string[];
    behavior_reasoning: string;
    city_tiers: string[];
    recommended_cities: string[];
    city_reasoning: string;
    excluded_audiences: string[];
    language_recommendation: string;
    testing_angles?: TargetingTestAngle[];
    targeting_recommendations?: {
      demographics?: RecommendationItem;
      gender?: RecommendationItem;
      interests?: RecommendationItem[];
      behaviors?: RecommendationItem[];
      locations?: RecommendationItem[];
      placements?: RecommendationItem[];
      exclusions?: RecommendationItem[];
    };
  };
  placement_recommendation: string;
  generated_hooks: GeneratedHook[];
  generated_ad_copy: GeneratedAdCopy[];
  agent_analysis?: AgentAnalysis;
  strategy_depth?: {
    funnel_stage?: string;
    buyer_intent_level?: string;
    offer_clarity_score?: number;
    cta_strength_score?: number;
    landing_page_risk?: string;
    audience_clusters?: {
      premium_buyers?: (string | AudienceClusterItem)[];
      value_buyers?: (string | AudienceClusterItem)[];
      trend_buyers?: (string | AudienceClusterItem)[];
      problem_aware_buyers?: (string | AudienceClusterItem)[];
      gift_buyers?: (string | AudienceClusterItem)[];
    };
    next_tests?: TargetingTestAngle[];
  };
  generated_headlines?: string[];
  cta_variants?: string[];
  overlay_text_ideas?: string[];
  ugc_scripts?: UGCScript[];
  unsupported_assumptions?: string[];
  analysis_quality?: {
    schema_validated?: boolean;
    catalog_grounded?: boolean;
    recommendation_count?: number;
    unsupported_assumption_count?: number;
  };
}

interface OptimizerResponse {
  is_video: boolean;
  frames_analyzed: number;
  transcript: string | null;
  ai_analysis: CampaignResult;
  quota?: {
    daily_limit: number;
    monthly_limit: number;
    daily_used: number;
    monthly_used: number;
    daily_remaining: number;
    monthly_remaining: number;
    daily_reset_at: string;
    monthly_reset_at: string;
  };
}

function safeList(items?: string[]) {
  return (items || []).filter(Boolean);
}

function scoreColor(score: number) {
  if (score >= 80) return "var(--green)";
  if (score >= 60) return "var(--gold)";
  return "var(--red)";
}

function clusterTitle(item: string | AudienceClusterItem) {
  return typeof item === "string" ? item : item.buyer_type || "Audience cluster";
}

function clusterDetail(item: string | AudienceClusterItem) {
  if (typeof item === "string") return "";
  return [item.targeting_cue, item.copy_angle, item.evidence].filter(Boolean).join(" • ");
}

function SectionHeader({
  icon,
  eyebrow,
  title,
  subtitle,
}: {
  icon: React.ReactNode;
  eyebrow?: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="co-section-header">
      <div className="co-section-icon">{icon}</div>
      <div>
        {eyebrow && <div className="co-eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
    </div>
  );
}

function ChipList({
  items,
  tone = "neutral",
  empty = "No specific picks returned",
}: {
  items?: string[];
  tone?: "neutral" | "blue" | "green" | "red" | "gold";
  empty?: string;
}) {
  const values = safeList(items);
  if (!values.length) {
    return <p className="co-muted">{empty}</p>;
  }

  return (
    <div className="co-chip-list">
      {values.map((item, index) => (
        <span key={`${item}-${index}`} className={`co-chip co-chip-${tone}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function MiniCard({
  icon,
  label,
  value,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  value?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="co-mini-card">
      <div className="co-mini-label">
        {icon}
        <span>{label}</span>
      </div>
      {value && <div className="co-mini-value">{value}</div>}
      {children}
    </div>
  );
}

function ScoreRow({ label, data, color }: { label: string; data?: ScoreWithReason; color: string }) {
  const [open, setOpen] = useState(false);
  const score = data?.score || 0;

  return (
    <div className="co-score-row">
      <button type="button" onClick={() => setOpen(!open)}>
        <span>{label}</span>
        <strong style={{ color }}>{score}/10</strong>
      </button>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${score * 10}%`, background: color }} />
      </div>
      {open && <p>{data?.reasoning || "No reasoning returned."}</p>}
    </div>
  );
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
  const targeting = ai?.targeting;
  const agents = ai?.agent_analysis;
  const metaAgent = agents?.meta_targeting_agent;
  const evidence = agents?.evidence_synthesizer;
  const hookAgent = agents?.hook_agent;
  const viralityAgent = agents?.virality_agent;
  const copyAgent = agents?.caption_copy_agent;
  const diagnosisAgent = agents?.creative_diagnosis_agent;
  const audienceClusters = ai?.strategy_depth?.audience_clusters;
  const clusterEntries = audienceClusters
    ? [
        ["Premium buyers", audienceClusters.premium_buyers],
        ["Value buyers", audienceClusters.value_buyers],
        ["Trend buyers", audienceClusters.trend_buyers],
        ["Problem-aware buyers", audienceClusters.problem_aware_buyers],
        ["Gift buyers", audienceClusters.gift_buyers],
      ].filter((entry): entry is [string, (string | AudienceClusterItem)[]] => Array.isArray(entry[1]) && entry[1].length > 0)
    : [];

  const isApiError = !!ai && ai.api_error === true;
  const isParseError = !!ai && ai.parse_error === true;

  const handleFileChange = (file: File) => {
    if (file.type.startsWith("video/")) {
      const url = URL.createObjectURL(file);
      const video = document.createElement("video");
      video.preload = "metadata";
      video.onloadedmetadata = () => {
        if (video.duration > 60) {
          setError("Video exceeds maximum allowed length of 1 minute. Please upload a shorter creative.");
          setCreativeFile(null);
          setPreviewUrl(null);
          if (result) setResult(null);
          URL.revokeObjectURL(url);
        } else {
          setError(null);
          setCreativeFile(file);
          setPreviewUrl(url);
          if (result) setResult(null);
        }
      };
      video.onerror = () => {
        setError("Invalid video file.");
        URL.revokeObjectURL(url);
      };
      video.src = url;
    } else {
      setError(null);
      setCreativeFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      if (result) setResult(null);
    }
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
          if (err.code === "QUERY_LIMIT_EXCEEDED" && err.quota) {
            errorMsg = `Query limit reached. Daily remaining: ${err.quota.daily_remaining}/${err.quota.daily_limit}. Monthly remaining: ${err.quota.monthly_remaining}/${err.quota.monthly_limit}.`;
          } else {
            errorMsg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || errorMsg;
          }
        } catch {
          errorMsg = `Server error (${res.status}): ${res.statusText}`;
        }
        throw new Error(errorMsg);
      }

      const data: OptimizerResponse = await res.json();
      setResult(data);

      fetchWithAuth("/activity/log", {
        method: "POST",
        body: JSON.stringify({
          module: "campaign_optimizer",
          action: "analyze",
          input_data: {
            file_name: creativeFile.name,
            file_type: creativeFile.type,
            file_size_kb: Math.round(creativeFile.size / 1024),
          },
          result_summary: data.ai_analysis?.detected_product
            ? `${data.ai_analysis.detected_product} | ${data.ai_analysis.overall_ad_readiness} | Hook: ${data.ai_analysis.hook_score}/100`
            : null,
        }),
      }).catch(() => {});
    } catch (err: unknown) {
      console.error("Fetch error:", err);
      const msg = err instanceof Error ? err.message : "Connection failed";
      setError(`[Local] ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="co-page">
      <section className="co-hero animate-in">
        <div className="badge co-hero-badge">
          <Sparkles size={12} />
          Meta Targeting Intelligence
        </div>
        <h1>
          Creative Intelligence <span className="gradient-text">for Meta Ads</span>
        </h1>
        <p>
          Upload one ad creative. The local scanner extracts video evidence, then the AI turns it into targeting, hooks, captions, and launch decisions.
        </p>
      </section>

      <section className="co-upload-shell">
        <div className="glass-card co-upload-card">
          <form onSubmit={handleSubmit}>
            <div
              className="upload-zone co-upload-zone"
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                accept="image/*,video/*"
                style={{ display: "none" }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileChange(file);
                }}
              />
              {previewUrl ? (
                <div>
                  {creativeFile?.type.startsWith("video") ? (
                    <video src={previewUrl} className="co-preview-media" controls muted />
                  ) : (
                    <img src={previewUrl} alt="Creative preview" className="co-preview-media" />
                  )}
                  <p className="co-file-name">{creativeFile?.name}</p>
                </div>
              ) : (
                <div className="co-empty-upload">
                  <Film size={34} strokeWidth={1.5} />
                  <h3>Drop creative here</h3>
                  <p>MP4, MOV, JPG, PNG supported</p>
                </div>
              )}
            </div>

            {error && (
              <div className="co-error">
                <AlertTriangle size={16} />
                <span>{error}</span>
              </div>
            )}

            <button type="submit" className="btn-primary co-run-button" disabled={!creativeFile || loading}>
              {loading ? (
                <>
                  <svg className="animate-spin" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                  Running agent scan
                </>
              ) : (
                <>
                  <BrainCircuit size={18} />
                  Run Intelligence Scan
                </>
              )}
            </button>
          </form>
        </div>

      </section>

      {result?.quota && (
        <section className="glass-card co-video-proof">
          <div className="co-scan-item">
            <Activity size={16} />
            <div>
              <strong>Quota remaining</strong>
              <span>{result.quota.daily_remaining} daily scans and {result.quota.monthly_remaining} monthly scans left</span>
            </div>
          </div>
          {ai?.fallback_used && (
            <div className="co-scan-item">
              <AlertTriangle size={16} />
              <div>
                <strong>Fallback used</strong>
                <span>The primary model failed or returned malformed JSON, so AdNova used the configured fallback.</span>
              </div>
            </div>
          )}
        </section>
      )}

      {!result && !loading && (
        <section className="glass-card co-empty-state">
          <BrainCircuit size={48} strokeWidth={1} />
          <h3>Awaiting Creative</h3>
          <p>Upload an ad to generate a Meta targeting plan, hook score, creative diagnosis, and copy variants.</p>
        </section>
      )}

      {loading && (
        <section className="co-loading-grid">
          <div className="glass-card skeleton" />
          <div className="glass-card skeleton" />
          <div className="glass-card skeleton" />
          <div className="glass-card skeleton" />
        </section>
      )}

      {result && ai && isApiError && (
        <section className="glass-card co-error-state animate-in">
          <AlertTriangle size={26} color="var(--red)" />
          <h3>OpenAI API Not Configured</h3>
          <p>The backend could not reach OpenAI. Add your key to backend/.env and restart the server.</p>
        </section>
      )}

      {result && ai && isParseError && (
        <section className="glass-card co-error-state animate-in">
          <Film size={26} color="var(--gold)" />
          <h3>Not an Ad Creative</h3>
          <p>Upload a clear Facebook/Instagram ad image or video to receive targeting and creative scoring.</p>
        </section>
      )}

      {result && ai && !isApiError && !isParseError && targeting && (
        <section className="co-results animate-in">
          <div className="glass-card co-summary-band">
            <div>
              <div className="co-eyebrow">{ai.creative_intent || "Core Message Detected"}</div>
              <h2>{ai.detected_product}</h2>
              <p>{ai.creative_meaning_analysis}</p>
            </div>
            <div className="co-summary-metrics">
              <MiniCard icon={<CheckCircle size={14} />} label="Verdict" value={ai.overall_ad_readiness} />
              <MiniCard icon={<Target size={14} />} label="Hook" value={`${ai.hook_score}/100`} />
              <MiniCard icon={<Activity size={14} />} label="Virality" value={`${viralityAgent?.score ?? 0}/100`} />
              <MiniCard icon={<Film size={14} />} label="Frames" value={result.is_video ? `${result.frames_analyzed}` : "1"} />
            </div>
          </div>

          {result.is_video && (
            <div className="glass-card co-video-proof">
              <div className="co-scan-item">
                <Film size={16} />
                <div>
                  <strong>Video structure analyzed</strong>
                  <span>{result.frames_analyzed} selected frames from local scan</span>
                </div>
              </div>
              {result.transcript && (
                <div className="co-transcript">
                  <button type="button" onClick={() => setTranscriptOpen((open) => !open)}>
                    <Mic size={14} />
                    {transcriptOpen ? "Hide detected dialogue" : "View detected dialogue"}
                  </button>
                  {transcriptOpen && <p>{`"${result.transcript}"`}</p>}
                </div>
              )}
            </div>
          )}

          <div className="glass-card co-targeting-plan">
            <SectionHeader
              icon={<Target size={22} color="var(--gold-light)" />}
              eyebrow="Main Agent"
              title="Meta Targeting Plan"
              subtitle="Practical ad-set decisions based on the creative evidence, not generic audience buckets."
            />

            <div className="co-persona-callout">
              <div>
                <span>Primary buyer persona</span>
                <strong>{metaAgent?.primary_persona || targeting.audience_persona || targeting.psychographic_profile}</strong>
              </div>
              <p>{metaAgent?.reasoning || targeting.targeting_rationale || targeting.interest_reasoning}</p>
            </div>

            <div className="co-target-grid">
              <MiniCard icon={<Users size={15} />} label="Who to target">
                <div className="co-mini-stack">
                  <strong>{targeting.recommended_age_range}</strong>
                  <span>{targeting.gender}</span>
                  <p>{metaAgent?.demographics || targeting.psychographic_profile}</p>
                </div>
              </MiniCard>

              <MiniCard icon={<MapPin size={15} />} label="Where to target">
                <ChipList items={metaAgent?.locations_to_choose || targeting.recommended_cities} tone="red" />
                <p className="co-muted">{targeting.city_reasoning}</p>
              </MiniCard>

              <MiniCard icon={<Tag size={15} />} label="Interests to choose">
                <ChipList items={metaAgent?.interests_to_choose || targeting.top_interests} tone="green" />
                <p className="co-muted">{targeting.interest_reasoning}</p>
              </MiniCard>

              <MiniCard icon={<Activity size={15} />} label="Behaviors to choose">
                <ChipList items={metaAgent?.behaviors_to_choose || targeting.behaviors} tone="blue" />
                <p className="co-muted">{targeting.behavior_reasoning}</p>
              </MiniCard>

              <MiniCard icon={<UserCheck size={15} />} label="Who to exclude">
                <ChipList items={metaAgent?.exclusions || targeting.excluded_audiences} tone="red" empty="No exclusions returned" />
              </MiniCard>

              <MiniCard icon={<Tv size={15} />} label="Placements">
                <ChipList items={metaAgent?.placements || [ai.placement_recommendation]} tone="gold" />
                <p className="co-muted">{ai.placement_recommendation}</p>
              </MiniCard>

              <MiniCard icon={<Languages size={15} />} label="Language">
                <div className="co-mini-value">{targeting.language_recommendation}</div>
              </MiniCard>
            </div>

            {(safeList(targeting.city_tiers).length > 0 || safeList(targeting.testing_angles?.map((angle) => angle.name)).length > 0 || safeList(metaAgent?.testing_angles?.map((angle) => angle.name)).length > 0) && (
              <div className="co-test-section">
                <h3>Ad-set tests to run</h3>
                <div className="co-test-grid">
	                  {(metaAgent?.testing_angles || []).map((angle, index) => (
	                    <div key={`${angle.name}-${index}`} className="co-test-card">
	                      <strong>{angle.name}</strong>
	                      <p>{angle.setup}</p>
	                      <span>{angle.hypothesis}</span>
	                      {angle.copy_angle && <em>{`Copy angle: ${angle.copy_angle}`}</em>}
	                      {angle.evidence && <em>{`Evidence: ${angle.evidence}`}</em>}
	                    </div>
	                  ))}
	                  {(!metaAgent?.testing_angles?.length ? targeting.testing_angles || [] : []).map((angle, index) => (
	                    <div key={`${angle.name}-${index}`} className="co-test-card">
	                      <strong>{angle.name}</strong>
	                      <p>{angle.audience}</p>
	                      <div className="co-test-detail-grid">
	                        {angle.age_range && <span>{`Age: ${angle.age_range}`}</span>}
	                        {angle.gender && <span>{`Gender: ${angle.gender}`}</span>}
	                        {safeList(angle.locations).length > 0 && <span>{`Locations: ${safeList(angle.locations).join(", ")}`}</span>}
	                        {safeList(angle.placements).length > 0 && <span>{`Placements: ${safeList(angle.placements).join(", ")}`}</span>}
	                      </div>
	                      <ChipList items={angle.interests} tone="green" />
	                      {safeList(angle.behaviors).length > 0 && <ChipList items={angle.behaviors} tone="blue" />}
	                      {safeList(angle.exclusions).length > 0 && <ChipList items={angle.exclusions} tone="red" />}
	                      <span>{angle.why_test}</span>
	                      {angle.copy_angle && <em>{`Copy angle: ${angle.copy_angle}`}</em>}
	                      {angle.evidence && <em>{`Evidence: ${angle.evidence}`}</em>}
	                    </div>
	                  ))}
	                </div>
	              </div>
	            )}

	            {clusterEntries.length > 0 && (
	              <div className="co-test-section">
	                <h3>Audience clusters and message angles</h3>
	                <div className="co-cluster-grid">
	                  {clusterEntries.map(([label, items]) => (
	                    <div key={label} className="co-cluster-card">
	                      <strong>{label}</strong>
	                      <div>
	                        {items.map((item, index) => (
	                          <p key={`${label}-${index}`}>
	                            <span>{clusterTitle(item)}</span>
	                            {clusterDetail(item) && <em>{clusterDetail(item)}</em>}
	                          </p>
	                        ))}
	                      </div>
	                    </div>
	                  ))}
	                </div>
	              </div>
	            )}
	          </div>

          <div className="co-agent-grid">
            <div className="glass-card co-agent-card">
              <SectionHeader icon={<Target size={20} color={scoreColor(ai.hook_score)} />} title="Hook Agent" subtitle={ai.hook_type} />
              <div className="co-agent-score" style={{ color: scoreColor(hookAgent?.score || ai.hook_score) }}>
                {hookAgent?.score || ai.hook_score}<span>/100</span>
              </div>
              <p>{hookAgent?.opening_diagnosis || ai.hook_score_reasoning}</p>
              <div className="co-agent-fix">{hookAgent?.fix || ai.hook_timing}</div>
            </div>

            <div className="glass-card co-agent-card">
              <SectionHeader icon={<Sparkles size={20} color={scoreColor(viralityAgent?.score || 0)} />} title="Virality Agent" subtitle="Scroll-stop and shareability" />
              <div className="co-agent-score" style={{ color: scoreColor(viralityAgent?.score || 0) }}>
                {viralityAgent?.score || 0}<span>/100</span>
              </div>
              <p>{viralityAgent?.scroll_stop_factor || "Virality scoring will appear on the next AI run."}</p>
              <div className="co-agent-fix">{viralityAgent?.trend_fit || viralityAgent?.shareability || "No trend fit returned."}</div>
            </div>

            <div className="glass-card co-agent-card">
              <SectionHeader icon={<Lightbulb size={20} color="var(--gold-light)" />} title="Creative Diagnosis" subtitle="Priority fixes" />
              <ChipList items={diagnosisAgent?.priority_fixes || ai.improvement_suggestions} tone="gold" />
              <p>{diagnosisAgent?.risk || ai.overall_ad_readiness_reasoning}</p>
            </div>
          </div>

          <div className="co-two-column">
            <div className="glass-card co-card-padding">
              <SectionHeader icon={<Activity size={20} color="var(--blue)" />} title="Creative Breakdown" />
              <ScoreRow label="Visual Clarity" data={ai.creative_format_score.visual_clarity} color="var(--gold-light)" />
              <ScoreRow label="Brand Visibility" data={ai.creative_format_score.brand_visibility} color="var(--purple)" />
              <ScoreRow label="Emotion Factor" data={ai.creative_format_score.emotion_factor} color="#f59e0b" />
              <ScoreRow label="India Relevance" data={ai.creative_format_score.india_relevance} color="var(--green)" />
            </div>

            <div className="glass-card co-card-padding">
              <SectionHeader icon={<BrainCircuit size={20} color="var(--purple)" />} title="Evidence Timeline" subtitle="What the agents used" />
              <div className="co-timeline">
	                {(evidence?.observed_timeline || []).map((item, index) => (
	                  <div key={`${item.timestamp}-${index}`}>
	                    <strong>{item.timestamp}</strong>
	                    <p>{item.observation}</p>
	                    <span>{item.marketing_signal}</span>
	                    {item.conversion_issue_or_opportunity && <em>{item.conversion_issue_or_opportunity}</em>}
	                  </div>
	                ))}
                {!evidence?.observed_timeline?.length && <p className="co-muted">Run the upgraded analysis to see timestamped evidence here.</p>}
              </div>
            </div>
          </div>

	              <div className="co-two-column">
            <div className="glass-card co-card-padding">
              <SectionHeader icon={<CheckCircle size={20} color="var(--green)" />} title="What Is Working" />
              <div className="co-list">
                {safeList(diagnosisAgent?.keep || ai.strengths).map((item, index) => (
                  <p key={`${item}-${index}`}><CheckCircle size={14} />{item}</p>
                ))}
              </div>
            </div>

            <div className="glass-card co-card-padding co-risk-card">
              <SectionHeader icon={<AlertTriangle size={20} color="var(--red)" />} title="High-Impact Fixes" />
              <div className="co-list">
                {safeList(ai.improvement_suggestions).map((item, index) => (
                  <p key={`${item}-${index}`}><AlertTriangle size={14} />{item}</p>
                ))}
              </div>
            </div>
          </div>

          {(ai.generated_hooks?.length > 0 || ai.generated_ad_copy?.length > 0 || copyAgent) && (
            <div className="glass-card co-creative-lab">
              <SectionHeader
                icon={<PenTool size={22} color="var(--blue)" />}
                eyebrow="Caption and Copy Agent"
                title="Creative Lab"
                subtitle="Launch-ready hooks, captions, and copy directions."
              />

              {copyAgent && (
                <div className="co-copy-highlight">
                  <div>
                    <span>Primary caption</span>
                    <p>{copyAgent.primary_caption}</p>
                  </div>
                  <div>
                    <span>Headline and CTA</span>
                    <strong>{copyAgent.headline}</strong>
                    <p>{copyAgent.cta}</p>
                  </div>
                </div>
              )}

              <div className="co-two-column">
                {ai.generated_hooks?.length > 0 && (
                  <div>
                    <h3 className="co-subhead"><Video size={16} /> New 3-second hooks</h3>
                    <div className="co-variant-list">
                      {ai.generated_hooks.map((hook, index) => (
                        <div key={`${hook.hook_script}-${index}`}>
                          <p>{`"${hook.hook_script}"`}</p>
                          <span>{hook.psychological_angle}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

	                {ai.generated_ad_copy?.length > 0 && (
	                  <div>
	                    <h3 className="co-subhead"><MessageSquareText size={16} /> Primary text combinations</h3>
	                    <div className="co-variant-list">
                      {ai.generated_ad_copy.map((copy, index) => (
                        <div key={`${copy.copy_text}-${index}`}>
                          <strong>{copy.copy_angle}</strong>
                          <p>{copy.copy_text}</p>
                        </div>
                      ))}
                    </div>
	                  </div>
	                )}
	              </div>

	              {(safeList(ai.generated_headlines).length > 0 || safeList(ai.cta_variants).length > 0 || safeList(ai.overlay_text_ideas).length > 0) && (
	                <div className="co-copy-assets-grid">
	                  <MiniCard icon={<MessageSquareText size={15} />} label="Headlines">
	                    <ChipList items={ai.generated_headlines} tone="blue" />
	                  </MiniCard>
	                  <MiniCard icon={<Target size={15} />} label="CTA variants">
	                    <ChipList items={ai.cta_variants} tone="gold" />
	                  </MiniCard>
	                  <MiniCard icon={<Film size={15} />} label="First-frame overlays">
	                    <ChipList items={ai.overlay_text_ideas} tone="green" />
	                  </MiniCard>
	                </div>
	              )}

	              {ai.ugc_scripts?.length ? (
	                <div className="co-test-section">
	                  <h3><Video size={16} /> UGC scripts</h3>
	                  <div className="co-test-grid">
	                    {ai.ugc_scripts.map((script, index) => (
	                      <div className="co-test-card" key={`${script.script_title}-${index}`}>
	                        <strong>{script.script_title || `UGC Script ${index + 1}`}</strong>
	                        {script.target_audience && <span>{script.target_audience}</span>}
	                        {script.opening_visual && <p>{`Opening: ${script.opening_visual}`}</p>}
	                        {script.voiceover && <p>{script.voiceover}</p>}
	                        {script.cta && <em>{`CTA: ${script.cta}`}</em>}
	                      </div>
	                    ))}
	                  </div>
	                </div>
	              ) : null}
	            </div>
	          )}
        </section>
      )}
    </main>
  );
}

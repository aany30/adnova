import os
import io
import json
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv
from data.facebook_india_targeting import get_targeting_context_string

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TARGETING_CONTEXT = get_targeting_context_string()


def _extract_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}

async def transcribe_video(video_bytes: bytes, filename: str = "video.mp4") -> str:
    """
    Transcribe audio from a video file using OpenAI Whisper.
    Extracts a small audio track first for efficiency.
    """
    from services.media_utils import extract_audio
    
    video_size_mb = len(video_bytes) / (1024 * 1024)
    
    # Use audio extraction ONLY for large videos (> 20MB) to stay safe & fast
    if video_size_mb > 20.0:
        print(f"Large video detected ({video_size_mb:.1f}MB). Extracting audio for Whisper efficiency.")
        audio_bytes = extract_audio(video_bytes)
        if audio_bytes:
            audio_to_send = audio_bytes
            ext = "mp3"
        else:
            print("Audio extraction failed, falling back to full video.")
            audio_to_send = video_bytes
            ext = "mp4"
    else:
        # Small video: send the whole thing as originally intended
        audio_to_send = video_bytes
        ext = "mp4"

    try:
        file_tuple = (filename.replace(".mp4", f".{ext}"), io.BytesIO(audio_to_send), f"video/{ext}" if ext == "mp4" else "audio/mp3")
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=file_tuple,
            language="hi",          # Hint Hindi first (handles Hinglish well)
            response_format="text",
            timeout=60.0
        )
        return str(response).strip()
    except Exception as e:
        print(f"Whisper transcription error: {e}")
        return ""



def _build_vision_messages(frame_b64_list: list[str], user_prompt: str, system_prompt: str = "") -> list:
    """Build multi-image message for GPT-4o storyboard analysis with optional system persona."""
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    content = []
    if len(frame_b64_list) == 1:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{frame_b64_list[0]}", "detail": "high"}
        })
    else:
        # Multiple frames — label each as part of a storyboard
        labels = ["Opening frame (0-5%)", "Early frame (25%)", "Mid frame (50%)", "Late frame (75%)"]
        for i, b64 in enumerate(frame_b64_list[:4]):
            label = labels[i] if i < len(labels) else f"Frame {i+1}"
            content.append({"type": "text", "text": f"[{label}]"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}
            })

    content.append({"type": "text", "text": user_prompt})
    messages.append({"role": "user", "content": content})
    return messages


async def analyze_creative_for_targeting(
    frame_b64_list: list[str],
    transcript: str = "",
    is_video: bool = False
) -> dict:
    """
    Deep creative analysis using GPT-4o Vision.
    Accepts storyboard frames (1 for image, up to 4 for video) + Whisper transcript.
    Returns granular scoring WITH reasoning, and dynamic, hyper-specific Meta targeting.
    """
    media_context = "video ad storyboard (4 frames shown)" if is_video and len(frame_b64_list) > 1 else "image ad creative"
    transcript_section = f"\nVIDEO TRANSCRIPT (from Whisper):\n\"{transcript}\"\n" if transcript else "\n(No audio transcript available — image upload or silent video)\n"

    system_prompt = """You are a senior Meta Ads strategist and creative director with deep expertise in the Indian D2C market. You have direct access to the entire Meta Ads Marketing API database in your mind.
You provide professional, brutally honest, and specific analysis. All output MUST be in valid JSON format."""

    user_prompt = f"""You are analyzing a {media_context} for a brand running Facebook/Instagram ads in India. {transcript_section}
    
YOUR TASK:
First, deeply understand WHAT is happening in this ad and WHO it is speaking to. Do not just look at surface-level objects. Analyze the story, the emotional hook, the implicit pain points being solved, and the cultural context. 

Then, act as a dynamic Meta Ads interest search engine. Generate hyper-specific, highly relevant targeting parameters based directly on the ad content. DO NOT use generic buckets.
- For Demographics: Define exact life stages, jobs, and roles (e.g., 'college goers', 'parents of toddlers', 'software engineers in IT hubs').
- For Interests: List highly specific brands, competitors, and exact Meta interests (e.g., 'Fabindia', 'Myntra', 'Organic food', 'Puma').
- For Locations: Identify specific Indian cities, districts, or regions where this exact product will "boom" (e.g., 'Koramangala in Bangalore', 'Tier-2 districts like Nashik or Surat for ethnic wear').

Return ONLY a valid JSON object with this EXACT structure:

{{
  "detected_product": "<Be specific: e.g. 'Ayurvedic anti-hairfall oil for postpartum mothers' not 'hair oil'>",
  "creative_meaning_analysis": "<2-3 sentences analyzing the underlying message and meaning of the ad. What is the emotional or utilitarian pitch?>",
  "detected_brand_stage": "<one of: Early-stage D2C (no brand recognition), Growing D2C (some presence), Established brand>",
  "creative_type": "<one of: Video Ad, Image Ad, UGC Video, Brand Film, Product Demo, Testimonial, Lifestyle, Unboxing, Meme/Trend>",

  "hook_score": <integer 1-100>,
  "hook_score_reasoning": "<Cite the EXACT visual/audio element in the first 2-3 seconds that creates or kills the hook. e.g. 'Opens with a static product shot against white background — no motion, no curiosity gap, viewer has no reason to stop scrolling'>",
  "hook_timing": "<e.g. 'Hook peaks at ~1.5s when the model reacts with surprise — this is the stop-scroll moment'>",
  "hook_type": "<one of: Motion Hook, Curiosity/Pattern Interrupt, Emotion/Reaction Hook, Price/Offer Hook, UGC/Social Proof Hook, Product Transformation Hook, Text-first Hook>",

  "strengths": [
    "<Cite SPECIFIC visual/audio element + WHY it hits the target demographic's psychology. If the ad uses relatability or meme/trend factors effectively, explicitly mention it here.>",
    "<Strength 2>",
    "<Strength 3>"
  ],

  "weaknesses": [
    "<Weakness 1: cite exactly what's missing and why it hurts conversions.>",
    "<Weakness 2>",
    "<Weakness 3>"
  ],

  "improvement_suggestions": [
    "<Actionable suggestion tied to a specific weakness.>",
    "<Suggestion 2>",
    "<Suggestion 3>"
  ],

  "creative_format_score": {{
    "visual_clarity": {{
      "score": <1-10>,
      "reasoning": "<What specifically makes it clear or unclear>"
    }},
    "brand_visibility": {{
      "score": <1-10>,
      "reasoning": "<Is brand name/logo visible? Where?>"
    }},
    "emotion_factor": {{
      "score": <1-10>,
      "reasoning": "<What emotion does this creative evoke and how effectively?>"
    }},
    "india_relevance": {{
      "score": <1-10>,
      "reasoning": "<Cultural nuances, language, casting, aesthetics that fit India>"
    }}
  }},

  "targeting": {{
    "recommended_age_range": "<e.g. '18-24 (College)', '28-35 (Young Parents)'>",
    "gender": "<All / Women / Men — with brief justification>",
    "psychographic_profile": "<1-2 sentences. Exactly who wakes up needing this solution based on the ad's messaging? Include their job, lifestyle, or daily routine.>",
    "top_interests": [
      "<Generate 8 to 12 highly specific Meta interests. Cast a wide but relevant net.>",
      "<Include exact competitor brands (e.g. FirstCry, Hamleys)>",
      "<Include lateral affinities (e.g. School supplies, Organic kids clothing)>",
      "<Include broad but relevant buyer buckets (e.g. Parents of toddlers, Primary school teachers)>",
      "<Interest 5>",
      "<Interest 6>",
      "<Interest 7>",
      "<Interest 8>"
    ],
    "interest_reasoning": "<Why are these exact interests, brands, or jobs the best fit for this creative?>",
    "behaviors": [
      "<e.g. 'Online Shopping', 'Engaged Shoppers', 'Early technology adopters', 'Frequent International Travelers'>",
      "<Behavior 2>"
    ],
    "behavior_reasoning": "<Why these behaviors match the buyer's intent>",
    "city_tiers": ["<Tier-1 / Tier-2 / Tier-3>"],
    "recommended_cities": [
      "<Provide 6 to 10 highly specific Indian districts or cities where this product will boom. Must include a mix of Tier-1 hubs and high-potential Tier-2/3 towns based on the exact product.>",
      "<City 2>",
      "<City 3>",
      "<City 4>",
      "<City 5>",
      "<City 6>"
    ],
    "city_reasoning": "<Provide a deep, 3-4 sentence strategic elaboration on WHY these precise Indian districts/cities are the primary market. Explain the geographic strategy based on wealth, infrastructure, or cultural affinity to the product.>",
    "excluded_audiences": ["<Who to exclude to save money>"],
    "language_recommendation": "<Hindi / English / Hinglish / Regional — with reasoning>"
  }},

  "placement_recommendation": "<Best Meta placement for this aspect ratio/style, with reasoning>",

  "overall_ad_readiness": "<one of: Ready to run / Needs minor fixes / Needs major rework>",
  "overall_ad_readiness_reasoning": "<1-2 sentences on whether this creative is strong enough to spend budget on right now>",

  "generated_hooks": [
    {{
      "hook_script": "<A detailed 3-second video hook script (Visuals + Dialogue)>",
      "psychological_angle": "<Why this specific angle will convert the target audience>"
    }},
    {{"hook_script": "...", "psychological_angle": "..."}},
    {{"hook_script": "...", "psychological_angle": "..."}}
  ],
  
  "generated_ad_copy": [
    {{
      "copy_text": "<Full 3-4 line Facebook/Instagram primary text. Use emojis appropriately.>",
      "copy_angle": "<e.g. 'Storytelling', 'Direct Offer', 'Pain-Agitate-Resolve'>"
    }},
    {{"copy_text": "...", "copy_angle": "..."}},
    {{"copy_text": "...", "copy_angle": "..."}}
  ]
}}

Be brutally honest. Specific. Reference what you actually see/hear. Do not output anything outside the JSON boundaries. Return ONLY valid JSON."""

    try:
        messages = _build_vision_messages(frame_b64_list, user_prompt, system_prompt)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2500,
            temperature=0.2
        )
        raw = response.choices[0].message.content or ""
        result = _extract_json(raw)
        if not result:
            print(f"JSON parse failed. Raw output: {raw[:500]}")
            result = _default_targeting_response()
        return result
    except Exception as e:
        print(f"OpenAI creative targeting error: {e}")
        return _default_targeting_response()


async def analyze_creative_performance(image_b64: str, metrics_context: dict) -> dict:
    """
    Analyzes an ad creative via GPT-4o Vision in context of real campaign metrics.
    Returns deep reasoning on why the ad worked, and specific improvements.
    """
    metrics_str = json.dumps(metrics_context, indent=2)

    system_prompt = """You are a senior Meta Ads strategist specializing in Indian D2C e-commerce.
You review real campaign performance data alongside ad creatives.
Your analysis must be professional, data-driven, and returned ONLY as a valid JSON object."""

    user_prompt = f"""Analyze WHY this creative drove the specific results shown below.
    
CAMPAIGN PERFORMANCE:
{metrics_str}

TASK: Be specific about:
- Which exact visual elements likely drove conversions (or hurt them)
- How the ROAS of {metrics_context.get('roas', 'N/A')}x compares to what this creative deserves
- What to test next based on what you actually see

Return a JSON object:
{{
  "creative_quality_score": <integer 1-100>,
  "creative_quality_reasoning": "<What specifically earns or loses this score>",
  "hook_analysis": "<Specific observation about the opening 3 seconds — what works or doesn't>",
  "why_it_worked": [
    "<Specific element + mechanism: e.g. 'The unboxing reveal at 2s creates a pattern interrupt — viewers who stop here are high-intent'>",
    "<Reason 2>",
    "<Reason 3>"
  ],
  "why_it_underperformed": [
    "<Specific friction point if ROAS < break-even, else skip with null>"
  ],
  "improvement_suggestions": [
    "<Specific test idea: e.g. 'Test a version that opens with the end result (product in use/worn) instead of the packaging — reduces cognitive load'>",
    "<Suggestion 2>",
    "<Suggestion 3>"
  ],
  "india_market_fit": "<How well does this creative feel designed FOR India? Cite specific cultural signals you see>",
  "verdict": "<Strong Performer / Good Creative / Needs Improvement>"
}}

Return ONLY valid JSON."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "high"}},
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ],
            max_tokens=1400,
            temperature=0.3
        )
        raw = response.choices[0].message.content or ""
        result = _extract_json(raw)
        return result or _default_performance_response()
    except Exception as e:
        print(f"OpenAI performance analysis error: {e}")
        return _default_performance_response()


async def analyze_text_only_performance(metrics_context: dict) -> dict:
    metrics_str = json.dumps(metrics_context, indent=2)
    prompt = f"""You are a Meta Ads strategist for Indian D2C brands.
Analyze these campaign metrics and give specific, useful advice (not generic):

METRICS:
{metrics_str}

Return JSON:
{{
  "performance_verdict": "<Strong Performer / Good / Break-even / Underperformer>",
  "performance_summary": "<2 sentences specific to these numbers>",
  "key_insights": ["<insight with specific numbers>", "<insight 2>", "<insight 3>"],
  "improvement_actions": ["<action tied to specific metric>", "<action 2>", "<action 3>"],
  "next_steps": "<What to do in the next 7 days based on these exact numbers>",
  "benchmark_comparison": "<How ROAS of {metrics_context.get('roas','?')}x compares to Indian D2C benchmarks by category>"
}}
Return ONLY valid JSON."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.3
        )
        raw = response.choices[0].message.content or ""
        return _extract_json(raw) or _default_text_analysis()
    except Exception as e:
        print(f"Text analysis error: {e}")
        return _default_text_analysis()


def _default_targeting_response() -> dict:
    return {
        "detected_product": "Unable to detect — OpenAI key may not be set",
        "detected_brand_stage": "Early-stage D2C (no brand recognition)",
        "creative_type": "Video Ad",
        "hook_score": 0,
        "hook_score_reasoning": "Analysis unavailable — check your OpenAI API key in backend/.env",
        "hook_timing": "—",
        "hook_type": "Product Demo",
        "strengths": ["Set your OPENAI_API_KEY in backend/.env to enable analysis"],
        "weaknesses": ["API key required for real analysis"],
        "improvement_suggestions": ["Add OPENAI_API_KEY=sk-... to backend/.env and restart the server"],
        "creative_format_score": {
            "visual_clarity": {"score": 0, "reasoning": "API key not configured"},
            "brand_visibility": {"score": 0, "reasoning": "API key not configured"},
            "emotion_factor": {"score": 0, "reasoning": "API key not configured"},
            "india_relevance": {"score": 0, "reasoning": "API key not configured"}
        },
        "targeting": {
            "recommended_age_range": "—",
            "gender": "—",
            "psychographic_profile": "Configure API key to enable targeting",
            "top_interests": ["API key required"],
            "interest_reasoning": "—",
            "behaviors": ["API key required"],
            "behavior_reasoning": "—",
            "city_tiers": ["Tier-1"],
            "recommended_cities": ["Mumbai", "Delhi", "Bangalore"],
            "city_reasoning": "—",
            "excluded_audiences": [],
            "language_recommendation": "Hinglish"
        },
        "placement_recommendation": "Instagram Reels (9:16 vertical video)",
        "overall_ad_readiness": "Needs major rework",
        "overall_ad_readiness_reasoning": "Cannot assess without OpenAI API key.",
        "generated_hooks": [],
        "generated_ad_copy": []
    }


def _default_performance_response() -> dict:
    return {
        "creative_quality_score": 0,
        "creative_quality_reasoning": "API key not configured — add to backend/.env",
        "hook_analysis": "—",
        "why_it_worked": ["Configure OPENAI_API_KEY to enable analysis"],
        "why_it_underperformed": [],
        "improvement_suggestions": ["Add OPENAI_API_KEY=sk-... to backend/.env"],
        "india_market_fit": "—",
        "verdict": "Needs Improvement"
    }


def _default_text_analysis() -> dict:
    return {
        "performance_verdict": "Good",
        "performance_summary": "Analysis temporarily unavailable.",
        "key_insights": ["Configure OpenAI key to enable insights"],
        "improvement_actions": ["Add OPENAI_API_KEY to backend/.env"],
        "next_steps": "—",
        "benchmark_comparison": "Indian D2C average ROAS: 2-4x"
    }
